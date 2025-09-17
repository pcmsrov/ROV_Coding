import requests
import argparse
import csv
import os
import tempfile
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

# Configure your Adafruit IO credentials and feed name
AIO_USERNAME = "Lclin"
AIO_KEY = "aio_EJaU98M2wQN1nqRb3abXM3JrN8BZ"
FEED_KEY = "attendance"

# Absolute paths for CSV files (edit these to your desired locations)
CSV_BASE_DIR = r"G:\\.shortcut-targets-by-id\1WgDzD3R19S0R_kQlVss8C6Pwgun8nDlP\__ROV\01MateTEAM\出席名單"
CSV_DOWNLOAD_PATH = os.path.join(CSV_BASE_DIR, "attendance_data.csv")
CSV_FILTERED_PATH = os.path.join(CSV_BASE_DIR, "attendance_data_filtered.csv")

def parse_dt(dt_str):
    # Accept formats: YYYY-MM-DD, YYYY-MM-DDTHH:MM, YYYY-MM-DDTHH:MM:SS, with or without 'Z'
    if not dt_str:
        return None
    s = dt_str.strip()
    # Add Z handling
    if s.endswith('Z'):
        s = s[:-1]
    fmts = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(s, fmt)
            # Assume UTC
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    raise ValueError("Unsupported datetime format. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM[:SS] (UTC).")


def isoformat_z(dt):
    if not dt:
        return None
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def prompt_for_dt(label):
    while True:
        try:
            user_input = input(f"{label} time (UTC), e.g. 2025-09-11 or 2025-09-11T08:00 (blank to skip): ").strip()
            if user_input == "":
                return None
            return parse_dt(user_input)
        except ValueError as e:
            print(e)


def main():
    parser = argparse.ArgumentParser(description="Download Adafruit IO attendance CSV and optionally filter by time range")
    parser.add_argument("--start", help="Start time (UTC). e.g. 2025-09-11 or 2025-09-11T08:00")
    parser.add_argument("--end", help="End time (UTC). e.g. 2025-09-11 or 2025-09-11T18:00")
    args = parser.parse_args()

    start_dt = parse_dt(args.start) if args.start else None
    end_dt = parse_dt(args.end) if args.end else None

    # If any is missing, prompt interactively
    if start_dt is None:
        start_dt = prompt_for_dt("Start")
    if end_dt is None:
        end_dt = prompt_for_dt("End")

    base_url = f"https://io.adafruit.com/api/v2/{AIO_USERNAME}/feeds/{FEED_KEY}/data.csv"
    params = {"limit": 1000}
    # If provided, also pass to server to reduce payload
    if start_dt:
        params["start_time"] = isoformat_z(start_dt)
    if end_dt:
        params["end_time"] = isoformat_z(end_dt)

    url = base_url + "?" + urlencode(params)
    headers = {"X-AIO-Key": AIO_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200 and response.content:
            target_path = CSV_DOWNLOAD_PATH
            # Write to a temp file first, then replace atomically.
            tmp_dir = os.path.dirname(target_path) or '.'
            fd, tmp_path = tempfile.mkstemp(prefix='attendance_data_', suffix='.csv', dir=tmp_dir)
            try:
                os.write(fd, response.content)
            finally:
                os.close(fd)
            try:
                os.replace(tmp_path, target_path)
                print(f'Attendance feed CSV downloaded to {target_path}')
            except PermissionError:
                # Target might be locked (e.g., opened in Excel). Save with timestamp instead.
                ts_name = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                alt_path = os.path.join(tmp_dir, f'attendance_data_{ts_name}.csv')
                os.replace(tmp_path, alt_path)
                print(f"Target file in use. Saved as {alt_path}")
        else:
            print('Failed to download data. HTTP status:', response.status_code)
            return
    except Exception as e:
        print('Error downloading data:', e)
        return

    # If no filtering requested, we're done
    if not start_dt and not end_dt:
        return

    # Filter downloaded CSV by created_at
    input_path = CSV_DOWNLOAD_PATH
    output_path = CSV_FILTERED_PATH
    kept_rows = []

    def parse_created_at(value):
        if not value:
            return None
        s = value.strip()
        # Example: 2025-09-11T08:30:12Z
        if s.endswith('Z'):
            s_wo_z = s[:-1]
            fmts = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]
            for fmt in fmts:
                try:
                    return datetime.strptime(s_wo_z, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
        # Fallback: try full parse without Z
        fmts = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
        for fmt in fmts:
            try:
                return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None

    with open(input_path, 'r', newline='', encoding='utf-8') as f_in:
        reader = csv.DictReader(f_in)
        fieldnames = reader.fieldnames or []
        # Ensure output has same columns
        for row in reader:
            created_at_str = row.get('created_at') or row.get('created at') or row.get('time')
            ts = parse_created_at(created_at_str)
            if ts is None:
                continue
            if start_dt and ts < start_dt:
                continue
            if end_dt and ts > end_dt:
                continue
            # Add China (UTC+8) local time string for readability
            try:
                cn_ts = ts.astimezone(timezone(timedelta(hours=8)))
                row['created_at_cn'] = cn_ts.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                row['created_at_cn'] = ''
            kept_rows.append(row)

    # Safe write filtered CSV (handle locked file scenario)
    out_dir = os.path.dirname(output_path) or '.'
    fd_out, tmp_out = tempfile.mkstemp(prefix='attendance_data_filtered_', suffix='.csv', dir=out_dir)
    try:
        with os.fdopen(fd_out, 'w', newline='', encoding='utf-8') as f_out:
            out_fieldnames = list(fieldnames)
            if 'created_at_cn' not in out_fieldnames:
                out_fieldnames.append('created_at_cn')
            writer = csv.DictWriter(f_out, fieldnames=out_fieldnames)
            if fieldnames:
                writer.writeheader()
            writer.writerows(kept_rows)
        try:
            os.replace(tmp_out, output_path)
            print(f"Filtered {len(kept_rows)} rows into {output_path}")
        except PermissionError:
            ts_name = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            alt_filtered = os.path.join(out_dir, f'attendance_data_filtered_{ts_name}.csv')
            os.replace(tmp_out, alt_filtered)
            print(f"Target filtered file in use. Saved {len(kept_rows)} rows as {alt_filtered}")
    except Exception as e:
        try:
            # Clean up tmp file on failure
            if os.path.exists(tmp_out):
                os.remove(tmp_out)
        except Exception:
            pass
        print('Error writing filtered CSV:', e)


if __name__ == "__main__":
    main()