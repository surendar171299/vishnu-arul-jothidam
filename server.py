#!/usr/bin/env python3
import os
import json
import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from pathlib import Path
import swisseph as swe

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8000"))
BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"

swe.set_sid_mode(swe.SIDM_LAHIRI)

RASHIS = ["மேஷம்","ரிஷபம்","மிதுனம்","கடகம்","சிம்மம்","கன்னி","துலாம்","விருச்சிகம்","தனுசு","மகரம்","கும்பம்","மீனம்"]
NAKSHATRAS = ["அஸ்வினி","பரணி","கார்த்திகை","ரோகிணி","மிருகசீரிஷம்","திருவாதிரை","புனர்பூசம்","பூசம்","ஆயில்யம்","மகம்","பூரம்","உத்திரம்","ஹஸ்தம்","சித்திரை","சுவாதி","விசாகம்","அனுஷம்","கேட்டை","மூலம்","பூராடம்","உத்திராடம்","திருவோணம்","அவிட்டம்","சதயம்","பூரட்டாதி","உத்திரட்டாதி","ரேவதி"]
DASHA_LORDS = ["கேது","சுக்கிரன்","சூரியன்","சந்திரன்","செவ்வாய்","ராகு","குரு","சனி","புதன்"]
DASHA_YEARS = {"கேது":7,"சுக்கிரன்":20,"சூரியன்":6,"சந்திரன்":10,"செவ்வாய்":7,"ராகு":18,"குரு":16,"சனி":19,"புதன்":17}
PLANETS = [("சூரியன்",swe.SUN),("சந்திரன்",swe.MOON),("செவ்வாய்",swe.MARS),("புதன்",swe.MERCURY),("குரு",swe.JUPITER),("சுக்கிரன்",swe.VENUS),("சனி",swe.SATURN),("ராகு",swe.TRUE_NODE)]

def norm(x): return x % 360.0
def rasi_index(lon): return int(norm(lon) // 30)

def dms(x):
    x = norm(x)
    d = int(x)
    m = int((x-d)*60)
    s = round((((x-d)*60)-m)*60)
    if s == 60: s=0; m+=1
    if m == 60: m=0; d+=1
    return f'{d}° {m}\\' {s}"'

def nakshatra(lon):
    span = 360.0/27.0
    idx = min(26, int(norm(lon)//span))
    pada = min(4, int(((norm(lon)-idx*span)/(span/4)))+1)
    return idx, pada

def julian_day(date_s, time_s, tz_hours):
    dt = datetime.datetime.fromisoformat(f"{date_s}T{time_s}")
    utc = dt - datetime.timedelta(hours=float(tz_hours))
    return swe.julday(utc.year, utc.month, utc.day,
                      utc.hour + utc.minute/60 + utc.second/3600)

def planet_position(jd, planet):
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    xx, _ = swe.calc_ut(jd, planet, flags)
    return norm(xx[0]), xx[3]

def make_planet(name, lon, speed):
    ni, pada = nakshatra(lon)
    return {
        "name": name,
        "longitude": lon,
        "degree": dms(lon),
        "rasi": RASHIS[rasi_index(lon)],
        "rasiIndex": rasi_index(lon),
        "nakshatra": NAKSHATRAS[ni],
        "pada": pada,
        "retrograde": speed < 0
    }

def calculate(req):
    jd = julian_day(req["dob"], req["time"], req.get("timezone", 5.5))
    lat = float(req["latitude"])
    lon = float(req["longitude"])

    # Sidereal Lahiri ascendant.
    _, ascmc = swe.houses_ex(jd, lat, lon, b"P", swe.FLG_SIDEREAL)
    asc = norm(ascmc[0])
    asc_rasi = rasi_index(asc)

    planets = []
    for name, planet in PLANETS:
        p, speed = planet_position(jd, planet)
        planets.append(make_planet(name, p, speed))

    rahu_lon = planets[-1]["longitude"]
    planets.append(make_planet("கேது", norm(rahu_lon + 180), -1))

    moon = next(p for p in planets if p["name"] == "சந்திரன்")
    ni, pada = nakshatra(moon["longitude"])
    lord = DASHA_LORDS[ni % 9]

    # Whole-sign houses.
    houses = [
        {"house": i+1, "rasi": RASHIS[(asc_rasi+i)%12],
         "rasiIndex": (asc_rasi+i)%12}
        for i in range(12)
    ]

    # South Indian sign chart.
    chart = [[] for _ in range(12)]
    for p in planets:
        chart[p["rasiIndex"]].append(p["name"])

    # Navamsa sign placements.
    navamsa = []
    for p in planets:
        sign = p["rasiIndex"]
        deg = p["longitude"] % 30
        part = min(8, int(deg / (30/9)))
        if sign % 3 == 0:
            start = sign
        elif sign % 3 == 1:
            start = (sign + 4) % 12
        else:
            start = (sign + 8) % 12
        ns = (start + part) % 12
        navamsa.append({"name": p["name"], "rasi": RASHIS[ns], "rasiIndex": ns})

    # Dasha sequence from Moon's nakshatra.
    span = 360/27
    within = moon["longitude"] % span
    elapsed = within/span
    first_balance = DASHA_YEARS[lord] * (1-elapsed)
    start_idx = DASHA_LORDS.index(lord)
    dasha = []
    for k in range(9):
        dl = DASHA_LORDS[(start_idx+k)%9]
        years = first_balance if k == 0 else DASHA_YEARS[dl]
        dasha.append({"lord": dl, "years": round(years, 3)})

    return {
        "ok": True,
        "input": req,
        "lagna": {"longitude": asc, "degree": dms(asc),
                  "rasi": RASHIS[asc_rasi], "rasiIndex": asc_rasi},
        "rasi": moon["rasi"],
        "rasiIndex": moon["rasiIndex"],
        "nakshatra": NAKSHATRAS[ni],
        "pada": pada,
        "nakshatraLord": lord,
        "planets": planets,
        "rasiChart": chart,
        "navamsa": navamsa,
        "houses": houses,
        "dasha": dasha,
        "engine": "Swiss Ephemeris / Lahiri"
    }

class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, code, content_type, data):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS,HEAD")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def send_json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_bytes(code, "application/json; charset=utf-8", data)

    def do_OPTIONS(self):
        self.send_json(200, {"ok": True})

    def do_HEAD(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html", "/api/health"):
            self.send_bytes(200, "text/html; charset=utf-8", b"")
        else:
            self.send_bytes(404, "text/plain; charset=utf-8", b"")

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/health":
            return self.send_json(200, {
                "ok": True,
                "engine": "Swiss Ephemeris",
                "ayanamsha": "Lahiri"
            })

        if path in ("/", "/index.html"):
            try:
                data = INDEX_FILE.read_bytes()
                return self.send_bytes(200, "text/html; charset=utf-8", data)
            except Exception as e:
                return self.send_json(500, {"ok": False, "error": str(e)})

        return self.send_json(404, {"ok": False, "error": "Not found"})

    def do_POST(self):
        if urlparse(self.path).path != "/api/jathagam":
            return self.send_json(404, {"ok": False, "error": "Not found"})

        try:
            length = int(self.headers.get("Content-Length", "0"))
            req = json.loads(self.rfile.read(length))

            for key in ("dob", "time", "latitude", "longitude"):
                if req.get(key) in (None, ""):
                    raise ValueError(f"Missing {key}")

            return self.send_json(200, calculate(req))
        except Exception as e:
            return self.send_json(400, {"ok": False, "error": str(e)})

if __name__ == "__main__":
    print(f"Starting Vishnu Arul Jothidam on {HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
