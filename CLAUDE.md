# Météo perso (appli PWA pour Samsung)

- Ludo, Billy-le-Grand (49.06 N, 4.47 E). Répondre en français, clair et direct. Pas de fichiers Office.
- Ne pas lire `site/data.json` (8 Mo, régénéré, non versionné).

## Fichiers
- `build_data.py` : choisit le dernier run commun ECMWF/GFS (00 ou 12 UTC), télécharge, écrit `site/data.json` (Int16 base64, grille 0,5°, 65 échéances : 3 h jusqu'à +144 h puis 6 h jusqu'à +240 h). Test rapide : `--max-step 12`.
- `coast.py`, `icons.py` : à relancer seulement si on change la zone ou l'icône (résultats versionnés).
- `site/` : `index.html` (tout le JS, sans bibliothèque), `sw.js` (hors connexion, réseau d'abord), `manifest.webmanifest`.
- `.github/workflows/update.yml` : 08:40, 20:40 et 02:20 UTC, régénère et publie sur GitHub Pages.

## Pièges
- Grille ECMWF open data commence à 180° E (décalage des colonnes). `tp` ECMWF cumulée. GFS `PRATE` absent à +0.
- Heures en Europe/Paris via Intl (format fr « 0 h » : utiliser parseInt).

## À faire ensuite (ordre)
1. Correction locale (biais par modèle vs station Châlons-Vatry ; test sur historique Open-Meteo).
2. Ensembles ECMWF ENS / GEFS : fourchettes et probabilités à 7-14 jours.
3. Radar 0-2 h (RainViewer). 4. Fiabilité mesurée. 5. Plus beau (fond de carte, isolignes). 6. Alléger data.json.
