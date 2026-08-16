// media/auth — principal + cookie session (not Orisha, not Jellyfin).
// issuer is password | dsm. Later oauth mints the same cookie.
// Request handlers call authorize(); they never hash on every HTML render
// beyond the cookie MAC. No public users API this push.
