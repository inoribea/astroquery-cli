#!/bin/bash
set -e

LOCALES_DIR="$(dirname "$0")"
DOMAIN="messages"

for tmp in "$LOCALES_DIR"/untranslated_*.tmp; do
    [ -f "$tmp" ] || continue
    lang=$(echo "$tmp" | sed -E 's/.*untranslated_([^.]+)\.tmp/\1/')
    po="$LOCALES_DIR/$lang/LC_MESSAGES/$DOMAIN.po"
    if [ ! -f "$po" ]; then
        echo "File not found: $po, skipping $lang"
        continue
    fi

    # Check format
    while IFS= read -r line; do
        if [[ ! "$line" =~ \|\|\| ]]; then
            echo "Format error: missing '|||' in $tmp: $line"
            exit 1
        fi
    done < "$tmp"

    # Backup original file
    cp "$po" "$po.bak"

    # Update po file using awk
    awk -v TMP="$tmp" '
        BEGIN {
            while ((getline < TMP) > 0) {
                split($0, arr, "|||");
                untranslated[arr[1]] = arr[2];
            }
            close(TMP)
        }
        /^msgid / {
            msgid=substr($0,8,length($0)-8);
            inmsgid=1; inmsgstr=0;
            print $0;
            next
        }
        /^msgstr / {
            inmsgid=0; inmsgstr=1;
            if (msgid in untranslated && untranslated[msgid] != "") {
                print "msgstr \"" untranslated[msgid] "\"";
                skip=1;
            } else {
                print $0;
                skip=0;
            }
            next
        }
        {
            if (!skip) print $0;
        }
    ' "$po.bak" > "$po"
    echo "Updated: $po"
done
