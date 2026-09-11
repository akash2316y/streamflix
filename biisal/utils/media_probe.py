# (c) TechifyBots
# (c) @biisal
# (c) adarsh-goel
"""
Best-effort media analysis used for the audio-track-switching and
quality-labelling features.

Design notes (important for Koyeb / low-resource deployments):
- We never transcode anything. We only *inspect* a small leading chunk of
  the file (a partial download, reusing the exact same Telegram byte-range
  mechanism already used for streaming) with `ffprobe`, purely to discover
  metadata such as embedded audio tracks.
- `ffprobe` is optional. If it isn't installed (e.g. a plain buildpack
  deployment without a Dockerfile), every function here degrades to safe
  defaults instead of raising, so the rest of the bot is completely
  unaffected. Installing ffmpeg (see the provided Dockerfile) simply
  unlocks richer audio-track detection.
- This module never downloads more than MAX_PROBE_BYTES, regardless of the
  real file size, to keep bandwidth/CPU/disk usage bounded on small
  instances.
"""

import asyncio
import json
import logging
import math
import os
import shutil
import tempfile

logger = logging.getLogger(__name__)

MAX_PROBE_BYTES = 20 * 1024 * 1024  # 20 MB - enough to reach the moov atom of most "fast-start" files
PROBE_CHUNK_SIZE = 1024 * 1024
PROBE_TIMEOUT = 25  # seconds

_probe_streamer = None


def ffprobe_available() -> bool:
    return shutil.which("ffprobe") is not None


def quality_label_from_height(height):
    """Maps a video's pixel height to the nearest familiar quality label
    (thresholds sit at the midpoint between adjacent standard heights)."""
    if not height:
        return None
    if height >= 1600:
        return "2160p"
    if height >= 900:
        return "1080p"
    if height >= 600:
        return "720p"
    if height >= 420:
        return "480p"
    if height >= 300:
        return "360p"
    if height >= 200:
        return "240p"
    return f"{height}p"


def _get_probe_streamer():
    """Lazily creates a single shared ByteStreamer instance for probing, so
    we don't spin up a new background cache-cleaner task per probe."""
    global _probe_streamer
    if _probe_streamer is None:
        from biisal.bot import StreamBot
        from biisal.utils.custom_dl import ByteStreamer
        _probe_streamer = ByteStreamer(StreamBot)
    return _probe_streamer


async def _download_probe_chunk(streamer, file_id, dest_path: str) -> int:
    file_size = getattr(file_id, "file_size", 0) or MAX_PROBE_BYTES
    until_bytes = min(MAX_PROBE_BYTES, file_size) - 1
    if until_bytes < 0:
        return 0

    offset = 0
    first_part_cut = 0
    last_part_cut = until_bytes % PROBE_CHUNK_SIZE + 1
    part_count = max(
        1,
        math.ceil(until_bytes / PROBE_CHUNK_SIZE) - math.floor(offset / PROBE_CHUNK_SIZE),
    )

    written = 0
    with open(dest_path, "wb") as f:
        async for chunk in streamer.yield_file(
            file_id, 0, offset, first_part_cut, last_part_cut, part_count, PROBE_CHUNK_SIZE
        ):
            if not chunk:
                continue
            f.write(chunk)
            written += len(chunk)
    return written


async def probe_media(message_id: int) -> dict:
    """
    Best-effort probe of a message already copied into BIN_CHANNEL.
    Always returns a dict with keys `audio_tracks`, `width`, `height` -
    empty/None on any failure, never raises.
    """
    result = {"audio_tracks": [], "width": None, "height": None}
    if not ffprobe_available():
        return result

    tmp_path = None
    try:
        streamer = _get_probe_streamer()
        file_id = await streamer.get_file_properties(int(message_id))

        with tempfile.NamedTemporaryFile(delete=False, suffix=".probe") as tmp:
            tmp_path = tmp.name

        written = await _download_probe_chunk(streamer, file_id, tmp_path)
        if written <= 0:
            return result

        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams",
            tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=PROBE_TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            return result

        data = json.loads(stdout or b"{}")
        streams = data.get("streams", [])
        audio_index = 0
        for s in streams:
            if s.get("codec_type") == "audio":
                tags = {k.lower(): v for k, v in (s.get("tags", {}) or {}).items()}
                lang = tags.get("language")
                title = tags.get("title")
                label = title or (lang.upper() if lang else f"Track {audio_index + 1}")
                result["audio_tracks"].append({
                    "index": audio_index,
                    "codec": s.get("codec_name"),
                    "language": lang,
                    "label": label,
                })
                audio_index += 1
            elif s.get("codec_type") == "video" and result["width"] is None:
                result["width"] = s.get("width")
                result["height"] = s.get("height")
        return result
    except Exception as e:
        logger.debug(f"media probe failed for message {message_id}: {e}")
        return result
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


async def probe_and_store(db, message_id: int):
    """Runs probe_media() and, if it found anything useful, updates the
    matching link document. Meant to be launched as a fire-and-forget
    background task right after a link is generated, so it never delays
    sending the link to the user."""
    try:
        info = await probe_media(message_id)
        update = {}
        if info.get("audio_tracks"):
            update["audio_tracks"] = info["audio_tracks"]
        if info.get("height"):
            record = await db.get_link_by_message_id(message_id)
            if record and not record.get("height"):
                update["height"] = info["height"]
                update["width"] = info.get("width")
                label = quality_label_from_height(info["height"])
                if label:
                    update["quality_label"] = label
        if update:
            await db.update_link_media_info(message_id, update)
    except Exception as e:
        logger.debug(f"probe_and_store failed for {message_id}: {e}")
