# (c) TechifyBots
# (c) @biisal
# (c) adarsh-goel
"""
Admin commands for managing generated private-file links:

    /genlink <seconds>   - reply to a private file/message to generate a
                           tracked stream+download link with a custom
                           expiry (seconds). No time = never expires.
                           Replying to an album (multiple files sent
                           together) generates one link with a quality
                           selector across all of them.
    /expire <time>       - reply to a previously generated link (or the
                           file itself) to change its expiry. Accepts
                           seconds/minutes/hours/days, e.g. 45s, 30m, 2h,
                           1d, or combinations like 1h30m.
    /delfile <id>        - deletes a previously generated link (and its
                           underlying file(s) in the log channel) by the
                           Link ID shown when the link was created.
"""

import asyncio
import datetime
import logging
import re
import secrets
import string

from pyrogram import filters, Client
from pyrogram.errors import FloodWait
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from biisal.bot import StreamBot
from biisal.utils.database import Database
from biisal.utils.human_readable import humanbytes
from biisal.utils.time_format import parse_duration, readable_duration
from biisal.utils.file_properties import get_name, get_hash, get_media_from_message, get_media_file_size
from biisal.utils.media_probe import quality_label_from_height, probe_and_store
from biisal.vars import Var
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)
db = Database(Var.DATABASE_URL, Var.name)


def _generate_link_code(length: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def _build_urls(message_id: int, file_name: str, file_hash: str):
    stream_link = f"{Var.URL}watch/{message_id}/{quote_plus(file_name)}?hash={file_hash}"
    download_link = f"{Var.URL}{message_id}/{quote_plus(file_name)}?hash={file_hash}"
    return stream_link, download_link


async def _resolve_target_message_id(m: Message):
    """Tries to figure out which tracked link a reply is pointing at, so
    /expire can be used either on the raw file post in BIN_CHANNEL, or on
    a bot-generated message containing the stream/download link."""
    reply = m.reply_to_message
    if not reply:
        return None

    if reply.chat and int(reply.chat.id) == int(Var.BIN_CHANNEL):
        return reply.id

    if reply.reply_markup and getattr(reply.reply_markup, "inline_keyboard", None):
        for row in reply.reply_markup.inline_keyboard:
            for btn in row:
                url = getattr(btn, "url", None)
                if url:
                    match = re.search(r"(\d+)/[^/]*(?:\?hash=|$)", url)
                    if match:
                        return int(match.group(1))

    text = reply.text or reply.caption
    if text:
        match = re.search(re.escape(Var.URL) + r"(?:watch/)?(\d+)/", text)
        if match:
            return int(match.group(1))

    return None


@StreamBot.on_message(filters.command("genlink") & filters.user(Var.OWNER_ID))
async def genlink_cmd(c: Client, m: Message):
    if not m.reply_to_message:
        return await m.reply_text(
            "<b>Reply to a private file/message with:</b>\n"
            "<code>/genlink 3600</code>  (expires in 3600 seconds)\n"
            "<code>/genlink</code>  (no expiration)"
        )

    reply = m.reply_to_message
    if not get_media_from_message(reply):
        return await m.reply_text("Please reply to a message containing a file (document/video/audio/photo).")

    args = m.text.split(maxsplit=1)
    time_arg = args[1].strip() if len(args) > 1 else None
    try:
        expire_seconds = parse_duration(time_arg)
    except ValueError:
        return await m.reply_text(
            "Invalid time. <code>/genlink</code> expects a number of seconds, e.g. "
            "<code>/genlink 3600</code>, or no value at all for no expiry."
        )

    status = await m.reply_text("<b>Generating link...</b>")

    # If this message is part of an album, treat every media item in it as
    # a separate quality variant of the same content.
    variants_source = [reply]
    if getattr(reply, "media_group_id", None):
        try:
            group_msgs = await c.get_media_group(reply.chat.id, reply.id)
            media_msgs = [msg for msg in group_msgs if get_media_from_message(msg)]
            if media_msgs:
                variants_source = media_msgs
        except Exception as e:
            logger.debug(f"get_media_group failed, falling back to single file: {e}")

    link_code = _generate_link_code()
    expire_at = (
        datetime.datetime.utcnow() + datetime.timedelta(seconds=expire_seconds)
        if expire_seconds else None
    )

    created = []
    for idx, src_msg in enumerate(variants_source):
        try:
            log_msg = await src_msg.copy(chat_id=Var.BIN_CHANNEL)
        except FloodWait as e:
            await asyncio.sleep(e.x)
            log_msg = await src_msg.copy(chat_id=Var.BIN_CHANNEL)

        media_obj = get_media_from_message(log_msg)
        height = getattr(media_obj, "height", None)
        width = getattr(media_obj, "width", None)
        auto_label = quality_label_from_height(height)
        quality_label = auto_label or ("Original" if len(variants_source) == 1 else f"Quality {idx + 1}")

        file_name = get_name(log_msg)
        file_hash = get_hash(log_msg)
        stream_link, download_link = _build_urls(log_msg.id, file_name, file_hash)

        await db.create_link(
            link_code=link_code,
            group_id=link_code,
            message_id=log_msg.id,
            channel_id=Var.BIN_CHANNEL,
            file_unique_id_hash=file_hash,
            file_name=file_name,
            quality_label=quality_label,
            width=width,
            height=height,
            is_primary=(idx == 0),
            source_chat_id=reply.chat.id,
            source_message_id=src_msg.id,
            expire_at=expire_at,
            created_by=m.from_user.id,
            created_by_name=m.from_user.first_name,
            generated_via="genlink",
        )
        asyncio.create_task(probe_and_store(db, log_msg.id))
        created.append((log_msg, stream_link, download_link, quality_label, get_media_file_size(log_msg)))

    primary_log_msg, primary_stream, primary_download, _, primary_size = created[0]
    expiry_text = readable_duration(expire_seconds) if expire_seconds else "Nᴇᴠᴇʀ (ɴᴏ ᴇxᴘɪʀʏ)"

    text = (
        f"<b>✅ ʟɪɴᴋ ɢᴇɴᴇʀᴀᴛᴇᴅ</b>\n\n"
        f"<b>📧 ꜰɪʟᴇ ɴᴀᴍᴇ :</b> <i>{get_name(primary_log_msg)}</i>\n"
        f"<b>📦 ꜰɪʟᴇ sɪᴢᴇ :</b> <i>{humanbytes(primary_size)}</i>\n"
        f"<b>🆔 ʟɪɴᴋ ɪᴅ :</b> <code>{link_code}</code>\n"
        f"<b>⏳ ᴇxᴘɪʀʏ :</b> {expiry_text}\n\n"
        f"<b>🎬 sᴛʀᴇᴀᴍ :</b> {primary_stream}\n"
        f"<b>📥 ᴅᴏᴡɴʟᴏᴀᴅ :</b> {primary_download}"
    )
    if len(created) > 1:
        qualities_line = ", ".join(item[3] for item in created)
        text += f"\n<b>🎞 ǫᴜᴀʟɪᴛɪᴇs :</b> {qualities_line}"
    text += f"\n\n<code>/delfile {link_code}</code> ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴛʜɪs ʟɪɴᴋ."

    await status.edit_text(
        text,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("• ꜱᴛʀᴇᴀᴍ •", url=primary_stream),
                InlineKeyboardButton("• ᴅᴏᴡɴʟᴏᴀᴅ •", url=primary_download),
            ]
        ])
    )


