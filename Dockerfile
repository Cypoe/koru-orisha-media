# Runtime image — Glance-style: alpine + one binary. No Python, no gosu, no Debian.
# Empty catalog walks /media on boot. Optional JSON import if catalog is empty.
# PUID is Docker `user:` in compose.nas.yaml, not a fat entrypoint.
FROM alpine:3.22

RUN apk add --no-cache tzdata

WORKDIR /app

COPY bin/media-server /app/media-server
COPY public /app/public
COPY docker/entrypoint.sh /app/entrypoint.sh

RUN sed -i 's/\r$//' /app/entrypoint.sh \
    && chmod +x /app/media-server /app/entrypoint.sh \
    && mkdir -p /media /data /config \
    && echo entrypoint-tz-optional >/dev/null

ENV KORU_MEDIA_ROOT=/media \
    KORU_CATALOG=/data/catalog.sqlite \
    KORU_MANIFEST=/data/manifest.json \
    KORU_SEMANTIC=/data/semantic.json \
    KORU_CONFIG=/config/settings.conf \
    TZ=Europe/Berlin

EXPOSE 3090

ENTRYPOINT ["/app/entrypoint.sh"]
