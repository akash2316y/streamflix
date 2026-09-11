from biisal.vars import Var
from biisal.bot import StreamBot
from biisal.utils.human_readable import humanbytes
from biisal.utils.file_properties import get_file_ids
from biisal.utils.database import Database
from biisal.server.exceptions import InvalidHash
import urllib.parse
import aiofiles
import logging
import aiohttp
import jinja2
import json

db = Database(Var.DATABASE_URL, Var.name)

async def render_page(id, secure_hash, src=None):
    file = await StreamBot.get_messages(int(Var.BIN_CHANNEL), int(id))
    file_data = await get_file_ids(StreamBot, int(Var.BIN_CHANNEL), int(id))
    if file_data.unique_id[:6] != secure_hash:
        logging.debug(f"link hash: {secure_hash} - {file_data.unique_id[:6]}")
        logging.debug(f"Invalid hash for message with - ID {id}")
        raise InvalidHash

    src = urllib.parse.urljoin(
        Var.URL,
        f"{id}/{urllib.parse.quote_plus(file_data.file_name)}?hash={secure_hash}",
    )

    tag = file_data.mime_type.split("/")[0].strip()
    file_size = humanbytes(file_data.file_size)

    # Look up quality variants (if this file was generated as part of a
    # multi-quality group, e.g. via /genlink on an album) and any detected
    # audio tracks. Files with no tracked link record (older channel-post
    # links) simply get an empty list here, which keeps the page identical
    # to how it looked before this feature was added.
    qualities = []
    audio_tracks = []
    current_quality = None
    try:
        record = await db.get_link_by_message_id(id)
        if record:
            audio_tracks = record.get("audio_tracks") or []
            current_quality = record.get("quality_label")
            siblings = await db.get_links_by_group(record.get("group_id"))
            if len(siblings) > 1:
                for doc in sorted(siblings, key=lambda d: d.get("height") or 0, reverse=True):
                    q_hash = doc.get("file_unique_id_hash") or ""
                    q_name = doc.get("file_name") or ""
                    q_src = urllib.parse.urljoin(
                        Var.URL,
                        f"{doc['message_id']}/{urllib.parse.quote_plus(q_name)}?hash={q_hash}",
                    )
                    qualities.append({
                        "label": doc.get("quality_label") or "Original",
                        "src": q_src,
                        "current": int(doc["message_id"]) == int(id),
                    })
    except Exception as e:
        logging.debug(f"quality/audio lookup failed for {id}: {e}")

    if tag in ["video", "audio"]:
        template_file = "biisal/template/req.html"
    else:
        template_file = "biisal/template/dl.html"
        async with aiohttp.ClientSession() as s:
            async with s.get(src) as u:
                file_size = humanbytes(int(u.headers.get("Content-Length")))

    with open(template_file) as f:
        template = jinja2.Template(f.read())

    file_name = file_data.file_name.replace("_", " ")

    try:
        bot_username = StreamBot.username
    except Exception:
        bot_username = None

    return template.render(
        file_name=file_name,
        file_url=src,
        file_size=file_size,
        file_unique_id=file_data.unique_id,
        qualities=qualities,
        audio_tracks=audio_tracks,
        current_quality=current_quality,
        audio_tracks_json=json.dumps(audio_tracks),
        qualities_json=json.dumps(qualities),
        file_name_json=json.dumps(file_name),
        file_url_json=json.dumps(src),
        bot_username=bot_username,
    )