@StreamBot.on_message(filters.command("expire") & filters.user(Var.OWNER_ID))
async def expire_cmd(c: Client, m: Message):
    args = m.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        return await m.reply_text(
            "<b>Reply to a generated link (or the file itself) with:</b>\n"
            "<code>/expire 1h</code>\n\n"
            "Supported units: s/sec, m/min, h/hour, d/day - "
            "e.g. <code>45s</code>, <code>30m</code>, <code>2h</code>, <code>1d</code>, <code>1h30m</code>."
        )

    try:
        seconds = parse_duration(args[1].strip())
    except ValueError:
        return await m.reply_text("Invalid duration. Examples: <code>45s</code>, <code>30m</code>, <code>2h</code>, <code>1d</code>, <code>1h30m</code>.")
    if not seconds:
        return await m.reply_text("Please provide a duration greater than 0, e.g. <code>/expire 1h</code>.")

    target_message_id = await _resolve_target_message_id(m)
    if target_message_id is None:
        return await m.reply_text(
            "Reply to the file/link message you want to update (the post in the log channel, "
            "or the bot's own link message), then run <code>/expire &lt;time&gt;</code>."
        )

    record = await db.get_link_by_message_id(target_message_id)
    if not record or record.get("deleted"):
        return await m.reply_text("No active generated link found for that message. Use /genlink to create one first.")

    expire_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)
    await db.set_group_expiry(record["group_id"], expire_at)

    await m.reply_text(
        f"<b>⏳ ᴇxᴘɪʀʏ ᴜᴘᴅᴀᴛᴇᴅ</b>\n\n"
        f"<b>🆔 ʟɪɴᴋ ɪᴅ :</b> <code>{record['link_code']}</code>\n"
        f"<b>ɴᴇᴡ ᴇxᴘɪʀʏ :</b> {readable_duration(seconds)}\n"
        f"<i>(ᴀᴛ {expire_at.strftime('%Y-%m-%d %H:%M:%S')} UTC)</i>"
    )


@StreamBot.on_message(filters.command("delfile") & filters.user(Var.OWNER_ID))
async def delfile_cmd(c: Client, m: Message):
    args = m.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        return await m.reply_text("Usage: <code>/delfile &lt;link_id&gt;</code>\n\nThe Link ID is shown when a link is generated.")

    link_code = args[1].strip()
    docs = await db.get_links_by_code(link_code)
    if not docs:
        return await m.reply_text(f"No link found with ID <code>{link_code}</code>.")

    removed = 0
    for doc in docs:
        if doc.get("deleted"):
            continue
        try:
            await c.delete_messages(doc["channel_id"], doc["message_id"])
        except Exception as e:
            logger.debug(f"couldn't delete tg message {doc.get('message_id')}: {e}")
        removed += 1

    await db.delete_link_group(link_code)

    await m.reply_text(
        f"<b>🗑 ᴅᴇʟᴇᴛᴇᴅ</b>\n\n"
        f"<b>ʟɪɴᴋ ɪᴅ :</b> <code>{link_code}</code>\n"
        f"<b>ꜰɪʟᴇs ʀᴇᴍᴏᴠᴇᴅ :</b> {removed}\n\n"
        f"ᴛʜᴇ ɢᴇɴᴇʀᴀᴛᴇᴅ ʟɪɴᴋ(s) ᴡɪʟʟ ɴᴏ ʟᴏɴɢᴇʀ ᴡᴏʀᴋ."
    )
