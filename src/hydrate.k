// media/hydrate — TMDB/TVDB client in the media binary (not request handlers).
// Keys come from Settings (/config/settings.conf). Python scripts remain
// recorded-fixture / CI only. Sequential HTTPS; one hydrate at a time.
// Wired as `! hydrate` on the HTTP accept pump via media:hydrate-catalog.
