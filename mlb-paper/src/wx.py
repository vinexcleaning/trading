"""Ballpark weather, from the one free source that survived the robots gate.

**The two obvious sources are both forbidden and that is not an assumption.**
`api.open-meteo.com/robots.txt` and `api.weather.gov/robots.txt` each return
`User-agent: *` / `Disallow: /`. They are refused by `robots_check.py` and
nothing in this project touches them.

What is used instead is better for this purpose anyway: **NOAA's Aviation
Weather Center**, `aviationweather.gov`. No key, no registration, no robots.txt
at all (a 404 means no restrictions are published -- RFC 9309), and it serves
two products this brief needs:

    METAR  observed temperature, dewpoint, wind direction and speed, hourly
    TAF    a 24-30 h FORECAST of wind direction, speed, gusts and precipitation

Every ballpark has a TAF-issuing airport within about 15 miles. The mapping is
DISCOVERED from the venue's own coordinates rather than hardcoded per club,
because clubs move -- the Athletics play in Sacramento this season, and a
hardcoded OAK -> KOAK table would have sent this at the wrong city all year.

### Why wind direction is useless without the ballpark's orientation

"Wind 250 degrees at 12 knots" says nothing about runs on its own. What matters
is the wind relative to the line from home plate to centre field. MLB publishes
that as `venue.location.azimuthAngle` (Yankee Stadium 75.0, PNC Park 116.0), so

    relative bearing = (wind_from_bearing - azimuth) normalised to +/-180

and the component of the wind blowing from home plate towards centre field --
"blowing out" -- is `-cos(relative)` times the speed. Positive is out, negative
is in. This is the only place in the brief where two sources have to be
combined to mean anything, and it is the reason `azimuthAngle` is worth having.
"""
from __future__ import annotations

import json
import math
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://aviationweather.gov/api/data"
UA = "trading-research/1.0 (personal research)"
HDR = {"User-Agent": UA}
STATION_MAP = Path(__file__).resolve().parent.parent / "data" / "venue_stations.json"


def _get(url, tries=4, timeout=45):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HDR)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:                        # noqa: BLE001
            last = e
            if i < tries - 1:
                time.sleep(1.5 * (2 ** i))
    raise RuntimeError(f"aviationweather failed: {url}: {last}")


def _haversine_km(a_lat, a_lon, b_lat, b_lon):
    r = 6371.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp = math.radians(b_lat - a_lat)
    dl = math.radians(b_lon - a_lon)
    h = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(h))


# ------------------------------------------------------- station discovery

