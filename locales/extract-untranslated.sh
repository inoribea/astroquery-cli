#!/bin/bash
set -e

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Navigate to the project root (assuming script is in locales/ within the root)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Full path to locales directory
LOCALES_DIR="$SCRIPT_DIR" 
DOMAIN="messages"
POT_FILE="$LOCALES_DIR/$DOMAIN.pot" # This needs to be an absolute path

# Extract untranslated and fuzzy entries
echo "Extracting untranslated and fuzzy entries..."
for po in "$LOCALES_DIR"/*/LC_MESSAGES/$DOMAIN.po; do
    [ -f "$po" ] || continue
    lang=$(basename "$(dirname "$(dirname "$po")")")
    tmpfile="$LOCALES_DIR/untranslated_${lang}.tmp"
    
    # Clear the tmpfile first
    : > "$tmpfile"

    # Extract untranslated messages by directly parsing the .po file
    awk -f - "$po" > "$tmpfile" << 'EOF_AWK'
        BEGIN {
            current_msgid = "";
            current_msgstr = "";
            is_fuzzy = 0;
            in_entry = 0; # 0: outside entry, 1: in msgid, 2: in msgstr
        }

        # Handle comments and fuzzy flag
        /^#/ {
            if ($0 ~ /#, fuzzy/) {
                is_fuzzy = 1;
            }
            next;
        }

        # Start of a new msgid
        /^msgid / {
            # Process the previous entry before starting a new one
            if (in_entry == 2 && current_msgid != "" && current_msgstr == "" && is_fuzzy == 0) {
                print current_msgid "|||" current_msgstr;
            }
            
            # Reset for the new entry
            current_msgid = $0;
            sub(/^msgid /, "", current_msgid); # Remove "msgid "
            # Remove leading and trailing quotes from msgid
            if (current_msgid ~ /^".*"$/) {
                current_msgid = substr(current_msgid, 2, length(current_msgid) - 2);
            }
            
            current_msgstr = "";
            is_fuzzy = 0;
            in_entry = 1; # Now in msgid block
            next;
        }

        # Start of a new msgstr
        /^msgstr / {
            current_msgstr = $0;
            sub(/^msgstr /, "", current_msgstr); # Remove "msgstr "
            # Remove leading and trailing quotes from msgstr
            if (current_msgstr ~ /^".*"$/) {
                current_msgstr = substr(current_msgstr, 2, length(current_msgstr) - 2);
            }
            in_entry = 2; # Now in msgstr block
            next;
        }

        # Continuation lines (quoted strings)
        /^"/ {
            line_content = $0;
            # Remove leading and trailing quotes from continuation lines
            if (line_content ~ /^".*"$/) {
                line_content = substr(line_content, 2, length(line_content) - 2);
            }
            
            if (in_entry == 1) { # Appending to msgid
                current_msgid = current_msgid line_content;
            } else if (in_entry == 2) { # Appending to msgstr
                current_msgstr = current_msgstr line_content;
            }
            next;
        }

        # Empty line (marks end of an entry)
        /^$/ {
            # Check if the completed entry is untranslated and not fuzzy
            if (in_entry == 2 && current_msgid != "" && current_msgstr == "" && is_fuzzy == 0) {
                print current_msgid "|||" current_msgstr;
            }
            # Reset for the next entry
            current_msgid = "";
            current_msgstr = "";
            is_fuzzy = 0;
            in_entry = 0;
            next;
        }

        # End of file: process the last entry if it exists
        END {
            if (in_entry == 2 && current_msgid != "" && current_msgstr == "" && is_fuzzy == 0) {
                print current_msgid "|||" current_msgstr;
            }
        }
EOF_AWK
    echo "Untranslated entries written to: $tmpfile"
done
