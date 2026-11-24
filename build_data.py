"""Télécharge le dernier run commun ECMWF (IFS open data) + GFS et écrit site/data.json.

Usage : python build_data.py [--out site/data.json] [--max-step 240]
Le run choisi est le plus récent (00 ou 12 UTC) disponible jusqu'à +max-step chez les deux modèles.
"""
import argparse, base64, json, os, sys, urllib.request, urllib.error
import concurrent.futures as cf
import datetime as dt
import numpy as np
import eccodes
from ecmwf.opendata import Client

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "site", "data.json"))
ap.add_argument("--max-step", type=int, default=240)
args = ap.parse_args()

STEPS = [s for s in list(range(0, 145, 3)) + list(range(150, 241, 6)) if s <= args.max_step]
LATS = np.arange(60, 35.99, -0.5)
LONS = np.arange(-15, 25.01, 0.5)
ri = np.round((90 - LATS) / 0.25).astype(int)
ci = np.round((LONS % 360) / 0.25).astype(int) % 1440
ci_ec = np.round(((LONS - 180) % 360) / 0.25).astype(int) % 1440  # grille ECMWF open data commence à 180° E
GFS = "https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.%s/%02d/atmos/gfs.t%02dz.pgrb2.0p25.f%03d"


def log(*a):
    print(*a, flush=True)


def gfs_ready(day, hh, step):
    try:
        urllib.request.urlopen(urllib.request.Request((GFS % (day, hh, hh, step)) + ".idx", method="HEAD"), timeout=30)
        return True
    except urllib.error.URLError:
        return False


# --- choix du run -----------------------------------------------------------
c = Client(source="ecmwf")
ec_latest = c.latest(type="fc", stream="oper", step=STEPS[-1], param="2t")
run = ec_latest.replace(minute=0, second=0, microsecond=0)
for _ in range(4):
    if run.hour in (0, 12) and gfs_ready(run.strftime("%Y%m%d"), run.hour, STEPS[-1]):
        break
    run -= dt.timedelta(hours=12) if run.hour in (0, 12) else dt.timedelta(hours=run.hour % 12)
else:
    sys.exit("Aucun run commun ECMWF/GFS trouvé")
DATE, HH = run.strftime("%Y%m%d"), run.hour
log("run choisi :", DATE, "%02d UTC" % HH, "| ECMWF le plus récent :", ec_latest)

out = {m: {k: np.zeros((len(STEPS), len(LATS), len(LONS)), dtype=np.float32)
           for k in ["t2m", "t850", "u10", "v10", "msl", "pr", "cloud"]} for m in ("ecmwf", "gfs")}


def sample(vals, cols):
    return np.asarray(vals, dtype=np.float64).reshape(721, 1440)[np.ix_(ri, cols)]


# --- ECMWF ------------------------------------------------------------------
c.retrieve(date=DATE, time=HH, type="fc", stream="oper", step=STEPS,
           param=["2t", "10u", "10v", "msl", "tp", "tcc"], target="ec_sfc.grib2")
c.retrieve(date=DATE, time=HH, type="fc", stream="oper", step=STEPS,
           param="t", levtype="pl", levelist=850, target="ec_pl.grib2")
log("ECMWF téléchargé")

tp = {}
for f in ["ec_sfc.grib2", "ec_pl.grib2"]:
    with open(f, "rb") as fh:
        while True:
            g = eccodes.codes_grib_new_from_file(fh)
            if g is None:
                break
            sn, st, lev = (eccodes.codes_get(g, k) for k in ("shortName", "step", "level"))
            if st in STEPS:
                i = STEPS.index(st)
                v = sample(eccodes.codes_get_values(g), ci_ec)
                if sn == "2t": out["ecmwf"]["t2m"][i] = v - 273.15
                elif sn == "10u": out["ecmwf"]["u10"][i] = v
                elif sn == "10v": out["ecmwf"]["v10"][i] = v
                elif sn == "msl": out["ecmwf"]["msl"][i] = v / 100
                elif sn == "t" and lev == 850: out["ecmwf"]["t850"][i] = v - 273.15
                elif sn == "tcc": out["ecmwf"]["cloud"][i] = v
                elif sn == "tp": tp[st] = v
            eccodes.codes_release(g)
