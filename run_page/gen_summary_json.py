import json
import os
import re
from datetime import datetime

ACTIVITIES_FILE = os.path.join("src", "static", "activities.json")
SUMMARY_FILE = os.path.join("public", "summary.json")

def convert_moving_time_to_seconds(moving_time):
    if not moving_time:
        return 0
    # moving_time can be formats like '1:30:20' or '2 days, 12:34:56' or '-1 day, 23:59:46'
    splits = moving_time.split(', ')
    days = 0
    if len(splits) == 2:
        try:
            days = int(splits[0].split(' ')[0])
        except ValueError:
            pass
    
    time_str = splits[-1]
    parts = time_str.split(':')
    hours = int(parts[0]) if len(parts) >= 3 else 0
    minutes = int(parts[1]) if len(parts) >= 3 else int(parts[0]) if len(parts) == 2 else 0
    seconds = float(parts[-1])
    
    total_seconds = ((days * 24 + hours) * 60 + minutes) * 60 + seconds
    
    # if it results in strange negative values due to some GPX glitch where 23:59:46 means short duration
    if total_seconds < 0:
        return float('inf') # ensure glitchy activities aren't selected as a PB
    
    return total_seconds

def extract_cities(location_country):
    if not location_country:
        return []
    locations = []
    pattern = re.compile(r"([\u4e00-\u9fa5]{2,}(市|自治州|特别行政区|盟|地区))")
    for match in pattern.finditer(location_country):
        locations.append(match.group(1))
    return locations

def extract_districts(location_country):
    if not location_country:
        return []
    locations = []
    pattern = re.compile(r"([\u4e00-\u9fa5]{2,}(区|县))")
    for match in pattern.finditer(location_country):
        locations.append(match.group(1))
    return locations

def main():
    if not os.path.exists(ACTIVITIES_FILE):
        print(f"Activities file not found at {ACTIVITIES_FILE}")
        return

    with open(ACTIVITIES_FILE, 'r', encoding='utf-8') as f:
        activities = json.load(f)

    total_distance_meters = 0
    years = set()
    cities = set()
    
    full_marathon_pb = None
    half_marathon_pb = None

    municipality_cities = ["北京市", "上海市", "天津市", "重庆市", "香港特别行政区", "澳门特别行政区"]

    for run in activities:
        if run.get("type") != "Run":
            continue
            
        distance = run.get("distance", 0)
        total_distance_meters += distance
        
        start_date_local = run.get("start_date_local")
        if start_date_local:
            try:
                dt = datetime.fromisoformat(start_date_local.replace(' ', 'T'))
                years.add(dt.year)
            except ValueError:
                pass
                
        location_country = run.get("location_country", "")
        if location_country:
            city_matches = extract_cities(location_country)
            if city_matches:
                city = city_matches[-1]
                if city in municipality_cities:
                    district_matches = extract_districts(location_country)
                    if district_matches:
                        city = district_matches[-1]
                cities.add(city)
                
        run_distance_km = distance / 1000.0
        moving_time = run.get("moving_time")
        if moving_time:
            seconds = convert_moving_time_to_seconds(moving_time)
            
            # Full Marathon
            if run_distance_km >= 42.195:
                if full_marathon_pb is None or seconds < full_marathon_pb["seconds"]:
                    full_marathon_pb = {
                        "run_id": run.get("run_id"),
                        "name": run.get("name"),
                        "distance": distance,
                        "moving_time": moving_time,
                        "seconds": seconds,
                        "start_date_local": start_date_local
                    }
                    
            # Half Marathon
            if 21.0975 <= run_distance_km < 42.195:
                if half_marathon_pb is None or seconds < half_marathon_pb["seconds"]:
                    half_marathon_pb = {
                        "run_id": run.get("run_id"),
                        "name": run.get("name"),
                        "distance": distance,
                        "moving_time": moving_time,
                        "seconds": seconds,
                        "start_date_local": start_date_local
                    }

    summary = {
        "total_distance_km": round(total_distance_meters / 1000.0, 2),
        "total_years": len(years),
        "years": sorted(list(years)),
        "total_cities": len(cities),
        "cities": sorted(list(cities)),
        "full_marathon_pb": full_marathon_pb,
        "half_marathon_pb": half_marathon_pb
    }

    os.makedirs(os.path.dirname(SUMMARY_FILE), exist_ok=True)
    with open(SUMMARY_FILE, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Summary JSON successfully generated at {SUMMARY_FILE}")

if __name__ == "__main__":
    main()
