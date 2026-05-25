#!/bin/sh
set -m

pid=0

# SIGTERM handler
term_handler() {
  echo "Caught SIGTERM signal!"
  echo "Caught SIGTERM signal!" >> /var/log/nginx/error.log
  sleep 1
  if [ "$pid" -ne 0 ]; then
    kill -QUIT "$pid"
    wait "$pid"
  fi
  exit 143;
}

trap 'term_handler' SIGTERM

allowlist="${VINTON_GRAY_CERF_IP_ALLOWLIST:-}"
allowlist_conf="/ygag/nginx/conf/vinton-gray-cerf-allowlist.conf"

: > "$allowlist_conf"

is_valid_octet() {
  case "$1" in
    ''|*[!0-9]*) return 1 ;;
  esac
  [ "$1" -ge 0 ] 2>/dev/null && [ "$1" -le 255 ]
}

is_valid_allowlist_entry() {
  entry="$1"
  ip="${entry%/*}"
  prefix=""

  if [ "$entry" != "$ip" ]; then
    prefix="${entry#*/}"
    case "$prefix" in
      ''|*[!0-9]*|*/*) return 1 ;;
    esac
    [ "$prefix" -ge 0 ] 2>/dev/null && [ "$prefix" -le 32 ] || return 1
  fi

  old_ifs="$IFS"
  IFS='.'
  set -- $ip
  IFS="$old_ifs"

  [ "$#" -eq 4 ] || return 1
  is_valid_octet "$1" &&
    is_valid_octet "$2" &&
    is_valid_octet "$3" &&
    is_valid_octet "$4"
}

for entry in $(printf '%s' "$allowlist" | tr ',' ' '); do
  if ! is_valid_allowlist_entry "$entry"; then
    echo "Invalid VINTON_GRAY_CERF_IP_ALLOWLIST entry: $entry"
    echo "Invalid VINTON_GRAY_CERF_IP_ALLOWLIST entry: $entry" >> /var/log/nginx/error.log
    exit 1
  fi

  printf '%s 1;\n' "$entry" >> "$allowlist_conf"
done

/ygag/nginx/sbin/nginx -p /ygag/nginx/ -t >> /var/log/nginx/error.log 2>&1 || exit 1

/ygag/nginx/sbin/nginx -p /ygag/nginx/ >> /var/log/nginx/error.log 2>&1 &

pid="$!"

# wait indefinitely
wait
