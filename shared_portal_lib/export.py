"""
Local CSV export for a volunteer's own assigned records - a personal
backup/offline copy, independent of the Sheets sync. Shared across
every portal since the shape (list of row dicts) is identical
regardless of pool.
"""
import csv
import io


def to_csv_bytes(rows: list[dict]) -> bytes:
    if not rows:
        return b""
    fieldnames = list(rows[0].keys())
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")  # BOM so Excel opens Arabic correctly
