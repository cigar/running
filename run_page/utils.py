import json
import os
import time
from datetime import UTC, datetime, timedelta

import pytz

try:
    from rich import print
except Exception:
    pass
from generator import Generator
from stravalib.client import Client
from stravalib.exc import RateLimitExceeded


def compute_activities_stats(activities_list):
    runs = [
        a for a in activities_list if isinstance(a, dict) and a.get("type") == "Run"
    ]

    now = datetime.now(UTC).replace(tzinfo=None)
    latest_dt = now
    for a in runs:
        start_date_local = a.get("start_date_local")
        if start_date_local:
            try:
                dt = datetime.fromisoformat(str(start_date_local).replace(" ", "T"))
                latest_dt = max(latest_dt, dt)
            except ValueError:
                pass

    # 1) 最近12个月按月拆分的跑步公里数 (Last 12 months monthly breakdown of running km)
    cur_year = latest_dt.year
    cur_month = latest_dt.month

    months_12_list = []
    total_12m_dist_m = 0.0

    for i in range(11, -1, -1):
        m = cur_month - i
        y = cur_year
        while m <= 0:
            m += 12
            y -= 1
        month_str = f"{y:04d}-{m:02d}"

        month_dist_m = 0.0
        for a in runs:
            start_date_local = a.get("start_date_local")
            if start_date_local:
                try:
                    dt = datetime.fromisoformat(str(start_date_local).replace(" ", "T"))
                    if dt.year == y and dt.month == m:
                        month_dist_m += a.get("distance", 0) or 0.0
                except ValueError:
                    pass

        total_12m_dist_m += month_dist_m
        months_12_list.append(
            {
                "month": month_str,
                "km": round(month_dist_m / 1000.0, 2),
            }
        )

    last_12_months_km = round(total_12m_dist_m / 1000.0, 2)
    last_12_months = {
        "total_km": last_12_months_km,
        "months": months_12_list,
    }

    # 2) 最近15天的跑步公里数，区分清晨(00:00-11:59)与午后(12:00-23:59)
    end_date = latest_dt.date()
    days_15_list = []
    total_morning_m = 0.0
    total_afternoon_m = 0.0

    for i in range(14, -1, -1):
        day_date = end_date - timedelta(days=i)
        morning_m = 0.0
        afternoon_m = 0.0

        for a in runs:
            start_date_local = a.get("start_date_local")
            if start_date_local:
                try:
                    dt = datetime.fromisoformat(str(start_date_local).replace(" ", "T"))
                    if dt.date() == day_date:
                        dist = a.get("distance", 0) or 0.0
                        if dt.hour < 12:
                            morning_m += dist
                        else:
                            afternoon_m += dist
                except ValueError:
                    pass

        total_morning_m += morning_m
        total_afternoon_m += afternoon_m

        days_15_list.append(
            {
                "date": str(day_date),
                "morning_km": round(morning_m / 1000.0, 2),
                "afternoon_km": round(afternoon_m / 1000.0, 2),
                "total_km": round((morning_m + afternoon_m) / 1000.0, 2),
            }
        )

    last_15_days_stats = {
        "total_km": round((total_morning_m + total_afternoon_m) / 1000.0, 2),
        "morning_km": round(total_morning_m / 1000.0, 2),
        "afternoon_km": round(total_afternoon_m / 1000.0, 2),
        "days": days_15_list,
    }

    return {
        "last_12_months_km": last_12_months_km,
        "last_12_months": last_12_months,
        "last_15_days": last_15_days_stats,
        "activities": activities_list,
    }


def save_activities_json(activities_list, file_paths=None):
    from config import JSON_FILE, PUBLIC_JSON_FILE

    if file_paths is None:
        file_paths = [JSON_FILE, PUBLIC_JSON_FILE]

    data = compute_activities_stats(activities_list)

    for filepath in file_paths:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2 if "public" in filepath else None,
            )


def adjust_time(time, tz_name):
    tc_offset = datetime.now(pytz.timezone(tz_name)).utcoffset()
    return time + tc_offset


def adjust_time_to_utc(time, tz_name):
    tc_offset = datetime.now(pytz.timezone(tz_name)).utcoffset()
    return time - tc_offset


def adjust_timestamp_to_utc(timestamp, tz_name):
    tc_offset = datetime.now(pytz.timezone(tz_name)).utcoffset()
    delta = int(tc_offset.total_seconds())
    return int(timestamp) - delta


def to_date(ts):
    """
    Parse ISO format timestamp string to datetime object.
    Uses datetime.fromisoformat() for standard ISO format strings.
    Falls back to strptime for non-standard formats.
    """
    # Try fromisoformat first (Python 3.7+)
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        # Fallback to strptime for non-standard formats
        ts_fmts = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"]
        for ts_fmt in ts_fmts:
            try:
                return datetime.strptime(ts, ts_fmt)
            except ValueError:
                pass
        raise ValueError(f"cannot parse timestamp {ts} into date")


def make_activities_file(
    sql_file, data_dir, json_file, file_suffix="gpx", activity_title_dict={}
):
    generator = Generator(sql_file)
    generator.sync_from_data_dir(
        data_dir, file_suffix=file_suffix, activity_title_dict=activity_title_dict
    )
    activities_list = generator.load()
    save_activities_json(activities_list)


def make_strava_client(client_id, client_secret, refresh_token):
    client = Client()

    refresh_response = client.refresh_access_token(
        client_id=client_id, client_secret=client_secret, refresh_token=refresh_token
    )
    client.access_token = refresh_response["access_token"]
    return client


def get_strava_last_time(client, is_milliseconds=True):
    """
    if there is no activities cause exception return 0
    """
    try:
        activity = None
        activities = client.get_activities(limit=10)
        activities = list(activities)
        activities.sort(key=lambda x: x.start_date, reverse=True)
        # for else in python if you don't know please google it.
        for a in activities:
            if a.type == "Run":
                activity = a
                break
        else:
            return 0
        end_date = activity.start_date + activity.elapsed_time
        last_time = int(datetime.timestamp(end_date))
        if is_milliseconds:
            last_time = last_time * 1000
        return last_time
    except Exception as e:
        print(f"Something wrong to get last time err: {e!s}")
        return 0


def upload_file_to_strava(client, file_name, data_type, force_to_run=True):
    with open(file_name, "rb") as f:
        try:
            if force_to_run:
                r = client.upload_activity(
                    activity_file=f, data_type=data_type, activity_type="run"
                )
            else:
                r = client.upload_activity(activity_file=f, data_type=data_type)

        except RateLimitExceeded as e:
            timeout = e.timeout
            print(f"Strava API Rate Limit Exceeded. Retry after {timeout} seconds")
            time.sleep(timeout)
            if force_to_run:
                r = client.upload_activity(
                    activity_file=f, data_type=data_type, activity_type="run"
                )
            else:
                r = client.upload_activity(activity_file=f, data_type=data_type)
        print(
            f"Uploading {data_type} file: {file_name} to strava, upload_id: {r.upload_id}."
        )
