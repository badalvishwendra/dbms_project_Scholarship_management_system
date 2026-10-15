"""Remove only the generated SQLite file so demo data is re-created next run."""
from pathlib import Path

database = Path(__file__).resolve().parent.parent / "storage" / "scholarships.db"
if database.exists():
    database.unlink()
    print("Database reset. Run python run.py to create fresh demo data.")
else:
    print("No generated database exists yet.")
