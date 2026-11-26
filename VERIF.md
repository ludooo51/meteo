# Vérification sur un an : ECMWF et GFS contre la réalité

Période : 2025-11-25 au 2026-11-24. Vérité : Météo-France, station VATRY-AERO (48.777 N, 4.165 E). Prévisions : Open-Meteo Previous Runs (même point).

Méthode : on apprend les biais sur une semaine sur deux et on mesure le gain sur les autres semaines (jamais vues).
Erreur = écart moyen absolu. J+0 = prévision du jour même, J+3 = faite 3 jours avant.

## Température 2 m (°C)

| Échéance | Modèle | Biais moyen | Erreur brute | Erreur corrigée | + Lune |
|---|---|---|---|---|---|
| J+0 | ECMWF | 0,30 | 0,87 | **0,78** | 0,78 |
| J+0 | GFS | 0,17 | 1,15 | **1,07** | 1,08 |
| J+1 | ECMWF | 0,16 | 1,06 | **0,97** | 0,98 |
| J+1 | GFS | 0,06 | 1,36 | **1,28** | 1,30 |
| J+2 | ECMWF | 0,08 | 1,16 | **1,11** | 1,12 |
| J+2 | GFS | -0,04 | 1,43 | **1,33** | 1,33 |
| J+3 | ECMWF | -0,03 | 1,28 | **1,24** | 1,25 |
| J+3 | GFS | -0,14 | 1,58 | **1,52** | 1,52 |
| J+4 | ECMWF | -0,01 | 1,44 | **1,41** | 1,41 |
| J+4 | GFS | -0,06 | 1,77 | **1,70** | 1,72 |
| J+5 | ECMWF | -0,11 | 1,78 | **1,74** | 1,74 |
| J+5 | GFS | -0,00 | 2,02 | **1,99** | 2,04 |
| J+6 | ECMWF | -0,08 | 2,19 | **2,11** | 2,14 |
| J+6 | GFS | 0,18 | 2,31 | **2,28** | 2,30 |
| J+7 | ECMWF | -0,04 | 2,34 | **2,23** | 2,31 |
| J+7 | GFS | 0,29 | 2,63 | **2,65** | 2,66 |

Meilleur mélange (part d'ECMWF, après correction) : J+0 80 % (erreur 0,76), J+1 80 % (erreur 0,93), J+2 70 % (erreur 1,06), J+3 80 % (erreur 1,19), J+4 70 % (erreur 1,36), J+5 70 % (erreur 1,63), J+6 60 % (erreur 1,93), J+7 70 % (erreur 2,13)

Lune : aucun gain mesurable hors échantillon (écart moyen -0,02 °C), termes mis à zéro dans l'appli.

## Vent 10 m (m/s)

| Échéance | Modèle | Biais moyen | Erreur brute | Erreur corrigée | + Lune |
|---|---|---|---|---|---|
| J+0 | ECMWF | -0,94 | 1,15 | **0,84** | 0,85 |
| J+0 | GFS | -0,42 | 0,90 | **0,84** | 0,84 |
| J+1 | ECMWF | -0,93 | 1,19 | **0,92** | 0,93 |
| J+1 | GFS | -0,36 | 1,00 | **0,97** | 0,97 |
| J+2 | ECMWF | -0,97 | 1,26 | **1,00** | 1,00 |
| J+2 | GFS | -0,38 | 1,11 | **1,06** | 1,07 |
| J+3 | ECMWF | -1,01 | 1,36 | **1,10** | 1,11 |
| J+3 | GFS | -0,38 | 1,18 | **1,15** | 1,17 |
| J+4 | ECMWF | -1,00 | 1,45 | **1,20** | 1,20 |
| J+4 | GFS | -0,45 | 1,39 | **1,33** | 1,35 |
| J+5 | ECMWF | -0,94 | 1,54 | **1,40** | 1,41 |
| J+5 | GFS | -0,42 | 1,52 | **1,52** | 1,52 |
| J+6 | ECMWF | -1,00 | 1,78 | **1,65** | 1,65 |
| J+6 | GFS | -0,45 | 1,68 | **1,65** | 1,66 |
| J+7 | ECMWF | -1,03 | 1,89 | **1,81** | 1,83 |
| J+7 | GFS | -0,31 | 1,87 | **1,88** | 1,89 |

Meilleur mélange (part d'ECMWF, après correction) : J+0 50 % (erreur 0,77), J+1 60 % (erreur 0,87), J+2 60 % (erreur 0,94), J+3 60 % (erreur 1,03), J+4 60 % (erreur 1,15), J+5 60 % (erreur 1,32), J+6 50 % (erreur 1,48), J+7 50 % (erreur 1,66)

Lune : aucun gain mesurable hors échantillon (écart moyen -0,01 m/s), termes mis à zéro dans l'appli.

## Pluie (cumul par jour)

| Échéance | Modèle | Jours | Erreur (mm/j) | Rapport cumul prévu/observé | Jour de pluie ≥ 1 mm bien prévu |
|---|---|---|---|---|---|
| J+0 | ECMWF | 356 | 0,98 | 1,36 | 87 % |
| J+0 | GFS | 356 | 1,04 | 1,25 | 87 % |
| J+1 | ECMWF | 356 | 1,11 | 1,33 | 88 % |
| J+1 | GFS | 356 | 1,11 | 1,20 | 87 % |
| J+2 | ECMWF | 356 | 1,17 | 1,32 | 86 % |
| J+2 | GFS | 356 | 1,29 | 1,35 | 85 % |
| J+3 | ECMWF | 356 | 1,26 | 1,37 | 85 % |
| J+3 | GFS | 356 | 1,26 | 1,26 | 85 % |
| J+4 | ECMWF | 356 | 1,47 | 1,42 | 82 % |
| J+4 | GFS | 356 | 1,49 | 1,29 | 80 % |
| J+5 | ECMWF | 350 | 1,30 | 1,17 | 80 % |
| J+5 | GFS | 356 | 1,33 | 0,79 | 80 % |
| J+6 | ECMWF | 356 | 1,56 | 1,32 | 74 % |
| J+6 | GFS | 356 | 1,49 | 0,72 | 78 % |
| J+7 | ECMWF | 350 | 1,89 | 1,39 | 73 % |
| J+7 | GFS | 356 | 1,36 | 0,61 | 77 % |
