import math
import re

platforms = [
    {"name": "Hibernia",   "lat": 46.7504, "lng": -48.7819, "depth": 78},
    {"name": "Sea Rose",   "lat": 46.7895, "lng": -48.146,  "depth": 107},
    {"name": "Terra Nova", "lat": 46.4,    "lng": -48.4,    "depth": 91},
    {"name": "Hebron",     "lat": 46.544,  "lng": -48.518,  "depth": 93},
]

def dms_to_decimal(coord_str, NSWE_hint=None):
    s = (
        coord_str.strip()
        .replace('o', '°')
        .replace('’', "'")
        .replace('‘', "'")
        .replace('”', '"')
        .replace('″', '"')
    )
    regex = r"(\d+)[°]?\s*(\d+)?[']?\s*(\d+)?[\"h]?\s*([NSEW])?"
    m = re.search(regex, s, re.IGNORECASE)
    if not m:
        raise ValueError(f"座標輸入格式錯誤: {coord_str}")
    deg = int(m.group(1))
    mi = int(m.group(2)) if m.group(2) is not None else 0
    sec = int(m.group(3)) if m.group(3) is not None else 0
    hemi = m.group(4) if m.group(4) else (NSWE_hint or "")
    decimal = deg + mi / 60 + sec / 3600
    if hemi.upper() in ["S", "W"]:
        decimal = -decimal
    elif hemi == "" and NSWE_hint is not None:
        if NSWE_hint.upper() in ["S", "W"]:
            decimal = -decimal
    return decimal

def deg2rad(deg):
    return deg * math.pi / 180.0

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0  # 地球半徑 (公里)
    dlat = deg2rad(lat2 - lat1)
    dlon = deg2rad(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(deg2rad(lat1)) * math.cos(deg2rad(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = R * c
    return d

def initial_bearing_deg(lat1, lon1, lat2, lon2):
    """
    從點1到點2的初始方位角（0~360 度，0=正北，順時針）
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)

    x = math.sin(dlon) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360.0) % 360.0  # 正規化到 0~360

def point_to_track_distance_km(plat_lat, plat_lng, ice_lat, ice_lng, heading_deg):
    """
    使用垂直距離（cross‑track）計算平台到冰山航跡的最近距離（公里）

    步驟：
    1. 算冰山到平台中心的哈弗辛距離 d（km）
    2. 算冰山→平台的方位角 bearing_ip
    3. 計算與冰山航向 heading_deg 之夾角 Δθ
    4. 垂直距離 = |d * sin(Δθ)|
    5. 若平台落在航跡「後方」（d*cosΔθ < 0），則最近距離視為 d
    """
    d_km = haversine_km(ice_lat, ice_lng, plat_lat, plat_lng)
    if d_km == 0:
        return 0.0

    bearing_ip = initial_bearing_deg(ice_lat, ice_lng, plat_lat, plat_lng)

    # Δθ 規一到 -180 ~ +180 度
    delta = (bearing_ip - heading_deg + 540.0) % 360.0 - 180.0
    delta_rad = deg2rad(delta)

    cross_track_km = abs(d_km * math.sin(delta_rad))
    along_km = d_km * math.cos(delta_rad)

    # 若平台在冰山起點後方，則最近點是冰山當前位置
    if along_km < 0:
        return d_km
    else:
        return cross_track_km

def platform_threat(distance_km, keel_depth, ocean_depth):
    if keel_depth >= ocean_depth * 1.10:
        return "Green"
    if distance_km > 18.52:  # >10 NM
        return "Green"
    elif distance_km >= 9.26:  # 5~10 NM
        return "Yellow"
    else:                     # <5 NM
        return "Red"

def subsea_threat(distance_km, keel_depth, ocean_depth):
    if distance_km > 46.3:  # >25 NM
        return "Green (does not intersect)"
    if keel_depth >= ocean_depth * 1.10:
        return "Green"
    ratio = keel_depth / ocean_depth
    if ratio >= 0.90:
        return "Red"
    elif ratio >= 0.70:
        return "Yellow"
    else:
        return "Green"

def main():
    print("請輸入冰山資訊:")
    iceberg_lat_str = input("冰山緯度 : ").strip()
    iceberg_lng_str = input("冰山經度 : ").strip()
    iceberg_heading_str = input("冰山航向角 (度): ").strip()
    iceberg_keel_str = input("冰山龍骨深度 (公尺): ").strip()

    # 緯度
    try:
        iceberg_lat = dms_to_decimal(iceberg_lat_str, NSWE_hint="N")
    except Exception:
        try:
            iceberg_lat = float(iceberg_lat_str)
        except Exception:
            print("緯度輸入錯誤。")
            return

    # 經度
    try:
        iceberg_lng = dms_to_decimal(iceberg_lng_str, NSWE_hint="W")
    except Exception:
        try:
            iceberg_lng = float(iceberg_lng_str)
            if iceberg_lng > 0:  # 紐芬蘭外海為西經，預設轉負
                iceberg_lng = -iceberg_lng
        except Exception:
            print("經度輸入錯誤。")
            return

    # 航向角
    try:
        iceberg_heading = float(re.sub(r"[^\d.]", "", iceberg_heading_str))
        iceberg_heading = iceberg_heading % 360.0
    except Exception:
        print("航向角輸入錯誤。")
        return

    # 龍骨深度
    try:
        iceberg_keel = float(re.sub(r"[^\d.]", "", iceberg_keel_str))
    except Exception:
        print("龍骨深度輸入錯誤。")
        return

    platform_results = {}
    subsea_results = {}
    platform_dists = {}
    direct_dists = {}

    for p in platforms:
        min_dist_km = point_to_track_distance_km(
            p["lat"], p["lng"], iceberg_lat, iceberg_lng, iceberg_heading
        )
        direct_dist_km = haversine_km(iceberg_lat, iceberg_lng, p["lat"], p["lng"])

        platform_dists[p["name"]] = min_dist_km
        direct_dists[p["name"]] = direct_dist_km

        plat_lv = platform_threat(min_dist_km, iceberg_keel, p["depth"])
        platform_results[p["name"]] = plat_lv

        if min_dist_km > 46.3:
            subsea_results[p["name"]] = "Green (does not intersect)"
        else:
            sub_lv = subsea_threat(min_dist_km, iceberg_keel, p["depth"])
            subsea_results[p["name"]] = sub_lv

    print("\n冰山與平台中心點哈弗辛距離 (直接距離, km):")
    for pname in ["Hibernia", "Hebron", "Sea Rose", "Terra Nova"]:
        print(f"{pname}: {direct_dists.get(pname, 0):.2f} km")

    print("\n冰山航跡到平台的垂直最近距離 (cross-track, km):")
    for pname in ["Hibernia", "Hebron", "Sea Rose", "Terra Nova"]:
        print(f"{pname}: {platform_dists.get(pname, 0):.2f} km")

    print("\nPlatform Threat Level\n")
    for pname in ["Hibernia", "Hebron", "Sea Rose", "Terra Nova"]:
        print(f"{pname}: {platform_results.get(pname, '')}")

    print("\nSubsea Asset Threat Level\n")
    for pname in ["Hibernia", "Hebron", "Sea Rose", "Terra Nova"]:
        print(f"{pname}: {subsea_results.get(pname, '')}")

if __name__ == "__main__":
    main()

