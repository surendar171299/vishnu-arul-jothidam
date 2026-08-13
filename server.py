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

RASHIS = [
    "மேஷம்", "ரிஷபம்", "மிதுனம்", "கடகம்", "சிம்மம்", "கன்னி",
    "துலாம்", "விருச்சிகம்", "தனுசு", "மகரம்", "கும்பம்", "மீனம்"
]

NAKSHATRAS = [
    "அஸ்வினி", "பரணி", "கார்த்திகை", "ரோகிணி", "மிருகசீரிஷம்",
    "திருவாதிரை", "புனர்பூசம்", "பூசம்", "ஆயில்யம்", "மகம்",
    "பூரம்", "உத்திரம்", "ஹஸ்தம்", "சித்திரை", "சுவாதி",
    "விசாகம்", "அனுஷம்", "கேட்டை", "மூலம்", "பூராடம்",
    "உத்திராடம்", "திருவோணம்", "அவிட்டம்", "சதயம்",
    "பூரட்டாதி", "உத்திரட்டாதி", "ரேவதி"
]

DASHA_LORDS = ["கேது", "சுக்கிரன்", "சூரியன்", "சந்திரன்", "செவ்வாய்", "ராகு", "குரு", "சனி", "புதன்"]
DASHA_YEARS = {
    "கேது": 7, "சுக்கிரன்": 20, "சூரியன்": 6, "சந்திரன்": 10,
    "செவ்வாய்": 7, "ராகு": 18, "குரு": 16, "சனி": 19, "புதன்": 17
}

PLANETS = [
    ("சூரியன்", swe.SUN),
    ("சந்திரன்", swe.MOON),
    ("செவ்வாய்", swe.MARS),
    ("புதன்", swe.MERCURY),
    ("குரு", swe.JUPITER),
    ("சுக்கிரன்", swe.VENUS),
    ("சனி", swe.SATURN),
    ("ராகு", swe.TRUE_NODE)
]

def norm(value):
    return value % 360.0

