"""Vérification sur un an : prévisions ECMWF et GFS archivées contre la station réelle la plus proche.

Sorties :
- VERIF.md            : le bilan lisible (erreurs par échéance, gain de la correction, effet de la Lune).
- site/correction.json: biais par modèle / échéance / saison / créneau de 3 h, poids du mélange, termes lunaires.

Sources : Open-Meteo Previous Runs API (prévisions passées J+0 à J+7), Météo-France (données horaires
de la Marne, data.gouv.fr) ; repli Meteostat puis ERA5 si la station n'est pas trouvée.
Usage : python verify.py [--days 365]
"""
import argparse, datetime as dt, gzip, io, json, math, os, re, sys, urllib.request
import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--days", type=int, default=365)
args = ap.parse_args()

ROOT = os.path.dirname(os.path.abspath(__file__))
HOME = (49.06, 4.47)                       # Billy-le-Grand
VATRY = (48.776, 4.184)                    # Châlons-Vatry
MODELS = {"ecmwf": "ecmwf_ifs025", "gfs": "gfs_global"}
LEADS = list(range(0, 8))                  # J+0 .. J+7
VARS = {"t2m": "temperature_2m", "wind": "wind_speed_10m", "pr": "precipitation"}
END = dt.date.today() - dt.timedelta(days=2)
START = END - dt.timedelta(days=args.days - 1)
UA = {"User-Agent": "meteo-perso-verif/1.0"}


def log(*a):
    print(*a, flush=True)


def get(url, tries=4):
    for t in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300).read()
        except Exception as e:
            log("  essai", t + 1, "échoué :", e)
            if t == tries - 1:
                raise


# --- observations ------------------------------------------------------------
def obs_meteofrance():
    meta = json.loads(get("https://www.data.gouv.fr/api/1/datasets/donnees-climatologiques-de-base-horaires/"))
    res = [r for r in meta["resources"] if re.search(r"H_51_.*\.csv\.gz$", r.get("title", "") + r.get("url", ""))]
    keep = []
    for r in res:
        yrs = [int(y) for y in re.findall(r"(?<!\d)(\d{4})(?!\d)", r["title"])]
        if "latest" in r["title"] or (yrs and max(yrs) >= START.year):
            keep.append(r)
    if not keep:
        raise RuntimeError("aucun fichier Météo-France pour la Marne")
    frames = []
    for r in keep:
        log("  Météo-France :", r["title"])
        df = pd.read_csv(io.BytesIO(gzip.decompress(get(r["url"]))), sep=";", low_memory=False,
                         usecols=lambda c: c in ("NUM_POSTE", "NOM_USUEL", "LAT", "LON", "AAAAMMJJHH", "RR1", "FF", "T"))
        frames.append(df)
    df = pd.concat(frames)
    df = df[df["T"].notna()]
    vat = df[df["NOM_USUEL"].astype(str).str.contains("VATRY", case=False)]
    if vat.empty:  # sinon la station la plus proche de Vatry
        st = df.groupby("NUM_POSTE")[["LAT", "LON"]].first()
        d = (st.LAT - VATRY[0]) ** 2 + ((st.LON - VATRY[1]) * math.cos(math.radians(49))) ** 2
        vat = df[df.NUM_POSTE == d.idxmin()]
    name, lat, lon = vat.NOM_USUEL.iloc[0], float(vat.LAT.iloc[0]), float(vat.LON.iloc[0])
    t = pd.to_datetime(vat.AAAAMMJJHH.astype(int).astype(str), format="%Y%m%d%H", utc=True)
    o = pd.DataFrame({"t2m": vat["T"].values, "wind": vat["FF"].values, "pr": vat["RR1"].values}, index=t)
    return "Météo-France, station %s (%.3f N, %.3f E)" % (name, lat, lon), lat, lon, o


