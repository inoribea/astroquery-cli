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

    cp "$po" "$po.bak"

    awk -v TMP="$tmp" '
        function trim(s) { sub(/^[ \t\r\n]+/, "", s); sub(/[ \t\r\n]+$/, "", s); return s }
        BEGIN {
            while ((getline < TMP) > 0) {
                if ($0 ~ /^\//) continue;
                split($0, arr, /\|\|\|/);
                key = trim(arr[1]);
                val = trim(arr[2]);
                untranslated[key] = val;
            }
            close(TMP)
            msgid = ""; msgstr = ""; inmsgid = 0; inmsgstr = 0; lines = "";
        }
        /^msgid / {
            inmsgid = 1; inmsgstr = 0;
            msgid = substr($0,8,length($0)-8);
            lines = $0 "\n";
            next
        }
        /^msgstr / {
            inmsgid = 0; inmsgstr = 1;
            msgstr = substr($0,9,length($0)-9);
            if (msgid in untranslated && untranslated[msgid] != "") {
                n = split(untranslated[msgid], arr, /\n/);
                if (n == 1) {
                    lines = lines "msgstr \"" arr[1] "\"\n";
                } else {
                    lines = lines "msgstr \"\"\n";
                    for (i = 1; i <= n; i++) {
                        if (arr[i] != "")
                            lines = lines "\"" arr[i] "\"\n";
                    }
                }
            } else {
                lines = lines $0 "\n";
            }
            print lines;
            msgid = ""; msgstr = ""; lines = "";
            next
        }
        /^"/ {
            if (inmsgid) {
                msgid = msgid substr($0,2,length($0)-2);
            }
            if (inmsgstr) {
                msgstr = msgstr substr($0,2,length($0)-2);
            }
            lines = lines $0 "\n";
            next
        }
        {
            lines = lines $0 "\n";
            if ($0 == "") {
                print lines;
                msgid = ""; msgstr = ""; inmsgid = 0; inmsgstr = 0; lines = "";
            }
        }
    ' "$po.bak" > "$po"

    msgattrib --clear-fuzzy "$po" -o "$po"
    echo "Updated: $po"
done

pybabel compile -d "./locales"
echo "Compiled all .po files to .mo."