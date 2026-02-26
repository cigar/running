import json
import sqlite3
from datetime import datetime
from itertools import combinations

with open("src/static/activities.json", "r") as f:
    activities = json.load(f)

runs = [a for a in activities if a.get("type") == "Run"]
deleted_count = 0

conn = sqlite3.connect("run_page/data.db")
cursor = conn.cursor()

for r1, r2 in combinations(runs, 2):
    date1 = r1.get("start_date_local", "")[:10]
    date2 = r2.get("start_date_local", "")[:10]
    
    if not date1 or not date2 or date1 != date2:
        continue
        
    dist_diff = abs(r1.get("distance", 0) - r2.get("distance", 0))
    dist_max = max(r1.get("distance", 1), r2.get("distance", 1))
    
    dt1 = datetime.fromisoformat(r1["start_date_local"].replace(' ', 'T'))
    dt2 = datetime.fromisoformat(r2["start_date_local"].replace(' ', 'T'))
    time_diff = abs((dt1 - dt2).total_seconds())

    is_dup = False
    if (dist_diff / dist_max) < 0.15 and time_diff < 7200:
        is_dup = True
    elif time_diff < 300:
        is_dup = True
    elif dist_diff < 1 and time_diff < 86400:
        is_dup = True

    if is_dup:
        # Score criteria: HR > Location > Distance
        def score(r):
            pts = 0
            if r.get("average_heartrate"): pts += 100
            if r.get("location_country"): pts += 10
            # Prefer longer distances if metadata is identical
            pts += (r.get("distance", 0) / 100000.0) 
            return pts
            
        r1_score = score(r1)
        r2_score = score(r2)
        
        run_to_delete = r2 if r1_score >= r2_score else r1
        
        cursor.execute("DELETE FROM activities WHERE run_id = ?", (run_to_delete['run_id'],))
        if cursor.rowcount > 0:
            deleted_count += 1
            print(f"Deleted overlapping {run_to_delete['run_id']} (Kept {'r1' if run_to_delete==r2 else 'r2'} with score {max(r1_score, r2_score):.2f})")

conn.commit()
conn.close()

if deleted_count > 0:
    from run_page.utils import make_activities_file
    print(f"Cleanup complete. Deleted {deleted_count} fuzzy records. Rebuilding activities.json...")
    import export_db # reuse earlier script
print("Done")
