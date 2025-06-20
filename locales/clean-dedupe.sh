#!/bin/bash
set -e

LOCALES_DIR="$(dirname "$0")"
DOMAIN="messages"

for po in "$LOCALES_DIR"/*/LC_MESSAGES/$DOMAIN.po; do
    [ -f "$po" ] || continue
    
    echo "Processing $po..."
    
    poetry run python "$LOCALES_DIR/clean_po_files.py" "$po"
    echo "Cleaned and updated: $po"
done
