# Runtime image — musl static binary, same shape as Orisha `FROM scratch`.
# No libc, no shell, no Python. PUID is Docker `user:` in compose, not an entrypoint.
# CA bundle is copied from Alpine so Zig std.http.Client can speak HTTPS (TMDB/TVDB).
FROM alpine:3.20 AS certs
RUN apk add --no-cache ca-certificates

FROM scratch

COPY --from=certs /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --chmod=755 bin/media-server /app/media-server
COPY public /app/public

WORKDIR /app

ENV KORU_MEDIA_ROOT=/media \
    KORU_CATALOG=/data/catalog.sqlite \
    KORU_MANIFEST=/data/manifest.json \
    KORU_SEMANTIC=/data/semantic.json \
    KORU_CONFIG=/config/settings.conf \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

EXPOSE 3090

ENTRYPOINT ["/app/media-server"]
