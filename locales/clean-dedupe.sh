#!/bin/bash
set -e

LOCALES_DIR="$(dirname \"$0\")"
DOMAIN="messages"

for po in "$LOCALES_DIR"/*/LC_MESSAGES/$DOMAIN.po; do
    [ -f "$po" ] || continue
    msguniq "$po" -o "$po"
    msgattrib --no-obsolete --no-fuzzy "$po" -o "$po"
    echo "Deduped, cleaned, and removed obsolete/fuzzy: $po"
done
