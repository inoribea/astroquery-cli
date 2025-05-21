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

    while IFS= read -r line; do
        if [[ ! "$line" =~ \|\|\| ]]; then
            echo "Format error: missing '|||' in $tmp: $line"
            exit 1
        fi
    done < "$tmp"

    cp "$po" "$po.bak"

    awk -v TMP="$tmp" '
        function trim(s) { sub(/^[ \t\r\n]+/, "", s); sub(/[ \t\r\n]+$/, "", s); return s }
        BEGIN {
            replaced = 0;
            not_replaced = 0;
            while ((getline < TMP) > 0) {
                if ($0 ~ /^\/\//) continue;
                split($0, arr, /\|\|\|/);
                key = trim(arr[1]);
                val = trim(arr[2]);
                untranslated[key] = val;
            }
            close(TMP)
        }
        /^msgid / {
            msgid=substr($0,8,length($0)-8);
            msgid=trim(msgid);
            pmsgid_list[++msgid_count] = msgid;
            print $0;
            next
        }
        /^msgstr / {
            if (msgid in untranslated && untranslated[msgid] != "") {
                print "msgstr \"" untranslated[msgid] "\"";
                printf("[Replaced] Original: %s\nTranslation: %s\n", msgid, untranslated[msgid]) > "/dev/stderr";
                replaced++;
            } else {
                print $0;
                if (msgid != "") {
                    printf("[Not replaced] Original: %s\n", msgid) > "/dev/stderr";
                    not_replaced++;
                }
            }
            msgid = "";
            next
        }
        !/^msgid / && !/^msgstr / {
            print $0;
        }
        END {
            print "\n[DEBUG] All keys loaded from tmp:" > "/dev/stderr";
            for (k in untranslated) {
                printf("  [%s]\n", k) > "/dev/stderr";
            }
            print "\n[DEBUG] All msgid encountered:" > "/dev/stderr";
            for (i in msgid_list) {
                printf("  [%s]\n", msgid_list[i]) > "/dev/stderr";
            }
            printf("\nTotal replaced: %d, not replaced: %d\n", replaced, not_replaced) > "/dev/stderr";
        }
    ' "$po.bak" > "$po"
    echo "Updated: $po"
done

pybabel compile -d "$LOCALES_DIR"

echo "Compiled all .po files to .mo."