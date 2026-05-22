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

for entry in $(printf '%s' "$allowlist" | tr ',' ' '); do
  if ! printf '%s\n' "$entry" | grep -Eq '^([0-9]{1,3}\.){3}[0-9]{1,3}(/[0-9]{1,2})?$'; then
    echo "Invalid VINTON_GRAY_CERF_IP_ALLOWLIST entry: $entry"
    echo "Invalid VINTON_GRAY_CERF_IP_ALLOWLIST entry: $entry" >> /var/log/nginx/error.log
    exit 1
  fi

  printf '%s 1;\n' "$entry" >> "$allowlist_conf"
done

./sbin/nginx -p /ygag/nginx/ -t >> /var/log/nginx/error.log 2>&1 || exit 1

./sbin/nginx -p /ygag/nginx/ >> /var/log/nginx/error.log 2>&1 &

pid="$!"

# wait indefinitely
wait
