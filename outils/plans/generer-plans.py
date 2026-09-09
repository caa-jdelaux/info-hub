#!/usr/bin/env python3
"""Prépare le plan du rez-de-jardin servi par la page programme.

Hors chaîne de production : ce script n'est pas exécuté par le CI et demande
Pillow + numpy (`pip install Pillow numpy`). Il ne sert qu'à régénérer les
images si le plan du Business Center change.

Deux sorties, deux usages différents :

  worker/public/assets/plans/rez-de-jardin.png
      Le plan nu, servi tel quel par la page. La mise en évidence d'une salle
      est dessinée par-dessus en SVG, dans la page — une seule image sert donc
      toutes les salles, et l'anneau reste net à n'importe quel zoom.

  outils/plans/apercus/plan-<salle>.png
      Une image par salle, gravée. Sert de référence visuelle et de contrôle
      des coordonnées ; la page ne les charge pas.

Les zones ont été relevées par segmentation de couleur : magenta (#DF2E85)
pour les dix salles repérées d'abord, violet (#7E76A1) pour Sumida et Alzette,
vert foncé (#006A4E) pour Donau. Garonne, mitoyenne de Sumida et Alzette, et
l'auditorium Seine restent hors liste : aucun kiosque ne s'y tient. Les
coordonnées sont figées ici plutôt que redétectées à chaque exécution : un
changement de plan doit être constaté et revu, pas absorbé en silence. Elles
sont reprises à l'identique dans la table PLAN_SALLES de la page.
"""
from PIL import Image, ImageDraw
import numpy as np
import pathlib

RACINE = pathlib.Path(__file__).resolve().parents[2]
SOURCE = pathlib.Path(__file__).with_name('plan-rez-de-jardin-source.png')
PLAN_SERVI = RACINE / 'worker' / 'public' / 'assets' / 'plans' / 'rez-de-jardin.png'
APERCUS = pathlib.Path(__file__).with_name('apercus')

# (identifiant, nom affiché, x0, y0, x1, y1)
SALLES = [
    ('moselle', 'MOSELLE', 175,  59, 208, 131),
    ('liffey',  'LIFFEY',  175, 136, 208, 208),
    ('loire',   'LOIRE',   249, 111, 316, 208),
    ('tajo',    'TAJO',    460, 110, 526, 208),
    ('tevere',  'TEVERE',  712, 210, 786, 254),
    ('adige',   'ADIGE',   712, 259, 797, 328),
    ('douro',   'DOURO',   406, 384, 472, 464),
    ('rhone',   'RHÔNE',   529, 385, 594, 464),
    ('donau',   'DONAU',   406, 468, 595, 527),
    ('wisla',   'WISLA',   182, 537, 284, 596),
    ('rhin',    'RHIN',    182, 601, 284, 667),
    ('sumida',  'SUMIDA',  717, 542, 753, 580),
    ('alzette', 'ALZETTE', 719, 584, 758, 622),
]

ENCRE = (26, 26, 46)   # --te-dark de la page programme
# Le reste du plan est éclairci sans disparaître : la salle doit sauter aux
# yeux, mais les escaliers, les sanitaires et l'entrée servent à s'orienter.
ESTOMPE = 0.62
# Aplats vectoriels : 64 couleurs suffisent et divisent le poids par deux et
# demi, sans perte visible.
PALETTE = 64


def main():
    base = Image.open(SOURCE).convert('RGB')
    print(f'plan source {base.width}x{base.height}')

    PLAN_SERVI.parent.mkdir(parents=True, exist_ok=True)
    base.convert('P', palette=Image.ADAPTIVE, colors=PALETTE).save(
        PLAN_SERVI, optimize=True)
    print(f'{PLAN_SERVI.relative_to(RACINE)}  {PLAN_SERVI.stat().st_size / 1024:.1f} Ko')

    arr = np.asarray(base).astype(float)
    fond = Image.fromarray(
        np.clip(255 - (255 - arr) * (1 - ESTOMPE), 0, 255).astype(np.uint8))

    APERCUS.mkdir(parents=True, exist_ok=True)
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
        img.convert('P', palette=Image.ADAPTIVE, colors=128).save(
            APERCUS / f'plan-{slug}.png', optimize=True)
    print(f'{len(SALLES)} aperçus dans {APERCUS.relative_to(RACINE)}/')


if __name__ == '__main__':
    main()
