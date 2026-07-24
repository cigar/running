import os
import sqlite3
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "run_page"))
from utils import save_activities_json

conn = sqlite3.connect("run_page/data.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get the names of the columns to handle mapping
cursor.execute("SELECT * FROM activities ORDER BY start_date DESC")
rows = cursor.fetchall()
activities = []
for r in rows:
    activities.append(dict(r))

save_activities_json(activities)
print(f"Exported {len(activities)} activities.")
