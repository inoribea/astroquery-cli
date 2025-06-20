#!/bin/bash
set -ex # Enable verbose debugging

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Navigate to the project root (assuming script is in locales/ within the root)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Full path to locales directory
LOCALES_DIR="$SCRIPT_DIR" 
DOMAIN="messages"

echo "Extracting untranslated and missing entries using Python..."
for file in "$LOCALES_DIR"/$DOMAIN.pot "$LOCALES_DIR"/*/LC_MESSAGES/$DOMAIN.po; do
    [ -f "$file" ] || continue
    
    filename=$(basename "$file")
    if [ "$filename" = "$DOMAIN.pot" ]; then
        lang="pot"
        tmpfile="$LOCALES_DIR/untranslated_${lang}.tmp"
    else
        lang=$(basename "$(dirname "$(dirname "$file")")")
        tmpfile="$LOCALES_DIR/untranslated_${lang}.tmp"
    fi
    
    # Clear tmp file
    : > "$tmpfile"

    echo "--- Processing file: $file (Language: $lang) ---"

    # Use the Python script to extract untranslated msgid,msgstr pairs
    echo "Extracting untranslated entries from $file to $tmpfile..."
    poetry run python "$LOCALES_DIR/extract_untranslated.py" "$file" "$tmpfile"
    echo "Complete: Untranslated entries written to: $tmpfile"

done
