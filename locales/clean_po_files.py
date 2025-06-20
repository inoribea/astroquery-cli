import polib
import sys
import os

def clean_po_file(po_file_path):
    """
    Cleans a .po file by deduplicating entries, removing obsolete entries,
    and removing fuzzy flags.
    """
    try:
        po = polib.pofile(po_file_path)
    except Exception as e:
        print(f"Error reading PO file {po_file_path}: {e}", file=sys.stderr)
        return

    # Manually deduplicate and filter out obsolete and fuzzy entries
    seen_msgids = set()
    deduplicated_and_cleaned_entries = []

    for entry in po:
        if entry.msgid not in seen_msgids:
            seen_msgids.add(entry.msgid)
            if not entry.obsolete: # Keep non-obsolete entries
                if not entry.fuzzy: # Keep non-fuzzy entries
                    deduplicated_and_cleaned_entries.append(entry)
                else:
                    print(f"Removing fuzzy entry: {entry.msgid}", file=sys.stderr)
            else:
                print(f"Removing obsolete entry: {entry.msgid}", file=sys.stderr)

    # Create a new POFile object with only the deduplicated and cleaned entries
    new_po = polib.POFile()
    new_po.metadata = po.metadata # Preserve metadata
    new_po.extend(deduplicated_and_cleaned_entries)

    try:
        new_po.save(po_file_path)
        print(f"Cleaned and updated: {po_file_path}")
    except Exception as e:
        print(f"Error saving cleaned PO file {po_file_path}: {e}", file=sys.stderr)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python clean_po_files.py <po_file_path>", file=sys.stderr)
        sys.exit(1)

    po_file = sys.argv[1]
    clean_po_file(po_file)