def obs_meteostat():
    raw = gzip.decompress(get("https://bulk.meteostat.net/v2/hourly/07139.csv.gz")).decode()
    df = pd.read_csv(io.StringIO(raw), header=None)
    t = pd.to_datetime(df[0] + " " + df[1].astype(str).str.zfill(2), format="%Y-%m-%d %H", utc=True)
    o = pd.DataFrame({"t2m": df[2].values, "wind": df[8].values / 3.6, "pr": df[5].values}, index=t)
    return "Meteostat, station 07139 Châlons-Vatry", VATRY[0], VATRY[1], o


def obs_era5():
    j = json.loads(get("https://archive-api.open-meteo.com/v1/archive?latitude=%.3f&longitude=%.3f&start_date=%s&end_date=%s"
                       "&hourly=temperature_2m,wind_speed_10m,precipitation&wind_speed_unit=ms&timezone=GMT"
                       % (VATRY[0], VATRY[1], START, END)))
    h = j["hourly"]
    o = pd.DataFrame({"t2m": h["temperature_2m"], "wind": h["wind_speed_10m"], "pr": h["precipitation"]},
                     index=pd.to_datetime(h["time"], utc=True))
    return "ERA5 (réanalyse, pas une station)", VATRY[0], VATRY[1], o


SRC = None
for f in (obs_meteofrance, obs_meteostat, obs_era5):
    try:
        SRC, LAT, LON, OBS = f()
        OBS = OBS[(OBS.index >= pd.Timestamp(START, tz="UTC")) & (OBS.index < pd.Timestamp(END + dt.timedelta(days=1), tz="UTC"))]
        if OBS["t2m"].notna().sum() > 24 * 90:
            break
        log("  trop peu d'observations avec", f.__name__, ":", OBS["t2m"].notna().sum())
    except Exception as e:
        log("  source", f.__name__, "indisponible :", e)
else:
    sys.exit("Aucune observation exploitable")
OBS = OBS[~OBS.index.duplicated()]
log("observations :", SRC, "|", OBS["t2m"].notna().sum(), "heures")


# --- prévisions archivées ----------------------------------------------------
def fc_chunk(a, b):
    hv = ",".join(v + ("" if L == 0 else "_previous_day%d" % L) for v in VARS.values() for L in LEADS)
    url = ("https://previous-runs-api.open-meteo.com/v1/forecast?latitude=%.3f&longitude=%.3f&start_date=%s&end_date=%s"
           "&hourly=%s&models=%s&wind_speed_unit=ms&timezone=GMT" % (LAT, LON, a, b, hv, ",".join(MODELS.values())))
    h = json.loads(get(url))["hourly"]
    return pd.DataFrame({k: v for k, v in h.items() if k != "time"}, index=pd.to_datetime(h["time"], utc=True))


parts, a = [], START
while a <= END:
    b = min(END, a + dt.timedelta(days=89))
    log("prévisions", a, "->", b)
    parts.append(fc_chunk(a, b))
    a = b + dt.timedelta(days=1)
FC = pd.concat(parts)
FC = FC[~FC.index.duplicated()]


def col(m, k, L):
    return VARS[k] + ("" if L == 0 else "_previous_day%d" % L) + "_" + MODELS[m]


# --- tableau long : une ligne par (modèle, échéance, heure) -------------------
rows = []
idx = FC.index.intersection(OBS.index)
idx = idx[idx.hour % 3 == 0]  # ECMWF open data : pas de 3 h ; on compare sur les mêmes heures pour les deux
for m in MODELS:
    for L in LEADS:
        d = pd.DataFrame(index=idx)
        d["m"], d["L"] = m, L
        for k in VARS:
            c = col(m, k, L)
            d["f_" + k] = FC.loc[idx, c].values if c in FC else np.nan
            d["o_" + k] = OBS.loc[idx, k].values
        rows.append(d)