def _load_map():
    if STATION_MAP.exists():
        try:
            return json.loads(STATION_MAP.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def _save_map(m):
    STATION_MAP.parent.mkdir(parents=True, exist_ok=True)
    STATION_MAP.write_text(json.dumps(m, indent=2))


def station_for(venue_id, lat, lon, box_deg=0.6):
    """Nearest TAF-issuing airport to a ballpark. Discovered once, then cached.

    Two steps because the two endpoints answer different questions: the METAR
    bbox query says which stations exist near here, and `stationinfo` says
    which of them issue a TAF. A station that only issues METAR gives observed
    weather but no forecast, which is no use for a decision taken hours before
    first pitch.
    """
    m = _load_map()
    key = str(venue_id)
    if key in m:
        return m[key]
    bbox = f"{lat - box_deg},{lon - box_deg},{lat + box_deg},{lon + box_deg}"
    near = _get(f"{BASE}/metar?bbox={bbox}&format=json")
    ids = []
    for row in near:
        i = row.get("icaoId")
        if i and i not in ids:
            ids.append(i)
    if not ids:
        raise RuntimeError(f"no METAR station within {box_deg} deg of "
                           f"venue {venue_id}")
    info = _get(f"{BASE}/stationinfo?ids={','.join(ids[:40])}&format=json")
    best = None
    for s in info:
        if "TAF" not in (s.get("siteType") or []):
            continue
        d = _haversine_km(lat, lon, s["lat"], s["lon"])
        if best is None or d < best["distance_km"]:
            best = {"icao": s["icaoId"], "site": s.get("site"),
                    "lat": s["lat"], "lon": s["lon"],
                    "distance_km": round(d, 1)}
    if best is None:
        raise RuntimeError(f"no TAF station near venue {venue_id}")
    m[key] = best
    _save_map(m)
    return best


# ------------------------------------------------------------- the forecast

def taf(icao):
    rows = _get(f"{BASE}/taf?ids={icao}&format=json")
    return rows[0] if rows else None


def metar(icao):
    rows = _get(f"{BASE}/metar?ids={icao}&format=json&taf=false")
    return rows[0] if rows else None


def _fcst_at(t, at_epoch):
    """The TAF period covering `at_epoch`, ignoring PROB/TEMPO groups.

    A TAF is a base forecast plus conditional amendments. A PROB30 group is a
    30% chance, not a forecast, and treating it as one would make every windy
    possibility look certain. Those groups are returned separately so a caller
    can see them without them contaminating the base numbers.
    """
    base, cond = None, []
    for f in (t.get("fcsts") or []):
        tf, tt = f.get("timeFrom"), f.get("timeTo")
        if tf is None or tt is None or not (tf <= at_epoch < tt):
            continue
        if f.get("fcstChange") in ("PROB", "TEMPO") or f.get("probability"):
            cond.append(f)
        else:
            base = f
    return base, cond


def forecast(venue, at: datetime):
    """Wind, temperature and rain risk at a ballpark at a given instant.

    `venue` is the dict from `statsapi.venue()`. Returns None for any quantity
    the forecast does not cover, never a zero.
    """
    if venue.get("lat") is None or venue.get("lon") is None:
        return {"available": False, "reason": "venue has no coordinates"}
    st = station_for(venue["id"], venue["lat"], venue["lon"])
    at_epoch = int(at.timestamp())
    t = taf(st["icao"])
    obs = metar(st["icao"])
    out = {
        "available": bool(t or obs),
        "station": st["icao"], "station_site": st["site"],
        "station_distance_km": st["distance_km"],
        "roof": venue.get("roof"),
        "elevation_ft": venue.get("elevation_ft"),
        "azimuth_deg": venue.get("azimuth_deg"),
        "source": "aviationweather.gov (NOAA AWC) METAR+TAF",
        "obs_temp_c": (obs or {}).get("temp"),
        "obs_wdir_deg": (obs or {}).get("wdir"),
        "obs_wspd_kt": (obs or {}).get("wspd"),
        "obs_time": (obs or {}).get("reportTime"),
        "fcst_temp_c": None, "fcst_wdir_deg": None, "fcst_wspd_kt": None,
        "fcst_gust_kt": None, "fcst_wx": None, "fcst_issue_time": None,
        "prob_groups": [],
    }
    if t:
        base, cond = _fcst_at(t, at_epoch)
        out["fcst_issue_time"] = t.get("issueTime")
        if base:
            out["fcst_wdir_deg"] = base.get("wdir")
            out["fcst_wspd_kt"] = base.get("wspd")
            out["fcst_gust_kt"] = base.get("wgst")
            out["fcst_wx"] = base.get("wxString")
            temps = base.get("temp") or []
            if temps:
                out["fcst_temp_c"] = temps[0].get("sfcTemp")
        out["prob_groups"] = [
            {"probability": c.get("probability"), "wx": c.get("wxString"),
             "wspd": c.get("wspd"), "wdir": c.get("wdir")} for c in cond]

    wdir = out["fcst_wdir_deg"] if out["fcst_wdir_deg"] is not None \
        else out["obs_wdir_deg"]
    wspd = out["fcst_wspd_kt"] if out["fcst_wspd_kt"] is not None \
        else out["obs_wspd_kt"]
    # A TAF runs ~24-30 h from issue, so a game more than a day out falls off
    # the end of it and there is no forecast at all. Recorded explicitly: a
    # brief built at T-48 h has OBSERVED weather, which is not a forecast of
    # anything, and any mentality that uses wind must decline rather than
    # pretend. `wind_used` is the flag the decision rules read.
    out["wind_used"] = ("forecast" if out["fcst_wspd_kt"] is not None
                        else ("observed" if out["obs_wspd_kt"] is not None
                              else "none"))
    out["taf_covers_game_time"] = out["fcst_wspd_kt"] is not None
    out.update(wind_components(wdir, wspd, venue.get("azimuth_deg")))
    # A closed roof makes every wind number irrelevant, and saying so is more
    # useful than silently reporting a breeze that never reaches the field.
    if (venue.get("roof") or "").lower() in ("dome", "retractable", "closed",
                                             "indoor", "fixed"):
        out["wind_out_kt"] = None
        out["wind_note"] = f"roof = {venue.get('roof')}; wind not applied"
    return out


def wind_components(wdir_deg, wspd_kt, azimuth_deg):
    """Split the wind into 'blowing out' and 'cross' relative to centre field.

    METAR/TAF wind direction is the direction the wind blows FROM. The park's
    azimuth is the bearing from home plate to centre field. Wind blowing out to
    centre therefore comes FROM the opposite of the azimuth, so

        out_component = -cos(wind_from - azimuth) * speed

    which is positive when the wind is at the batter's back. A calm wind
    (wdir 0, wspd 0 in METAR) yields 0.0, correctly.
    """
    if wdir_deg is None or wspd_kt is None or azimuth_deg is None:
        return {"wind_out_kt": None, "wind_cross_kt": None,
                "wind_rel_deg": None}
    # 'VRB' is a real METAR/TAF value meaning the direction is variable -- it
    # is not missing data and it is not a number. A variable wind has no
    # resolvable out/in component, so the components are None while the SPEED
    # is still reported. float('VRB') raised ValueError and killed the run.
    try:
        wd = float(wdir_deg)
    except (TypeError, ValueError):
        return {"wind_out_kt": None, "wind_cross_kt": None,
                "wind_rel_deg": None, "wind_variable": True}
    rel = (wd - float(azimuth_deg) + 180.0) % 360.0 - 180.0
    rad = math.radians(rel)
    return {
        "wind_rel_deg": round(rel, 1),
        "wind_out_kt": round(-math.cos(rad) * float(wspd_kt), 2),
        "wind_cross_kt": round(math.sin(rad) * float(wspd_kt), 2),
    }


if __name__ == "__main__":
    import statsapi as S
    from datetime import timedelta
    gs = S.schedule(datetime.now(timezone.utc).date() + timedelta(days=1))
    for g in gs[:6]:
        v = S.venue(g["venue"]["id"])
        at = datetime.fromisoformat(g["gameDate"].replace("Z", "+00:00"))
        try:
            f = forecast(v, at)
        except RuntimeError as e:
            print(f"{v['name']:<26} ERR {e}")
            continue
        print(f"{v['name']:<26} {f['station']} {f['station_distance_km']}km "
              f"roof={f['roof']} az={f['azimuth_deg']} "
              f"wind={f['fcst_wdir_deg']}deg/{f['fcst_wspd_kt']}kt "
              f"({f['wind_used']}) OUT={f['wind_out_kt']}kt "
              f"T={f['fcst_temp_c'] or f['obs_temp_c']}C "
              f"elev={f['elevation_ft']}ft wx={f['fcst_wx']}")
