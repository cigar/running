import json
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
        # Allow up to a 500m distance discrepancy given differing GPS recordings
        dist_diff = abs(r1.get("distance", 0) - r2.get("distance", 0))
        if dist_diff < 500:
            
            # Check if start times are within 15 minutes of each other
            dt1 = datetime.fromisoformat(r1["start_date_local"].replace(' ', 'T'))
            dt2 = datetime.fromisoformat(r2["start_date_local"].replace(' ', 'T'))
            time_diff = abs((dt1 - dt2).total_seconds())
            
            if time_diff < 900:
                duplicates.append((r1, r2))

with open("duplicates_report.txt", "w") as f:
    if not duplicates:
        f.write("No duplicates found.\n")
    else:
        for r1, r2 in duplicates:
            f.write(f"--- DUPLICATE SUSPECTED ---\n")
            f.write(f"Run 1: {r1['start_date_local']} | {r1['distance']}m | ID: {r1['run_id']} | Type: {r1['subtype']}\n")
            f.write(f"Run 2: {r2['start_date_local']} | {r2['distance']}m | ID: {r2['run_id']} | Type: {r2['subtype']}\n")
            f.write("\n")

print(f"Found {len(duplicates)} duplicate pairs. Report saved to duplicates_report.txt")
