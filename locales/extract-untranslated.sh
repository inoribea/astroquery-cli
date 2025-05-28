#!/bin/bash
set -e

LOCALES_DIR="$(dirname "$0")"
DOMAIN="messages"

for po in "$LOCALES_DIR"/*/LC_MESSAGES/$DOMAIN.po; do
    [ -f "$po" ] || continue
    lang=$(basename "$(dirname "$(dirname "$po")")")
    tmpfile="$LOCALES_DIR/untranslated_${lang}.tmp"
    msgattrib --untranslated "$po" | \
    awk '
        BEGIN { msgid=""; msgstr=""; inmsgid=0; inmsgstr=0; found=0; }
        /^msgid / { inmsgid=1; inmsgstr=0; msgid=substr($0,8,length($0)-8); next }
        /^msgstr / { inmsgid=0; inmsgstr=1; msgstr=substr($0,9,length($0)-9); next }
        /^"/ {
            if (inmsgid) msgid=msgid substr($0,2,length($0)-2);
            if (inmsgstr) msgstr=msgstr substr($0,2,length($0)-2);
            next
        }
        /^$/ {
            if (msgid != "") { print msgid "|||" msgstr; found=1; }
            msgid=""; msgstr=""; inmsgid=0; inmsgstr=0;
        }
        END { if (!found) close("/dev/null"); }
    ' > "$tmpfile"

    : > "$tmpfile"
    msgattrib --untranslated "$po" | \
    awk '
        BEGIN { msgid=""; msgstr=""; inmsgid=0; inmsgstr=0; found=0; }
        /^msgid / { inmsgid=1; inmsgstr=0; msgid=substr($0,8,length($0)-8); next }
        /^msgstr / { inmsgid=0; inmsgstr=1; msgstr=substr($0,9,length($0)-9); next }
        /^"/ {
            if (inmsgid) msgid=msgid substr($0,2,length($0)-2);
            if (inmsgstr) msgstr=msgstr substr($0,2,length($0)-2);
            next
        }
        /^$/ {
            if (msgid != "") { print msgid "|||" msgstr; found=1; }
            msgid=""; msgstr=""; inmsgid=0; inmsgstr=0;
        }
    ' > "$tmpfile"
    echo "Untranslated and fuzzy entries written to: $tmpfile"
done