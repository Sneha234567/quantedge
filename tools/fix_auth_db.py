from pathlib import Path
import sqlite3


def ensure_columns(db_path: Path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get existing columns for search_history
    cur.execute("PRAGMA table_info(search_history);")
    cols = [row[1] for row in cur.fetchall()]
    added = []

    if "action" not in cols:
        cur.execute("ALTER TABLE search_history ADD COLUMN action TEXT;")
        added.append("action")

    # price is intentionally removed; only ensure `action` exists

    if added:
        conn.commit()
    conn.close()
    return added


if __name__ == "__main__":
    db_path = Path(__file__).resolve().parents[1] / "auth.db"
    if not db_path.exists():
        print(f"DB not found at {db_path}")
        raise SystemExit(1)
    added = ensure_columns(db_path)
    if added:
        print(f"Added columns to search_history: {added}")
    else:
        print("No columns needed adding; schema up-to-date.")
