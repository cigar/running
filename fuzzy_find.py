import json
from datetime import datetime
from itertools import combinations

with open("src/static/activities.json", "r") as f:
    activities = json.load(f)

runs = [a for a in activities if a.get("type") == "Run"]
duplicates = []

for r1, r2 in combinations(runs, 2):
    # Rule 1: Looser time matching (within same day)
    date1 = r1.get("start_date_local", "")[:10]
    date2 = r2.get("start_date_local", "")[:10]

    if not date1 or not date2 or date1 != date2:
        continue

    dist_diff = abs(r1.get("distance", 0) - r2.get("distance", 0))
    dist_max = max(r1.get("distance", 1), r2.get("distance", 1))

    dt1 = datetime.fromisoformat(r1["start_date_local"].replace(" ", "T"))
    dt2 = datetime.fromisoformat(r2["start_date_local"].replace(" ", "T"))
    time_diff = abs((dt1 - dt2).total_seconds())

    is_dup = False

    # 1. Very similar distance AND same time window (Time gap < 120 mins)
    if (dist_diff / dist_max) < 0.15 and time_diff < 7200:
        is_dup = True
        reason = f"Similar distance ({dist_diff:.1f}m diff) + Close start time"

    # 2. Start time is almost identical (< 5 mins difference) EVEN IF distance differs (drifty GPS watch vs app)
    elif time_diff < 300:
        is_dup = True
        reason = "Start times almost identical (app vs watch)"

    # 3. Exactly the same distance on the exact same day
    elif dist_diff < 1 and time_diff < 86400:
        is_dup = True
        reason = "Exact same distance on the same day"

    if is_dup:
        # Don't show duplicates that we already deleted
        duplicates.append((r1, r2, reason))

with open("fuzzy_report.txt", "w") as f:
    if not duplicates:
        f.write("No overlaps found.\n")
    else:
        # Sort by date
        duplicates.sort(key=lambda x: x[0]["start_date_local"])
        for r1, r2, reason in duplicates:
            f.write(f"--- SUSPECTED OVERLAP: {reason} ---\n")
            f.write(
                f"  A [{r1['run_id']}]: {r1['start_date_local']} | {r1.get('distance')}m | HR: {r1.get('average_heartrate')}\n"
            )
            f.write(
                f"  B [{r2['run_id']}]: {r2['start_date_local']} | {r2.get('distance')}m | HR: {r2.get('average_heartrate')}\n"
            )
            f.write("\n")

print(f"Found {len(duplicates)} fuzzy overlap pairs. Wrote to fuzzy_report.txt")
