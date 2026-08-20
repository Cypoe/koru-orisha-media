#!/usr/bin/env bash
# Bind SigmaNAS library shares into .pw/dev/media so local WSL `dev-wsl.sh`
# walks the same movies/shows/music/books/musicVideos trees as the NAS
# container (nfo, posters, [tt…] folders). Does not copy files.
#
#   bash scripts/dev-nas-link.sh          # map UNC shares, symlink into .pw/dev/media
#   bash scripts/dev-nas-link.sh unlink   # remove maps + symlinks
#
# Then: wsl --shutdown if /mnt/<letter> is missing, re-run this script,
# then SKIP_COMPILE=1 bash scripts/dev-wsl.sh
# Uses .pw/dev/nas-catalog.sqlite (not the fixture catalog).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MEDIA="${KORU_NAS_MEDIA:-$ROOT/.pw/dev/media}"
HOST="${NAS_HOST:-sigmanas}"
STATE="$MEDIA/.mounts"

# Compose binds: /volume1/<share> → /media/<name>
# musicVidoes is the DSM share name (typo kept).
SHARES=(
  "movies:movies"
  "shows:shows"
  "music:music"
  "books:books"
  "musicVidoes:musicVideos"
)

mkdir -p "$MEDIA"

win_net_use() {
  local unc="$1"
  powershell.exe -NoProfile -Command "net use * '${unc}' /persistent:no" 2>/dev/null | tr -d '\r'
}

letter_from_net_use() {
  local out="$1"
  local letter
  letter="$(printf '%s\n' "$out" | grep -oE '(^|[[:space:]])[A-Za-z]:( |$)' | head -n1 | tr -d ' :' | tr '[:upper:]' '[:lower:]')"
  printf '%s' "$letter"
}

existing_letter_for_unc() {
  local unc="$1"
  powershell.exe -NoProfile -Command "net use" 2>/dev/null | tr -d '\r' | grep -i "$unc" | grep -oE '[A-Za-z]:' | head -n1 | tr -d ':' | tr '[:upper:]' '[:lower:]'
}

link_share() {
  local share="$1" name="$2"
  local dest="$MEDIA/$name"
  if [[ -d "$dest" ]] && ls -A "$dest" >/dev/null 2>&1; then
    echo "ok $name -> $dest (already populated)"
    return 0
  fi
  rm -f "$dest"

  if command -v sshfs >/dev/null 2>&1; then
    mkdir -p "$dest"
    if sshfs -o reconnect,ServerAliveInterval=15 "${NAS_SSH:-cypoe@$HOST}:/volume1/${share}" "$dest"; then
      echo "$name sshfs /volume1/${share}" >>"$STATE"
      echo "ok $name -> sshfs /volume1/${share}"
      return 0
    fi
    rmdir "$dest" 2>/dev/null || true
  fi

  local unc="\\\\${HOST}\\${share}"
  local out letter
  letter="$(existing_letter_for_unc "$unc")"
  if [[ -z "$letter" ]]; then
    out="$(win_net_use "$unc" || true)"
    letter="$(letter_from_net_use "$out")"
  fi
  if [[ -z "$letter" ]]; then
    echo "could not map $unc" >&2
    printf '%s\n' "${out:-}" >&2
    return 1
  fi
  local mnt="/mnt/${letter}"
  local i
  for i in $(seq 1 20); do
    if [[ -d "$mnt" ]]; then break; fi
    sleep 0.2
  done
  if [[ ! -d "$mnt" ]]; then
    echo "$name netuse ${letter}: $unc" >>"$STATE"
    echo "Windows mapped ${letter}: but this WSL VM has no $mnt yet." >&2
    echo "From PowerShell: wsl --shutdown" >&2
    echo "Then: bash scripts/dev-nas-link.sh" >&2
    return 1
  fi
  ln -sfn "$mnt" "$dest"
  echo "$name netuse ${letter}: $unc" >>"$STATE"
  echo "ok $name -> $mnt ($unc)"
}

unlink_all() {
  if [[ -f "$STATE" ]]; then
    while read -r name kind rest; do
      [[ -z "${name:-}" ]] && continue
      if [[ "$kind" == "sshfs" ]]; then
        fusermount -u "$MEDIA/$name" 2>/dev/null || umount "$MEDIA/$name" 2>/dev/null || true
      elif [[ "$kind" == "netuse" ]]; then
        local letter="${rest%%:*}"
        letter="${letter%:}"
        powershell.exe -NoProfile -Command "net use ${letter}: /delete /y" >/dev/null 2>&1 || true
      fi
      rm -f "$MEDIA/$name"
    done <"$STATE"
    rm -f "$STATE"
  fi
  echo "unlinked $MEDIA"
}

cmd="${1:-link}"
if [[ "$cmd" == "unlink" ]]; then
  unlink_all
  exit 0
fi

: >"$STATE"
fail=0
for spec in "${SHARES[@]}"; do
  share="${spec%%:*}"
  name="${spec##*:}"
  if ! link_share "$share" "$name"; then
    fail=1
  fi
done

echo "media root $MEDIA"
echo "next: SKIP_COMPILE=1 bash scripts/dev-wsl.sh   # uses this tree + .pw/dev/nas-catalog.sqlite"
exit "$fail"
