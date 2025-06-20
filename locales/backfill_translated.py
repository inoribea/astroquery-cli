import polib
import os
import sys

def backfill_translated(po_file_path, untranslated_tmp_path):
    """
    Backfills translations from a .tmp file into a .po file using polib.
    Also clears fuzzy flags for updated entries.
    """
    try:
        po = polib.pofile(po_file_path)
    except Exception as e:
        print(f"Error reading PO file {po_file_path}: {e}", file=sys.stderr)
        return

    # Read translations from the .tmp file
    translations = {}
    try:
        with open(untranslated_tmp_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Do not strip the entire line, as msgid might have leading/trailing whitespace or newlines
                if line.startswith('/') or not line.strip(): # Skip comments and empty lines
                    continue
                parts = line.split('|||', 1)
                if len(parts) == 2:
                    msgid = parts[0]
                    msgstr = parts[1].strip()
                    translations[msgid] = msgstr
    except Exception as e:
        print(f"Error reading untranslated .tmp file {untranslated_tmp_path}: {e}", file=sys.stderr)
        return

    updated_count = 0
    for entry in po:
        # Normalize the msgid from the .po file for comparison
        # Remove leading newline if it's a multi-line string starting with ""\n"..."
        normalized_po_msgid = entry.msgid
        if normalized_po_msgid.startswith('\n') and len(normalized_po_msgid) > 1 and normalized_po_msgid[1] != '\n':
            normalized_po_msgid = normalized_po_msgid[1:]

        if not entry.obsolete:
            if normalized_po_msgid in translations:
                new_msgstr = translations[normalized_po_msgid]
                if entry.msgstr != new_msgstr:
                    entry.msgstr = new_msgstr
                    # Clear fuzzy flag if it was updated
                    if 'fuzzy' in entry.flags:
                        entry.flags.remove('fuzzy')
                    updated_count += 1
                elif 'fuzzy' in entry.flags:
                    # If msgstr is already correct but still fuzzy, clear fuzzy flag
                    entry.flags.remove('fuzzy')
                    updated_count += 1


    if updated_count > 0:
        try:
            po.save()
            print(f"Updated {updated_count} entries in {po_file_path}")
        except Exception as e:
            print(f"Error saving PO file {po_file_path}: {e}", file=sys.stderr)
    else:
        print(f"No updates needed for {po_file_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python backfill_translated.py <po_file_path> <untranslated_tmp_path>", file=sys.stderr)
        sys.exit(1)

    po_file = sys.argv[1]
    untranslated_tmp_file = sys.argv[2]
    backfill_translated(po_file, untranslated_tmp_file)
