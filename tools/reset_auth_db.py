from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))

    try:
        from src import auth_db
    except Exception as e:
        print("Failed to import src.auth_db:", e)
        raise

    db_path = auth_db.DB_PATH
    if db_path.exists():
        print(f"Removing existing DB at {db_path}")
        db_path.unlink()
    else:
        print(f"No existing DB at {db_path}; creating new one")

    auth_db.init_db()
    print(f"Initialized new DB at {db_path}")


if __name__ == "__main__":
    main()
