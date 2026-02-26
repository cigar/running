import json
import os
from datetime import datetime
from itertools import combinations

with open("src/static/activities.json", "r") as f:
    activities = json.load(f)

runs = [a for a in activities if a.get("type") == "Run"]

duplicates = []

# Group by Date string (YYYY-MM-DD) to limit search space
runs_by_date = {}
for r in runs:
    date_str = r.get("start_date_local", "")[:10]
    if not date_str:
        continue
    if date_str not in runs_by_date:
        runs_by_date[date_str] = []
    runs_by_date[date_str].append(r)

for date_str, daily_runs in runs_by_date.items():
    if len(daily_runs) < 2:
        continue
        
    for r1, r2 in combinations(daily_runs, 2):
        dist_diff = abs(r1.get("distance", 0) - r2.get("distance", 0))
        if dist_diff < 500:
            dt1 = datetime.fromisoformat(r1["start_date_local"].replace(' ', 'T'))
            dt2 = datetime.fromisoformat(r2["start_date_local"].replace(' ', 'T'))
            time_diff = abs((dt1 - dt2).total_seconds())
            if time_diff < 900:
                duplicates.append((r1, r2))

deleted_count = 0

for r1, r2 in duplicates:
    r1_score = 0
    r2_score = 0
    
    # 1. Heart rate
    if r1.get("average_heartrate"): r1_score += 100
    if r2.get("average_heartrate"): r2_score += 100
    
    # 2. Location
    if r1.get("location_country"): r1_score += 10
    if r2.get("location_country"): r2_score += 10
    
    # 3. Distance
    if r1.get("distance", 0) > r2.get("distance", 0): r1_score += 1
    if r2.get("distance", 0) > r1.get("distance", 0): r2_score += 1

    run_to_delete = r2 if r1_score >= r2_score else r1
    run_to_keep = r1 if r1_score >= r2_score else r2
    
    print(f"Keeping {run_to_keep['run_id']} ({r1_score if run_to_keep == r1 else r2_score} pts) | Deleting {run_to_delete['run_id']} ({r2_score if run_to_delete == r2 else r1_score} pts)")

    import sqlite3
    try:
        conn = sqlite3.connect("run_page/data.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM activities WHERE run_id = ?", (run_to_delete['run_id'],))
        if cursor.rowcount > 0:
            deleted_count += 1
            print(f"  -> Deleted from DB")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error accessing DB: {e}")

from run_page.utils import make_activities_file
print(f"\nCleanup complete. Deleted {deleted_count} redundant track records.")
print("Rebuilding activities.json...")
try:
    make_activities_file("run_page/data.db", "GPX_OUT", "src/static/activities.json")
    print("Done")
except:
    pass
