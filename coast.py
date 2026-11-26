"""Côtes et frontières Natural Earth, découpées et simplifiées -> site/coast.json (Europe, 50 m)
et site/coast_world.json (monde, 110 m). À lancer une seule fois (fichiers versionnés). Dépendance : shapely."""
import json, os, urllib.request
from shapely.geometry import box, shape

URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_%s_%s.geojson"


def lines(name, res="50m", bb=box(-15.5, 35.5, 25.5, 60.5), tol=0.03, nd=2):
    out = []
    gj = json.load(urllib.request.urlopen(URL % (res, name), timeout=120))
    for f in gj["features"]:
        g = shape(f["geometry"]).intersection(bb)
        if g.is_empty:
            continue
        for p in (g.geoms if hasattr(g, "geoms") else [g]):
            if p.geom_type != "LineString":
                continue
            out.append([[round(x, nd), round(y, nd)] for x, y in p.simplify(tol).coords])
    return out


site = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")
os.makedirs(site, exist_ok=True)
for fn, kw in (("coast.json", {}), ("coast_world.json", dict(res="110m", bb=box(-180, -90, 180, 90), tol=0.1, nd=1))):
    d = {"coast": lines("coastline", **kw), "borders": lines("admin_0_boundary_lines_land", **kw)}
    json.dump(d, open(os.path.join(site, fn), "w"), separators=(",", ":"))
    print(fn, len(d["coast"]), len(d["borders"]))
