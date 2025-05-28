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
        function extract_vars(str, arr,    n, i, m) {
            n = split(str, arr, /\{[a-zA-Z0-9_]+\}/)
            m = match(str, /\{[a-zA-Z0-9_]+\}/)
            delete arr
            i = 0
            while (match(str, /\{[a-zA-Z0-9_]+\}/)) {
                arr[++i] = substr(str, RSTART, RLENGTH)
                str = substr(str, RSTART + RLENGTH)
            }
            return i
        }
        function sync_vars(msgid, msgstr,    vars_id, vars_str, i, j, out, p) {
            split("", vars_id)
            split("", vars_str)
            extract_vars(msgid, vars_id)
            extract_vars(msgstr, vars_str)
            out = msgstr
            if (length(vars_id) > 0 && length(vars_str) == 0) {
                sub(/"$/, " " vars_id[1] "\"", out)
                for (i=2; i<=length(vars_id); i++) out = substr(out,1,length(out)-2) " " vars_id[i] "\"\n"
                return out
            }
            if (length(vars_id) > 0) {
                j = 1
                out = msgstr
                while (match(out, /\{[a-zA-Z0-9_]+\}/)) {
                    if (j <= length(vars_id)) {
                        out = substr(out,1,RSTART-1) vars_id[j] substr(out,RSTART+RLENGTH)
                    } else {
                        out = substr(out,1,RSTART-1) substr(out,RSTART+RLENGTH)
                    }
                    j++
                }
                for (p=j; p<=length(vars_id); p++) {
                    sub(/"$/, " " vars_id[p] "\"", out)
                }
                return out
            }
            gsub(/\{[a-zA-Z0-9_]+\}/, "", out)
            return out
        }
        BEGIN {
            while ((getline < TMP) > 0) {
                if ($0 ~ /^\//) continue
                split($0, arr, /\|\|\|/)
                key = trim(arr[1])
                val = trim(arr[2])
                untranslated[key] = val
            }
            close(TMP)
            msgid = ""; msgstr = ""; inmsgid = 0; inmsgstr = 0; lines = ""
        }
        /^msgid / {
            inmsgid = 1; inmsgstr = 0
            msgid = substr($0,8,length($0)-8)
            lines = $0 "\n"
            next
        }
        /^msgstr / {
            inmsgid = 0; inmsgstr = 1
            msgstr = substr($0,9,length($0)-9)
            if (msgid in untranslated && untranslated[msgid] != "") {
                n = split(untranslated[msgid], arr, /\n/)
                if (n == 1) {
                    fixed = sync_vars(msgid, "msgstr \"" arr[1] "\"\n")
                    lines = lines fixed
                } else {
                    lines = lines "msgstr \"\"\n"
                    for (i = 1; i <= n; i++) {
                        if (arr[i] != "") {
                            fixed = sync_vars(msgid, "\"" arr[i] "\"\n")
                            lines = lines fixed
                        }
                    }
                }
            } else {
                lines = lines $0 "\n"
            }
            print lines
            msgid = ""; msgstr = ""; lines = ""
            next
        }
        /^"/ {
            if (inmsgid) {
                msgid = msgid substr($0,2,length($0)-2)
            }
            if (inmsgstr) {
                msgstr = msgstr substr($0,2,length($0)-2)
            }
            lines = lines $0 "\n"
            next
        }
        {
            lines = lines $0 "\n"
            if ($0 == "") {
                print lines
                msgid = ""; msgstr = ""; inmsgid = 0; inmsgstr = 0; lines = ""
            }
        }
    ' "$po.bak" > "$po"

    msgattrib --clear-fuzzy "$po" -o "$po"
    echo "Updated: $po"
done

pybabel compile -d "./locales"
echo "Compiled all .po files to .mo."