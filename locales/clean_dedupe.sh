#!/bin/bash
set -e

LOCALES_DIR="$(dirname "$0")"
DOMAIN="messages"

for po in "$LOCALES_DIR"/*/LC_MESSAGES/$DOMAIN.po; do
    [ -f "$po" ] || continue
    msguniq "$po" -o "$po"
    msgattrib --no-obsolete "$po" -o "$po"
    echo "Deduped and cleaned: $po"
done