def rasi_index(longitude):
    return int(norm(longitude) // 30)

def dms(value):
    value = norm(value)
    degrees = int(value)
    minutes_float = (value - degrees) * 60
    minutes = int(minutes_float)
    seconds = round((minutes_float - minutes) * 60)
    if seconds == 60:
        seconds = 0
        minutes += 1
    if minutes == 60:
        minutes = 0
        degrees += 1
    return f"{degrees}° {minutes}' {seconds}″"

def get_nakshatra(longitude):
    span = 360.0 / 27.0
    index = min(26, int(norm(longitude) // span))
    pada = min(4, int(((norm(longitude) - index * span) / (span / 4))) + 1)
    return index, pada

def julian_day(date_string, time_string, timezone_hours):
    local_dt = datetime.datetime.fromisoformat(f"{date_string}T{time_string}")
    utc_dt = local_dt - datetime.timedelta(hours=float(timezone_hours))
    return swe.julday(
        utc_dt.year,
        utc_dt.month,
        utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60 + utc_dt.second / 3600
    )

def planet_position(jd, planet):
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    values, _ = swe.calc_ut(jd, planet, flags)
    return norm(values[0]), values[3]

def make_planet(name, longitude, speed):
    nak_index, pada = get_nakshatra(longitude)
    return {
        "name": name,
        "longitude": longitude,
        "degree": dms(longitude),
        "rasi": RASHIS[rasi_index(longitude)],
        "rasiIndex": rasi_index(longitude),
        "nakshatra": NAKSHATRAS[nak_index],
        "pada": pada,
        "retrograde": speed < 0
    }

def calculate_jathagam(req):
    jd = julian_day(
        req["dob"],
        req["time"],
        req.get("timezone", 5.5)
    )

    latitude = float(req["latitude"])
    longitude = float(req["longitude"])

    _, ascmc = swe.houses_ex(
        jd,
        latitude,
        longitude,
        b"P",
        swe.FLG_SIDEREAL
    )

    ascendant = norm(ascmc[0])
    ascendant_rasi = rasi_index(ascendant)

    planets = []

    for name, planet in PLANETS:
        longitude_value, speed = planet_position(jd, planet)
        planets.append(
            make_planet(name, longitude_value, speed)
        )

    rahu_longitude = planets[-1]["longitude"]
    planets.append(
        make_planet("கேது", norm(rahu_longitude + 180), -1)
    )

    moon = next(
        planet for planet in planets
        if planet["name"] == "சந்திரன்"
    )

    nak_index, pada = get_nakshatra(moon["longitude"])
    nakshatra_lord = DASHA_LORDS[nak_index % 9]

    houses = []
    for i in range(12):
        houses.append({
            "house": i + 1,
            "rasi": RASHIS[(ascendant_rasi + i) % 12],
            "rasiIndex": (ascendant_rasi + i) % 12
        })

    rasi_chart = [[] for _ in range(12)]
    for planet in planets:
        rasi_chart[planet["rasiIndex"]].append(planet["name"])

    navamsa = []

    for planet in planets:
        sign = planet["rasiIndex"]
        degree_in_sign = planet["longitude"] % 30
        part = min(8, int(degree_in_sign / (30 / 9)))

        if sign % 3 == 0:
            start_sign = sign
        elif sign % 3 == 1:
            start_sign = (sign + 4) % 12
        else:
            start_sign = (sign + 8) % 12

        navamsa_sign = (start_sign + part) % 12

        navamsa.append({
            "name": planet["name"],
            "rasi": RASHIS[navamsa_sign],
            "rasiIndex": navamsa_sign
        })

    nakshatra_span = 360.0 / 27.0
    position_inside_nakshatra = moon["longitude"] % nakshatra_span
    elapsed_fraction = position_inside_nakshatra / nakshatra_span

    first_dasha_balance = DASHA_YEARS[nakshatra_lord] * (1 - elapsed_fraction)
    first_index = DASHA_LORDS.index(nakshatra_lord)

    dasha = []

    for i in range(9):
        lord = DASHA_LORDS[(first_index + i) % 9]
        years = first_dasha_balance if i == 0 else DASHA_YEARS[lord]
        dasha.append({
            "lord": lord,
            "years": round(years, 3)
        })

    return {
        "ok": True,
        "input": req,
        "lagna": {
            "longitude": ascendant,
            "degree": dms(ascendant),
            "rasi": RASHIS[ascendant_rasi],
            "rasiIndex": ascendant_rasi
        },
        "rasi": moon["rasi"],
        "rasiIndex": moon["rasiIndex"],
        "nakshatra": NAKSHATRAS[nak_index],
        "pada": pada,
        "nakshatraLord": nakshatra_lord,
        "planets": planets,
        "rasiChart": rasi_chart,
        "navamsa": navamsa,
        "houses": houses,
        "dasha": dasha,
        "engine": "Swiss Ephemeris / Lahiri"
    }

class Handler(BaseHTTPRequestHandler):

    def send_bytes(self, status, content_type, data):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()

        if self.command != "HEAD":
            self.wfile.write(data)

    def send_json(self, status, data):
        body = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_bytes(
            status,
            "application/json; charset=utf-8",
            body
        )

    def do_OPTIONS(self):
        self.send_json(200, {"ok": True})

    def do_HEAD(self):
        path = urlparse(self.path).path

        if path in ("/", "/index.html"):
            self.send_bytes(
                200,
                "text/html; charset=utf-8",
                b""
            )
        elif path == "/api/health":
            self.send_bytes(
                200,
                "application/json; charset=utf-8",
                b""
            )
        else:
            self.send_bytes(
                404,
                "text/plain; charset=utf-8",
                b""
            )

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/health":
            return self.send_json(
                200,
                {
                    "ok": True,
                    "engine": "Swiss Ephemeris",
                    "ayanamsha": "Lahiri"
                }
            )

        if path in ("/", "/index.html"):
            try:
                body = INDEX_FILE.read_bytes()
                return self.send_bytes(
                    200,
                    "text/html; charset=utf-8",
                    body
                )
            except Exception as error:
                return self.send_json(
                    500,
                    {
                        "ok": False,
                        "error": str(error)
                    }
                )

        return self.send_json(
            404,
            {
                "ok": False,
                "error": "Not found"
            }
        )

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/api/jathagam":
            return self.send_json(
                404,
                {
                    "ok": False,
                    "error": "Not found"
                }
            )

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )

            raw_body = self.rfile.read(content_length)
            request_data = json.loads(raw_body)

            required = [
                "dob",
                "time",
                "latitude",
                "longitude"
            ]

            for field in required:
                if request_data.get(field) in (None, ""):
                    raise ValueError(
                        f"Missing {field}"
                    )

            result = calculate_jathagam(request_data)

            return self.send_json(200, result)

        except Exception as error:
            return self.send_json(
                400,
                {
                    "ok": False,
                    "error": str(error)
                }
            )

if __name__ == "__main__":
    print(
        f"Vishnu Arul Jothidam server listening on "
        f"{HOST}:{PORT}"
    )

    server = ThreadingHTTPServer(
        (HOST, PORT),
        Handler
    )

    server.serve_forever()
