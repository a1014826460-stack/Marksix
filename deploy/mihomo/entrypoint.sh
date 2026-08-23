#!/bin/sh
set -eu

if [ -z "${DRAW_PROXY_SUBSCRIPTION_URL:-}" ]; then
  exec /mihomo -d /tmp -f /etc/mihomo/no-proxy.yaml
fi

# Keep the subscription URL out of the checked-in configuration. Escape only
# characters with special meaning to sed before rendering the runtime file.
escaped_url=$(printf '%s' "$DRAW_PROXY_SUBSCRIPTION_URL" | sed 's/[\\&|]/\\&/g')
sed "s|\${DRAW_PROXY_SUBSCRIPTION_URL}|$escaped_url|g" \
  /etc/mihomo/config.template.yaml > /tmp/config.yaml

exec /mihomo -d /tmp -f /tmp/config.yaml
