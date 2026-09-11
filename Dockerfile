# Optional - only needed if you want audio-track detection to actually run.
#
# The bot works fine without this file (Koyeb will just use its default
# Python buildpack). But without `ffprobe` available at runtime, the
# audio-track-switching feature silently no-ops (it never fails, it just
# has nothing to show). Building from this Dockerfile instead gives you
# ffmpeg, which unlocks that feature.
#
# On Koyeb: when creating/editing the service, choose "Dockerfile" as the
# build method instead of "Buildpack" - Koyeb will pick this file up
# automatically since it lives at the repo root.

FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "biisal"]
