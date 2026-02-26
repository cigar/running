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
    splits = moving_time.split(", ")
    days = 0
    if len(splits) == 2:
        try:
            days = int(splits[0].split(" ")[0])
        except ValueError:
            pass

    time_str = splits[-1]

    # Extract HH:MM:SS or HH:MM:SS.f from the string ignoring date prefixes
    time_match = re.search(r"(\d+:\d+:\d+(?:\.\d+)?)", time_str)
    if time_match:
        time_str = time_match.group(1)
        if "." in time_str:
            time_str = time_str.split(".")[0]

    parts = time_str.split(":")
    hours = int(parts[0]) if len(parts) >= 3 else 0
    minutes = (
        int(parts[1]) if len(parts) >= 3 else int(parts[0]) if len(parts) == 2 else 0
    )
    seconds = float(parts[-1])

    total_seconds = ((days * 24 + hours) * 60 + minutes) * 60 + seconds

    # if it results in strange negative values due to some GPX glitch where 23:59:46 means short duration
    if total_seconds < 0:
        return float("inf")  # ensure glitchy activities aren't selected as a PB

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


def extract_countries(location_country):
    if not location_country:
        return ""
    # Usually in format "City, Region, Postcode, Country"
    parts = [p.strip() for p in location_country.split(",")]
    if parts:
        return parts[-1]
    return ""


def main():
    if not os.path.exists(ACTIVITIES_FILE):
        print(f"Activities file not found at {ACTIVITIES_FILE}")
        return

    with open(ACTIVITIES_FILE, "r", encoding="utf-8") as f:
        activities = json.load(f)

    total_distance_meters = 0
    years = set()
    cities = set()
    countries = set()

    runs_stats = {
        "total": {"full_marathon": 0, "half_marathon": 0, "10k": 0},
        "years": {},
    }

    full_marathon_pb = None
    half_marathon_pb = None

    municipality_cities = [
        "北京市",
        "上海市",
        "天津市",
        "重庆市",
        "香港特别行政区",
        "澳门特别行政区",
    ]

    for run in activities:
        if run.get("type") != "Run":
            continue

        distance = run.get("distance", 0)
        total_distance_meters += distance

        start_date_local = run.get("start_date_local")
        if start_date_local:
            try:
                dt = datetime.fromisoformat(start_date_local.replace(" ", "T"))
                years.add(dt.year)
            except ValueError:
                pass

        location_country = run.get("location_country", "")
        if location_country:
            city_matches = extract_cities(location_country)
            if city_matches:
                city = city_matches[-1]
                cities.add(city)

            country_match = extract_countries(location_country)
            if country_match:
                countries.add(country_match)

        # The GPX data contains dirty historical runs (bike rides saved as runs).
        # We ignore these IDs to accurately find true PBs.
        IGNORE_RUN_IDS = [
            1497110863000,
            1521907511000,
            1484928039000,
            1486741898000,
            1505491955000,
            1570923543000,
        ]

        run_id = run.get("run_id")
        if run_id in IGNORE_RUN_IDS:
            continue

        run_distance_km = distance / 1000.0

        # Initialize year in stats if not present
        if start_date_local:
            year_str = str(dt.year)
            if year_str not in runs_stats["years"]:
                runs_stats["years"][year_str] = {
                    "full_marathon": 0,
                    "half_marathon": 0,
                    "10k": 0,
                }

            # Classify distance
            if run_distance_km >= 42.195:
                runs_stats["total"]["full_marathon"] += 1
                runs_stats["years"][year_str]["full_marathon"] += 1
            elif run_distance_km >= 21.0975:
                runs_stats["total"]["half_marathon"] += 1
                runs_stats["years"][year_str]["half_marathon"] += 1
            elif run_distance_km >= 10.0:
                runs_stats["total"]["10k"] += 1
                runs_stats["years"][year_str]["10k"] += 1

        # Filter out obvious bike rides/glitches saved as runs. A 4.5 m/s speed is ~3:42 min/km.
        avg_speed = run.get("average_speed") or 0
        if avg_speed > 4.5:
            continue

        moving_time = run.get("moving_time")
        if moving_time:
            seconds = convert_moving_time_to_seconds(moving_time)
            if seconds <= 0:
                continue

            # Full Marathon PBs
            if 42.195 <= run_distance_km < 46:
                if full_marathon_pb is None or seconds < full_marathon_pb["seconds"]:
                    full_marathon_pb = {
                        "run_id": run.get("run_id"),
                        "name": run.get("name"),
                        "distance": distance,
                        "moving_time": moving_time,
                        "seconds": seconds,
                        "start_date_local": start_date_local,
                    }

            # Half Marathon
            if 21.0975 <= run_distance_km < 25:
                if half_marathon_pb is None or seconds < half_marathon_pb["seconds"]:
                    half_marathon_pb = {
                        "run_id": run.get("run_id"),
                        "name": run.get("name"),
                        "distance": distance,
                        "moving_time": moving_time,
                        "seconds": seconds,
                        "start_date_local": start_date_local,
                    }

    summary = {
        "total_distance_km": round(total_distance_meters / 1000.0, 2),
        "total_years": len(years),
        "years": sorted(list(years)),
        "total_cities": len(cities),
        "cities": sorted(list(cities)),
        "total_countries": len(countries),
        "countries": sorted(list(countries)),
        "runs_stats": runs_stats,
        "full_marathon_pb": full_marathon_pb,
        "half_marathon_pb": half_marathon_pb,
    }

    # Override for precise chip time requested by user since GPX durations naturally drift by 1-2 seconds
    PRECISE_METADATA_OVERRIDES = {
        1733007657000: {"moving_time": "2:58:32", "seconds": 10712.0},
        1745103638000: {"moving_time": "1:26:58", "seconds": 5218.0},
    }

    if (
        summary["full_marathon_pb"]
        and summary["full_marathon_pb"]["run_id"] in PRECISE_METADATA_OVERRIDES
    ):
        override = PRECISE_METADATA_OVERRIDES[summary["full_marathon_pb"]["run_id"]]
        summary["full_marathon_pb"]["moving_time"] = override["moving_time"]
        summary["full_marathon_pb"]["seconds"] = override["seconds"]

    if (
        summary["half_marathon_pb"]
        and summary["half_marathon_pb"]["run_id"] in PRECISE_METADATA_OVERRIDES
    ):
        override = PRECISE_METADATA_OVERRIDES[summary["half_marathon_pb"]["run_id"]]
        summary["half_marathon_pb"]["moving_time"] = override["moving_time"]
        summary["half_marathon_pb"]["seconds"] = override["seconds"]

    os.makedirs(os.path.dirname(SUMMARY_FILE), exist_ok=True)
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Summary JSON successfully generated at {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
