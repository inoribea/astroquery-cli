#!/bin/bash
set -e

LOCALES_DIR="$(dirname "$0")"
DOMAIN="messages"

for po in "$LOCALES_DIR"/*/LC_MESSAGES/$DOMAIN.po; do
    [ -f "$po" ] || continue
    
    echo "Processing $po..."
    
    TEMP_PO=$(mktemp)
    
    # Deduplicate and normalize .po file using msgcat and msguniq
    # Then remove obsolete and fuzzy entries using msgattrib
    msgcat --no-wrap "$po" | msguniq --no-wrap -o "$TEMP_PO"
    msgattrib --no-obsolete --no-fuzzy "$TEMP_PO" -o "$po"
    rm "$TEMP_PO"
    
    echo "Deduped, cleaned, and removed obsolete/fuzzy: $po"
done