for f in ["ec_sfc.grib2", "ec_pl.grib2"]:
    try:
        os.remove(f)
    except OSError:
        pass
prev = None
for i, st in enumerate(STEPS):  # tp cumulée -> mm/h
    cur = tp.get(st, prev)
    if i > 0 and prev is not None and cur is not None:
        out["ecmwf"]["pr"][i] = np.maximum(cur - prev, 0) * 1000 / (st - STEPS[i - 1])
    prev = cur
log("ECMWF lu ; échéances de pluie :", len(tp))

# --- GFS (téléchargement partiel via .idx + Range) ---------------------------
PAT = {"t2m": ":TMP:2 m above ground:", "u10": ":UGRD:10 m above ground:", "v10": ":VGRD:10 m above ground:",
       "msl": ":PRMSL:mean sea level:", "t850": ":TMP:850 mb:", "pr": ":PRATE:surface:", "cloud": ":TCDC:entire atmosphere:"}


def fetch(url, headers=None, tries=4):
    for t in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=90).read()
        except Exception:
            if t == tries - 1:
                raise


def do_step(st):
    base = GFS % (DATE, HH, HH, st)
    idx = fetch(base + ".idx").decode().splitlines()
    res = {}
    for k, p in PAT.items():
        for j, l in enumerate(idx):
            if p in l:
                a = int(l.split(":")[1])
                b = int(idx[j + 1].split(":")[1]) - 1 if j + 1 < len(idx) else ""
                g = eccodes.codes_new_from_message(fetch(base, {"Range": "bytes=%d-%s" % (a, b)}))
                res[k] = sample(eccodes.codes_get_values(g), ci)
                eccodes.codes_release(g)
                break
    return st, res


with cf.ThreadPoolExecutor(8) as ex:
    for st, res in ex.map(do_step, STEPS):
        i = STEPS.index(st)
        for k, v in res.items():
            out["gfs"][k][i] = v - 273.15 if k in ("t2m", "t850") else v / 100 if k == "msl" else v * 3600 if k == "pr" else v
for m in out:  # nébulosité en % (ECMWF peut être en fraction 0-1) ; GFS peut manquer à +0
    cl = out[m]["cloud"]
    if cl.max() <= 1.01:
        cl *= 100
    if len(STEPS) > 1 and not cl[0].any():
        cl[0] = cl[1]
log("GFS lu")

# --- écriture ---------------------------------------------------------------
SC = {"t2m": 100, "t850": 100, "u10": 100, "v10": 100, "msl": 10, "pr": 1000, "cloud": 10}
payload = {"steps": STEPS, "lats": [float(x) for x in LATS], "lons": [float(x) for x in LONS],
           "run": run.strftime("%Y-%m-%dT%H:00:00Z"),
           "built": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "scale": SC, "data": {}}
for m in out:
    payload["data"][m] = {k: base64.b64encode(np.clip(np.round(a * SC[k]), -32768, 32767).astype("<i2").tobytes()).decode()
                          for k, a in out[m].items()}
os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
tmp = args.out + ".tmp"
with open(tmp, "w") as fh:
    json.dump(payload, fh, separators=(",", ":"))
os.replace(tmp, args.out)
for m in out:
    for k, a in out[m].items():
        log(m, k, round(float(a.min()), 2), round(float(a.max()), 2))
# garde-fou : pression moyenne plausible pour les deux modèles
for m in out:
    p = float(out[m]["msl"][0].mean())
    if not 990 < p < 1035:
        sys.exit("Pression moyenne anormale pour %s : %.1f hPa" % (m, p))
log("écrit :", args.out)
