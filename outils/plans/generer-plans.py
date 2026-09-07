#!/usr/bin/env python3
"""Génère un plan par salle de kiosque, la salle concernée mise en évidence.

Hors chaîne de production : ce script n'est pas exécuté par le CI et demande
Pillow + numpy (`pip install Pillow numpy`). Il ne sert qu'à régénérer les
images si le plan du Business Center change ou si le rendu doit être ajusté.

Les dix zones ont été relevées par segmentation de la couleur magenta du plan
(#DF2E85), qui distingue les salles de kiosques des autres espaces : SUMIDA et
ALZETTE sont violettes, GARONNE bleu foncé, SEINE et DONAU vertes. Les
coordonnées sont figées ici plutôt que redétectées à chaque exécution : un
changement de plan doit être constaté et revu, pas absorbé en silence.
"""
from PIL import Image, ImageDraw
import numpy as np
import pathlib

RACINE = pathlib.Path(__file__).resolve().parents[2]
SOURCE = pathlib.Path(__file__).with_name('plan-rez-de-jardin-source.png')
SORTIE = RACINE / 'worker' / 'public' / 'assets' / 'plans'

# (identifiant de fichier, nom affiché, x0, y0, x1, y1)
SALLES = [
    ('moselle', 'MOSELLE', 175,  59, 208, 131),
    ('liffey',  'LIFFEY',  175, 136, 208, 208),
    ('loire',   'LOIRE',   249, 111, 316, 208),
    ('tajo',    'TAJO',    460, 110, 526, 208),
    ('tevere',  'TEVERE',  712, 210, 786, 254),
    ('adige',   'ADIGE',   712, 259, 797, 328),
    ('douro',   'DOURO',   406, 384, 472, 464),
    ('rhone',   'RHÔNE',   529, 385, 594, 464),
    ('wisla',   'WISLA',   182, 537, 284, 596),
    ('rhin',    'RHIN',    182, 601, 284, 667),
]

ENCRE = (26, 26, 46)   # --te-dark de la page programme
# Le reste du plan est éclairci sans disparaître : la salle doit sauter aux
# yeux, mais les escaliers, les sanitaires et l'entrée servent à s'orienter.
ESTOMPE = 0.62


def main():
    base = Image.open(SOURCE).convert('RGB')
    arr = np.asarray(base).astype(float)
    fond = Image.fromarray(
        np.clip(255 - (255 - arr) * (1 - ESTOMPE), 0, 255).astype(np.uint8))

    SORTIE.mkdir(parents=True, exist_ok=True)
    for slug, nom, x0, y0, x1, y1 in SALLES:
        img = fond.copy()
        img.paste(base.crop((x0, y0, x1 + 1, y1 + 1)), (x0, y0))

        d = ImageDraw.Draw(img)
        # Halo blanc puis anneau sombre : l'anneau doit se détacher aussi bien
        # du magenta de la salle que du gris du plan.
        d.rounded_rectangle([x0 - 6, y0 - 6, x1 + 6, y1 + 6],
                            radius=8, outline=(255, 255, 255), width=6)
        d.rounded_rectangle([x0 - 11, y0 - 11, x1 + 11, y1 + 11],
                            radius=11, outline=ENCRE, width=5)

        # Aplats vectoriels : 128 couleurs suffisent et divisent le poids par
        # deux et demi, sans perte visible.
        cible = SORTIE / f'plan-{slug}.png'
        img.convert('P', palette=Image.ADAPTIVE, colors=128).save(
            cible, optimize=True)
        print(f'{cible.relative_to(RACINE)}  ({nom})')


if __name__ == '__main__':
    main()
