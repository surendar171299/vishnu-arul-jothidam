#!/usr/bin/env python3
import json, math, datetime, io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import swisseph as swe

HOST, PORT = "127.0.0.1", 8000
swe.set_sid_mode(swe.SIDM_LAHIRI)

RASHIS = ["மேஷம்","ரிஷபம்","மிதுனம்","கடகம்","சிம்மம்","கன்னி","துலாம்","விருச்சிகம்","தனுசு","மகரம்","கும்பம்","மீனம்"]
NAK = ["அஸ்வினி","பரணி","கார்த்திகை","ரோகிணி","மிருகசீரிஷம்","திருவாதிரை","புனர்பூசம்","பூசம்","ஆயில்யம்","மகம்","பூரம்","உத்திரம்","ஹஸ்தம்","சித்திரை","சுவாதி","விசாகம்","அனுஷம்","கேட்டை","மூலம்","பூராடம்","உத்திராடம்","திருவோணம்","அவிட்டம்","சதயம்","பூரட்டாதி","உத்திரட்டாதி","ரேவதி"]
LORDS = ["கேது","சுக்கிரன்","சூரியன்","சந்திரன்","செவ்வாய்","ராகு","குரு","சனி","புதன்"]
PLANETS = [("சூரியன்",swe.SUN),("சந்திரன்",swe.MOON),("செவ்வாய்",swe.MARS),("புதன்",swe.MERCURY),("குரு",swe.JUPITER),("சுக்கிரன்",swe.VENUS),("சனி",swe.SATURN),("ராகு",swe.TRUE_NODE)]

def norm(x): return x % 360
def rasi(lon): return int(norm(lon)//30)
def dms(x):
    x=norm(x); d=int(x); m=int((x-d)*60); s=round((((x-d)*60)-m)*60)
    if s==60: s=0; m+=1
    if m==60: m=0; d+=1
    return f"{d}° {m}' {s}\""

def nakshatra(lon):
    span=360/27; i=min(26,int(norm(lon)//span))
    pada=min(4,int((norm(lon)-i*span)/(span/4))+1)
    return i,pada

def jd(date_s,time_s,tz):
    dt=datetime.datetime.fromisoformat(date_s+"T"+time_s)
    u=dt-datetime.timedelta(hours=float(tz))
    return swe.julday(u.year,u.month,u.day,u.hour+u.minute/60+u.second/3600)

def pos(j, planet):
    xx,_=swe.calc_ut(j,planet,swe.FLG_SWIEPH|swe.FLG_SIDEREAL|swe.FLG_SPEED)
    return norm(xx[0]),xx[3]

def add_planet(name,lon,speed):
    ni,pa=nakshatra(lon)
    return {"name":name,"longitude":lon,"degree":dms(lon),"rasi":RASHIS[rasi(lon)],
            "rasiIndex":rasi(lon),"nakshatra":NAK[ni],"pada":pa,"retrograde":speed<0}

def calc(req):
    j=jd(req["dob"],req["time"],req.get("timezone",5.5))
    lat=float(req["latitude"]); lon=float(req["longitude"])
    cusps,ascmc=swe.houses_ex(j,lat,lon,b'P',swe.FLG_SIDEREAL)
    asc=norm(ascmc[0]); ar=rasi(asc)
    planets=[]
    for n,p in PLANETS:
        x,s=pos(j,p); planets.append(add_planet(n,x,s))
    rahu=planets[-1]["longitude"]; planets.append(add_planet("கேது",norm(rahu+180),-1))
    moon=next(x for x in planets if x["name"]=="சந்திரன்")
    ni,pa=nakshatra(moon["longitude"])

    # Whole-sign chart positions, useful for a clear South Indian style chart.
    chart=[[] for _ in range(12)]
    for p in planets: chart[p["rasiIndex"]].append(p["name"])
    # Navamsa: each 30° sign divided into 9; movable/fixed/dual starting rule.
    # start sign for each sign: movable=same, fixed=5th, dual=9th.
    nav=[]
    for p in planets:
        sign=p["rasiIndex"]; deg=p["longitude"]%30
        part=min(8,int(deg/(30/9)))
        mode=sign%3
        start=sign if mode==0 else ((sign+4)%12 if mode==1 else (sign+8)%12)
        ns=(start+part)%12
        nav.append({"name":p["name"],"rasi":RASHIS[ns],"rasiIndex":ns})

    # Vimshottari dasha seed: remaining balance from Moon nakshatra.
    years={"கேது":7,"சுக்கிரன்":20,"சூரியன்":6,"சந்திரன்":10,"செவ்வாய்":7,"ராகு":18,"குரு":16,"சனி":19,"புதன்":17}
    lord=LORDS[ni] if False else LORDS[ni]
    span=360/27; within=moon["longitude"]%span; elapsed=within/span
    balance=years[lord]*(1-elapsed)
    dasha=[]
    order=LORDS[:]
    idx=order.index(lord)
    birth=datetime.datetime.fromisoformat(req["dob"]+"T"+req["time"])
    for k in range(9):
        dl=order[(idx+k)%9]
        yrs=balance if k==0 else years[dl]
        dasha.append({"lord":dl,"years":round(yrs,3)})
    houses=[{"house":i+1,"rasi":RASHIS[(ar+i)%12],"rasiIndex":(ar+i)%12} for i in range(12)]

    return {"ok":True,"input":req,"lagna":{"longitude":asc,"degree":dms(asc),"rasi":RASHIS[ar],"rasiIndex":ar},
            "rasi":moon["rasi"],"rasiIndex":moon["rasiIndex"],"nakshatra":NAK[ni],"pada":pa,"nakshatraLord":lord,
            "planets":planets,"rasiChart":chart,"navamsa":nav,"houses":houses,"dasha":dasha,
            "engine":"Swiss Ephemeris / Lahiri"}

class H(BaseHTTPRequestHandler):
    def json(self,code,obj):
        b=json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin","*"); self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS"); self.end_headers(); self.wfile.write(b)
    def do_OPTIONS(self): self.json(200,{"ok":True})
    def do_GET(self):
        if urlparse(self.path).path=="/api/health": return self.json(200,{"ok":True,"engine":"Swiss Ephemeris","ayanamsha":"Lahiri"})
        self.json(404,{"ok":False,"error":"Not found"})
    def do_POST(self):
        if urlparse(self.path).path!="/api/jathagam": return self.json(404,{"ok":False,"error":"Not found"})
        try:
            n=int(self.headers.get("Content-Length","0")); req=json.loads(self.rfile.read(n))
            for k in ["dob","time","latitude","longitude"]:
                if req.get(k) in [None,""]: raise ValueError("Missing "+k)
            self.json(200,calc(req))
        except Exception as e: self.json(400,{"ok":False,"error":str(e)})

if __name__=="__main__":
    print("Jathagam API: http://127.0.0.1:8000")
    ThreadingHTTPServer((HOST,PORT),H).serve_forever()
