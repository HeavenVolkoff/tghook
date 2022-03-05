#!/usr/bin/env sh

set -eu

# Shortcircuit for non-default commands.
# The last part inside the "{}" is a workaround for the following bug in ash/dash:
# https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=874264
if [ -n "${1:-}" ] && [ "${1#-}" = "${1}" ] \
  && [ -n "$(command -v -- "${1}")" ] \
  && { ! [ -f "${1}" ] || [ -x "${1}" ]; }; then
  exec "$@"
fi

if [ "$(id -u)" -ne 0 ]; then
  echo "This container requires executing as root for initial setup, privilages are dropped after" 1>&2
  exit 1
fi

echo "Configure unprivileged user"
addgroup --system --gid "${PGID}" tghook
adduser --system --disabled-password \
  --uid "${PUID}" \
  --home /var/empty \
  --gecos 'Telegram bot system account' \
  --ingroup tghook \
  tghook
passwd -l tghook

if [ -n "${TZ:-}" ]; then
  echo "Set Timezone to $TZ"
  rm -f /etc/localtime
  ln -s "/usr/share/zoneinfo/${TZ}" /etc/localtime
  echo "$TZ" >/etc/timezone
fi

echo "Fix telegram bot's directories permissions"
mkdir -p "$LOG_PATH"
chown -R "${PUID}:${PGID}" "$LOG_PATH"

set -- su tghook -s /usr/local/bin/tghook -- "$@"
