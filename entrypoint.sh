#!/usr/bin/env sh

set -eu

# Add user account and group
addgroup -S -g "${PUID:-1000}" tghook
adduser -S -u "${PGID:-1000}" -D -H -h /tmp -s /usr/bin/nologin -G tghook -g tghook tghook

# Assign ownership of public folder and configuration file to created user
mkdir -p "$LOG_PATH"
chown -R tghook:tghook "$LOG_PATH"

# Parse comamand line arguments
if [ "${1#-}" != "${1}" ] || [ -z "$(command -v "${1}")" ] || { [ -f "${1}" ] && ! [ -x "${1}" ]; }; then
  set -- su tghook -s /usr/local/bin/tghook -- "$@"
fi

exec "$@"
