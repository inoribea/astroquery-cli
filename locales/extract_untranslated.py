import polib
import os
import sys

def extract_untranslated(po_file_path, output_file_path):
    """
    Extracts untranslated or fuzzy entries from a .po file and writes them to an output file.
    """
    try:
        po = polib.pofile(po_file_path)
    except Exception as e:
        print(f"Error reading PO file {po_file_path}: {e}", file=sys.stderr)
        return

    untranslated_entries = []
    for entry in po:
        # An entry is considered untranslated if msgstr is empty or identical to msgid
        # and it's not a fuzzy translation.
        if not entry.obsolete and (not entry.msgstr or entry.msgstr == entry.msgid or entry.fuzzy):
            untranslated_entries.append(entry.msgid)

    # Sort and write unique entries to the output file
    untranslated_entries = sorted(list(set(untranslated_entries)))

    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            for entry in untranslated_entries:
                # polib handles unescaping, so we just write the msgid directly
                f.write(f"{entry}|||\n")
        print(f"Complete: Untranslated entries written to: {output_file_path}")
    except Exception as e:
        print(f"Error writing to output file {output_file_path}: {e}", file=sys.stderr)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python extract_untranslated_py.py <po_file_path> <output_file_path>", file=sys.stderr)
        sys.exit(1)

    po_file = sys.argv[1]
    output_file = sys.argv[2]
    extract_untranslated(po_file, output_file)
