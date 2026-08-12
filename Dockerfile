# Runtime image for koru-orisha-media.
# Expects a prebuilt Linux binary at bin/media-server (see scripts/build-image.sh).
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      python3 \
      zlib1g \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY bin/media-server /app/media-server
COPY public /app/public
COPY scripts/index_media.py /app/scripts/index_media.py
COPY docker/entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/media-server /app/entrypoint.sh \
    && mkdir -p /media /data

ENV KORU_MEDIA_ROOT=/media \
    KORU_MANIFEST=/data/manifest.json

EXPOSE 3090

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -sf http://127.0.0.1:3090/library >/dev/null || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
