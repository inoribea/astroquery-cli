#!/bin/bash
set -e

LOCALES_DIR="$(dirname "$0")"
DOMAIN="messages"

# First, extract all untranslated entries into .tmp files
echo "Extracting latest untranslated entries into .tmp files..."
sh "$LOCALES_DIR/extract-untranslated.sh"
echo "Finished extracting untranslated entries."

for tmp in "$LOCALES_DIR"/untranslated_*.tmp; do
    [ -f "$tmp" ] || continue
    lang=$(echo "$tmp" | sed -E 's/.*untranslated_([^.]+)\.tmp/\1/')
    po="$LOCALES_DIR/$lang/LC_MESSAGES/$DOMAIN.po"
    if [ ! -f "$po" ]; then
        echo "File not found: $po, skipping $lang"
        continue
    fi

    cp "$po" "$po.bak"

    poetry run python "$LOCALES_DIR/backfill_translated.py" "$po" "$tmp"
    echo "Updated: $po"
done

# Compile .po files to .mo files in both locations
pybabel compile -d "./locales"
echo "Compiled .po files to locales/ directory."

# Also compile to astroquery_cli/locales/ directory where the application expects them
echo "Compiling .mo files to astroquery_cli/locales/ directory..."
for po_file in locales/*/LC_MESSAGES/messages.po; do
    if [ -f "$po_file" ]; then
        # Extract language code from path (e.g., locales/zh/LC_MESSAGES/messages.po -> zh)
        lang=$(echo "$po_file" | sed 's|locales/\([^/]*\)/LC_MESSAGES/messages.po|\1|')
        
        # Create target directory if it doesn't exist
        target_dir="astroquery_cli/locales/$lang/LC_MESSAGES"
        mkdir -p "$target_dir"
        
        # Compile .po to .mo in the target location
        msgfmt "$po_file" -o "$target_dir/messages.mo"
        echo "  Compiled $po_file -> $target_dir/messages.mo"
    fi
done

echo "All .po files compiled to .mo files in both locations."