D = pd.concat(rows)
D["season"] = ((D.index.month % 12) // 3)          # 0 hiver, 1 printemps, 2 été, 3 automne (UTC)
D["slot"] = D.index.hour // 3
D["test"] = (D.index.isocalendar().week.values % 2) == 1
# phase de la Lune : 0 = nouvelle lune, pi = pleine lune (lunaison moyenne, précise à ~1 jour)
ref = pd.Timestamp("2000-01-06 18:14", tz="UTC")
D["phi"] = 2 * np.pi * (((D.index - ref).total_seconds() / 86400 / 29.530588853) % 1)
log("lignes :", len(D))


def bias_table(d, k):
    e = (d["f_" + k] - d["o_" + k]).rename("e")
    return e.groupby([d.m, d.L, d.season, d.slot]).mean()


def apply_bias(d, k, tab):
    key = pd.MultiIndex.from_arrays([d.m, d.L, d.season, d.slot])
    b = tab.reindex(key).fillna(0).values
    return d["f_" + k].values - b


report = {}
for k in ("t2m", "wind"):
    ok = D["f_" + k].notna() & D["o_" + k].notna()
    d = D[ok].copy()
    tr, te = d[~d.test], d[d.test]
    tab = bias_table(tr, k)
    te = te.assign(c=apply_bias(te, k, tab))
    te["raw_e"] = (te["f_" + k] - te["o_" + k]).abs()
    te["cor_e"] = (te.c - te["o_" + k]).abs()
    # Lune : régression des résidus corrigés sur cos/sin de la phase, apprise sur la moitié « entraînement »
    tr = tr.assign(res=(apply_bias(tr, k, tab) - tr["o_" + k]))
    moon = {}
    for (m, L), g in tr.groupby(["m", "L"]):
        X = np.c_[np.cos(g.phi), np.sin(g.phi), np.cos(2 * g.phi), np.sin(2 * g.phi)]
        moon[(m, L)] = np.linalg.lstsq(X, g.res.values, rcond=None)[0]
    X = np.c_[np.cos(te.phi), np.sin(te.phi), np.cos(2 * te.phi), np.sin(2 * te.phi)]
    coef = np.array([moon[(m, L)] for m, L in zip(te.m, te.L)])
    te["moon_e"] = (te.c - (X * coef).sum(1) - te["o_" + k]).abs()
    s = te.groupby(["m", "L"]).agg(n=("raw_e", "size"), raw=("raw_e", "mean"), cor=("cor_e", "mean"), moon=("moon_e", "mean"))
    s["bias"] = (te["f_" + k] - te["o_" + k]).groupby([te.m, te.L]).mean()
    # meilleur mélange ECMWF / GFS (après correction) par échéance
    piv = te.reset_index().pivot_table(index=["index", "L"], columns="m", values="c")
    obs = te[te.m == "ecmwf"].reset_index().set_index(["index", "L"])["o_" + k]
    piv = piv.join(obs).dropna()
    mix = {}
    for L, g in piv.groupby(level="L"):
        best = min((abs(w * g.ecmwf + (1 - w) * g.gfs - g["o_" + k]).mean(), w) for w in np.linspace(0, 1, 11))
        mix[int(L)] = (round(float(best[1]), 1), float(best[0]))
    report[k] = (s, mix)
    # tables finales sur toute l'année
    full = bias_table(d, k)
    d2 = d.assign(res=apply_bias(d, k, full) - d["o_" + k])
    mfull = {}
    for (m, L), g in d2.groupby(["m", "L"]):
        X = np.c_[np.cos(g.phi), np.sin(g.phi), np.cos(2 * g.phi), np.sin(2 * g.phi)]
        mfull[(m, L)] = np.linalg.lstsq(X, g.res.values, rcond=None)[0]
    report[k] += (full, mfull)

# pluie : cumuls journaliers et jours de pluie (>= 1 mm)
PR = {}
for m in MODELS:
    for L in LEADS:
        c = col(m, "pr", L)
        if c not in FC:
            continue
        f = FC[c].resample("1D").sum(min_count=20)
        o = OBS["pr"].resample("1D").sum(min_count=20)
        j = pd.concat([f, o], axis=1, keys=["f", "o"]).dropna()
        if len(j) < 30:
            continue
        hit = ((j.f >= 1) == (j.o >= 1)).mean()
        PR[(m, L)] = (len(j), (j.f - j.o).abs().mean(), j.f.sum() / max(j.o.sum(), 1e-6), hit)


# --- écriture ----------------------------------------------------------------
def moon_ok(k):
    s = report[k][0]
    return bool((s.moon < s.cor).mean() > 0.5 and (s.cor - s.moon).mean() > 0.005)


corr = {"source": SRC, "lat": LAT, "lon": LON, "radius_km": 60, "period": [str(START), str(END)],
        "built": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "valeur corrigée = prévision - biais[modèle][J][saison][créneau 3 h UTC] - lune ; saison 0 = déc-fév",
        "bias": {}, "mix": {}, "moon": {}, "moon_used": {}}
for k in ("t2m", "wind"):
    s, mix, full, mfull = report[k]
    corr["mix"][k] = {str(L): w for L, (w, _) in mix.items()}
    corr["moon_used"][k] = moon_ok(k)
    corr["bias"][k], corr["moon"][k] = {}, {}
    for m in MODELS:
        arr = np.zeros((len(LEADS), 4, 8))
        for (mm, L, se, sl), v in full.items():
            if mm == m:
                arr[L, se, sl] = round(float(v), 2)
        corr["bias"][k][m] = arr.tolist()
        corr["moon"][k][m] = [[round(float(x), 3) for x in mfull.get((m, L), np.zeros(4))] for L in LEADS]
json.dump(corr, open(os.path.join(ROOT, "site", "correction.json"), "w"), separators=(",", ":"))

f2 = lambda x: ("%.2f" % x).replace(".", ",")
L_ = lambda L: "J+%d" % L
md = ["# Vérification sur un an : ECMWF et GFS contre la réalité", "",
      "Période : %s au %s. Vérité : %s. Prévisions : Open-Meteo Previous Runs (même point)." % (START, END, SRC), "",
      "Méthode : on apprend les biais sur une semaine sur deux et on mesure le gain sur les autres semaines (jamais vues).",
      "Erreur = écart moyen absolu. J+0 = prévision du jour même, J+3 = faite 3 jours avant.", ""]
for k, nm, u in (("t2m", "Température 2 m", "°C"), ("wind", "Vent 10 m", "m/s")):
    s, mix = report[k][0], report[k][1]
    md += ["## %s (%s)" % (nm, u), "", "| Échéance | Modèle | Biais moyen | Erreur brute | Erreur corrigée | + Lune |", "|---|---|---|---|---|---|"]
    for L in LEADS:
        for m in MODELS:
            if (m, L) in s.index:
                r = s.loc[(m, L)]
                md.append("| %s | %s | %s | %s | **%s** | %s |" % (L_(L), m.upper(), f2(r.bias), f2(r.raw), f2(r.cor), f2(r.moon)))
    md += ["", "Meilleur mélange (part d'ECMWF, après correction) : " +
           ", ".join("%s %d %% (erreur %s)" % (L_(L), w * 100, f2(e)) for L, (w, e) in sorted(mix.items())), "",
           "Lune : %s" % ("améliore un peu la prévision hors échantillon, termes utilisés." if moon_ok(k) else
                          "aucun gain mesurable hors échantillon (écart moyen %s %s), termes mis à zéro dans l'appli."
                          % (f2((s.cor - s.moon).mean()), u)), ""]
md += ["## Pluie (cumul par jour)", "", "| Échéance | Modèle | Jours | Erreur (mm/j) | Rapport cumul prévu/observé | Jour de pluie ≥ 1 mm bien prévu |", "|---|---|---|---|---|---|"]
for (m, L), (n, e, ra, h) in sorted(PR.items(), key=lambda x: (x[0][1], x[0][0])):
    md.append("| %s | %s | %d | %s | %s | %d %% |" % (L_(L), m.upper(), n, f2(e), f2(ra), round(h * 100)))
open(os.path.join(ROOT, "VERIF.md"), "w").write("\n".join(md) + "\n")
log("\n".join(md))
