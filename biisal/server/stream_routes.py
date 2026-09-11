import re
import time
import math
import logging
import secrets
import mimetypes

from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine

from biisal.bot import multi_clients, work_loads, StreamBot
from biisal.server.exceptions import FIleNotFound, InvalidHash, LinkUnavailable
from biisal import StartTime, __version__
from ..utils.time_format import get_readable_time
from ..utils.custom_dl import ByteStreamer
from biisal.utils.render_template import render_page
from biisal.utils.database import Database
from biisal.vars import Var

db = Database(Var.DATABASE_URL, Var.name)
routes = web.RouteTableDef()

# ---------------- ROOT ---------------- #

@routes.get("/", allow_head=True)
async def root_route_handler(_):
    return web.json_response(
        {
            "server_status": "running",
            "uptime": get_readable_time(time.time() - StartTime),
            "telegram_bot": "@" + StreamBot.username,
            "connected_bots": len(multi_clients),
            "loads": dict(
                ("bot" + str(c + 1), l)
                for c, (_, l) in enumerate(
                    sorted(work_loads.items(), key=lambda x: x[1], reverse=True)
                )
            ),
            "version": __version__,
        }
    )


async def _ensure_link_active(file_id: int):
    """Raises LinkUnavailable if this message is tracked in the links
    collection AND has been deleted/expired. Messages with no tracked
    record (e.g. older channel-post links) are left completely untouched -
    they behave exactly as before this feature was added."""
    record = await db.get_link_by_message_id(file_id)
    if db.is_link_expired(record):
        raise LinkUnavailable


# ---------------- WATCH PAGE ---------------- #

@routes.get(r"/watch/{path:\S+}", allow_head=True)
async def watch_handler(request: web.Request):
    try:
        path = request.match_info.get("path", "")

        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            file_id = int(match.group(2))
        else:
            id_match = re.search(r"(\d+)", path)
            if not id_match:
                return web.Response(status=400, text="Invalid Watch URL")
            file_id = int(id_match.group(1))
            secure_hash = request.rel_url.query.get("hash")

        await _ensure_link_active(file_id)

        html = await render_page(file_id, secure_hash)
        return web.Response(text=html, content_type="text/html")

    except InvalidHash as e:
        return web.HTTPForbidden(text=e.message)

    except LinkUnavailable as e:
        return web.Response(status=410, text=e.message)

    except FIleNotFound as e:
        return web.HTTPNotFound(text=e.message)

    except (BadStatusLine, ConnectionResetError) as e:
        logging.error(e)
        return web.Response(status=400, text="Bad Request")

    except Exception as e:
        logging.exception(e)
        return web.Response(status=500, text="Internal Server Error")


# ---------------- STREAM / DOWNLOAD ---------------- #

@routes.get(r"/{path:\S+}", allow_head=True)
async def stream_route_handler(request: web.Request):
    try:
        path = request.match_info.get("path", "")

        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            file_id = int(match.group(2))
        else:
            id_match = re.search(r"(\d+)", path)
            if not id_match:
                return web.Response(status=400, text="Invalid Stream URL")
            file_id = int(id_match.group(1))
            secure_hash = request.rel_url.query.get("hash")

        await _ensure_link_active(file_id)

        return await media_streamer(request, file_id, secure_hash)

    except InvalidHash as e:
        return web.HTTPForbidden(text=e.message)

    except LinkUnavailable as e:
        return web.Response(status=410, text=e.message)

    except FIleNotFound as e:
        return web.HTTPNotFound(text=e.message)

    except (BadStatusLine, ConnectionResetError) as e:
        logging.error(e)
        return web.Response(status=400, text="Bad Request")

    except Exception as e:
        logging.exception(e)
        return web.Response(status=500, text="Internal Server Error")


# ---------------- MEDIA STREAMER ---------------- #

class_cache = {}

async def media_streamer(request: web.Request, file_id: int, secure_hash: str):
    range_header = request.headers.get("Range")

    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]

    if Var.MULTI_CLIENT:
        logging.info(f"Client {index} serving {request.remote}")

    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]
    else:
        tg_connect = ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect

    file = await tg_connect.get_file_properties(file_id)

    if file.unique_id[:6] != secure_hash:
        raise InvalidHash

    file_size = file.file_size

    if range_header:
        try:
            from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
            from_bytes = int(from_bytes)
            until_bytes = int(until_bytes) if until_bytes else file_size - 1
        except Exception:
            return web.Response(status=416, text="Invalid Range Header")
    else:
        from_bytes = request.http_range.start or 0
        until_bytes = (request.http_range.stop or file_size) - 1

    if until_bytes > file_size or from_bytes < 0 or until_bytes < from_bytes:
        return web.Response(
            status=416,
            text="416: Range Not Satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"}
        )

    chunk_size = 1024 * 1024
    until_bytes = min(until_bytes, file_size - 1)

    offset = from_bytes - (from_bytes % chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = until_bytes % chunk_size + 1

    req_length = until_bytes - from_bytes + 1
    part_count = math.ceil(until_bytes / chunk_size) - math.floor(offset / chunk_size)

    body = tg_connect.yield_file(
        file, index, offset, first_part_cut, last_part_cut,
        part_count, chunk_size
    )

    mime_type = file.mime_type or "application/octet-stream"
    file_name = file.file_name or f"{secrets.token_hex(2)}.bin"

    return web.Response(
        status=206 if range_header else 200,
        body=body,
        headers={
            "Content-Type": mime_type,
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(req_length),
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Accept-Ranges": "bytes",
        },
    )
