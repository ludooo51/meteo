"""Côtes et frontières Natural Earth 50 m, découpées sur la zone et simplifiées -> site/coast.json.
À lancer une seule fois (le fichier est versionné). Dépendance : shapely."""
import json, os, urllib.request
from shapely.geometry import box, shape

URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_%s.geojson"
bb = box(-15.5, 35.5, 25.5, 60.5)


def lines(name):
    out = []
    gj = json.load(urllib.request.urlopen(URL % name, timeout=120))
    for f in gj["features"]:
        g = shape(f["geometry"]).intersection(bb)
        if g.is_empty:
            continue
        for p in (g.geoms if hasattr(g, "geoms") else [g]):
            if p.geom_type != "LineString":
                continue
            out.append([[round(x, 2), round(y, 2)] for x, y in p.simplify(0.03).coords])
    return out


d = {"coast": lines("coastline"), "borders": lines("admin_0_boundary_lines_land")}
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site", "coast.json")
os.makedirs(os.path.dirname(path), exist_ok=True)
json.dump(d, open(path, "w"), separators=(",", ":"))
print(len(d["coast"]), len(d["borders"]), "->", path)
