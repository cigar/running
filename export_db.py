import sqlite3
import json

conn = sqlite3.connect("run_page/data.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get the names of the columns to handle mapping
cursor.execute("SELECT * FROM activities ORDER BY start_date DESC")
rows = cursor.fetchall()
activities = []
for r in rows:
    activities.append(dict(r))

with open("src/static/activities.json", "w", encoding='utf-8') as f:
    json.dump(activities, f, ensure_ascii=False, indent=2)

print(f"Exported {len(activities)} activities.")
