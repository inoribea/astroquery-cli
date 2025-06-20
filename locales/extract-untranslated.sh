#!/bin/bash
set -ex # Enable verbose debugging

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Navigate to the project root (assuming script is in locales/ within the root)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Full path to locales directory
LOCALES_DIR="$SCRIPT_DIR" 
DOMAIN="messages"
POT_FILE="$LOCALES_DIR/$DOMAIN.pot" # This needs to be an absolute path

# AWK script to extract and clean msgid strings, handling multi-line and unescaping
# This script is written to a temporary file to avoid issues with 'read -r -d'
AWK_EXTRACT_MSGID_SCRIPT_PATH="$LOCALES_DIR/awk_extract_msgid.awk"
cat << 'EOF_AWK_EXTRACT_MSGID' > "$AWK_EXTRACT_MSGID_SCRIPT_PATH"
BEGIN {
    current_msgid_raw = "";
    in_msgid_block = 0;
}

/^msgid / {
    if (in_msgid_block) {
        cleaned_msgid = current_msgid_raw;
        sub(/^msgid /, "", cleaned_msgid);
        if (length(cleaned_msgid) > 0 && substr(cleaned_msgid, 1, 1) == "\"" && substr(cleaned_msgid, length(cleaned_msgid), 1) == "\"") {
            cleaned_msgid = substr(cleaned_msgid, 2, length(cleaned_msgid) - 2);
        }
        gsub(/\n"/, "\n", cleaned_msgid);
        gsub(/\\"/, "\"", cleaned_msgid);
        gsub(/\\n/, "\n", cleaned_msgid);
        print cleaned_msgid;
    }
    current_msgid_raw = $0;
    in_msgid_block = 1;
    next;
}

/^msgstr / {
    cleaned_msgid = current_msgid_raw;
    sub(/^msgid /, "", cleaned_msgid);
    if (length(cleaned_msgid) > 0 && substr(cleaned_msgid, 1, 1) == "\"" && substr(cleaned_msgid, length(cleaned_msgid), 1) == "\"") {
        cleaned_msgid = substr(cleaned_msgid, 2, length(cleaned_msgid) - 2);
    }
    gsub(/\n"/, "\n", cleaned_msgid);
    gsub(/\\"/, "\"", cleaned_msgid);
    gsub(/\\n/, "\n", cleaned_msgid);
    print cleaned_msgid;
    
    current_msgid_raw = "";
    in_msgid_block = 0;
    next;
}

/^"/ {
    if (in_msgid_block) {
        current_msgid_raw = current_msgid_raw "\n" $0;
    }
    next;
}

/^#/ {
    next;
}

/^$/ {
    if (in_msgid_block) {
        cleaned_msgid = current_msgid_raw;
        sub(/^msgid /, "", cleaned_msgid);
        if (length(cleaned_msgid) > 0 && substr(cleaned_msgid, 1, 1) == "\"" && substr(cleaned_msgid, length(cleaned_msgid), 1) == "\"") {
            cleaned_msgid = substr(cleaned_msgid, 2, length(cleaned_msgid) - 2);
        }
        gsub(/\n"/, "\n", cleaned_msgid);
        gsub(/\\"/, "\"", cleaned_msgid);
        gsub(/\\n/, "\n", cleaned_msgid);
        print cleaned_msgid;
    }
    current_msgid_raw = "";
    in_msgid_block = 0;
    next;
}

END {
    if (in_msgid_block && current_msgid_raw != "") {
        cleaned_msgid = current_msgid_raw;
        sub(/^msgid /, "", cleaned_msgid);
        if (length(cleaned_msgid) > 0 && substr(cleaned_msgid, 1, 1) == "\"" && substr(cleaned_msgid, length(cleaned_msgid), 1) == "\"") {
            cleaned_msgid = substr(cleaned_msgid, 2, length(cleaned_msgid) - 2);
        }
        gsub(/\n"/, "\n", cleaned_msgid);
        gsub(/\\"/, "\"", cleaned_msgid);
        gsub(/\\n/, "\n", cleaned_msgid);
        print cleaned_msgid;
    }
}
EOF_AWK_EXTRACT_MSGID

echo "Extracting untranslated and missing entries..."
for po in "$LOCALES_DIR"/*/LC_MESSAGES/$DOMAIN.po; do
    [ -f "$po" ] || continue
    lang=$(basename "$(dirname "$(dirname "$po")")")
    tmpfile="$LOCALES_DIR/untranslated_${lang}.tmp"
    tmpfile_pot_msgids="$LOCALES_DIR/all_pot_msgids.tmp"
    tmpfile_po_translated_msgids="$LOCALES_DIR/po_translated_msgids_${lang}.tmp"
    
    # Clear tmp files
    : > "$tmpfile"
    : > "$tmpfile_pot_msgids"
    : > "$tmpfile_po_translated_msgids"

    echo "--- Processing language: $lang ---"

    # 1. Extract all msgids from the .pot file
    echo "Step 1: Extracting all msgids from $POT_FILE..."
    awk -f "$AWK_EXTRACT_MSGID_SCRIPT_PATH" "$POT_FILE" | sort -u > "$tmpfile_pot_msgids"
    echo "Step 1 Complete: All msgids from $POT_FILE extracted to $tmpfile_pot_msgids"

    # 2. Extract all *translated* msgids from the .po file
    echo "Step 2: Extracting translated msgids from $po..."
    grep -P -A 1 '^msgid ' "$po" | awk '
        BEGIN {
            current_msgid_block = "";
            in_msgid_section = 0;
        }
        /^msgid / {
            current_msgid_block = $0;
            in_msgid_section = 1;
            next;
        }
        /^msgstr "[^"]+"$/ { # msgstr is not empty
            if (in_msgid_section) {
                print current_msgid_block; # Print the msgid block
            }
            in_msgid_section = 0;
            current_msgid_block = "";
            next;
        }
        /^"/ { # Continuation lines for msgid
            if (in_msgid_section) {
                current_msgid_block = current_msgid_block "\n" $0;
            }
            next;
        }
        /^#/ { next; } # Ignore comments
        /^$/ { # Empty line, end of entry
            in_msgid_section = 0;
            current_msgid_block = "";
            next;
        }
        END {
            # Handle case where last entry is a translated msgid
            if (in_msgid_section && current_msgid_block != "") {
                # This case is tricky, as we only print if msgstr is non-empty.
                # The grep -A 1 should handle this by providing the msgstr line.
                # So, no need to print here, as it would have been printed by the /^msgstr/ block.
            }
        }
    ' | awk -f "$AWK_EXTRACT_MSGID_SCRIPT_PATH" - | sort -u > "$tmpfile_po_translated_msgids"
    echo "Step 2 Complete: Translated msgids from $po extracted to $tmpfile_po_translated_msgids"

    # 3. Compare the two lists to find untranslated/missing entries
    echo "Step 3: Comparing msgids to find untranslated and missing entries..."
    comm -23 "$tmpfile_pot_msgids" "$tmpfile_po_translated_msgids" > "$tmpfile"
    echo "Step 3 Complete: Untranslated and missing entries written to: $tmpfile"

    # Clean up temporary files for the current language
    echo "Cleaning up temporary files for language $lang..."
    rm "$tmpfile_pot_msgids" "$tmpfile_po_translated_msgids"
done

# Clean up the AWK script file after all languages are processed
echo "Cleaning up AWK script file..."
rm "$AWK_EXTRACT_MSGID_SCRIPT_PATH"
