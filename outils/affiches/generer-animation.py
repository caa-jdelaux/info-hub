#!/usr/bin/env python3
"""L'animation de la page de garde : un balayage lumineux sur le logo.

Hors chaîne de production : ce script n'est pas exécuté par le CI et demande
Pillow, pymupdf et ffmpeg.

Le mouvement dure 2,6 secondes, puis l'image reste fixe 27,4 secondes avant de
recommencer. C'est la traduction de « en boucle, mais pas trop constant » :
sur trente secondes d'affichage, il ne se passe quelque chose que pendant
deux. Le reste du temps, c'est une page de garde immobile.

Deux sorties, deux usages :

  couverture-logo.gif
      Le bloc du logo seul, aux dimensions exactes qu'il occupe sur la diapo 1.
      C'est lui qui est posé dans le PPTX : un GIF animé boucle tout seul, sans
      réglage de lecture automatique ni de répétition — donc sans rien qui
      puisse ne pas se déclencher le jour J. Le reste de la couverture (la
      signature, la date, le QR) reste du texte natif.

  couverture-testing-event.mp4
      La couverture entière en 1920 x 1080, pour un écran ou un lecteur vidéo.
      Elle est composée à partir de la page 1 du PDF de la présentation, ce qui
      garantit qu'elle montre exactement la diapo et non une reconstitution.

Le balayage est découpé sur l'alpha du logo : la lumière ne passe que sur les
lettres, jamais sur le fond. Un reflet qui déborderait sur le fond marine
trahirait le calque.

La pause est écrite comme une suite d'images identiques de deux secondes. Le
codeur GIF de Pillow les fusionne en une seule image à longue temporisation —
c'est la forme compacte normale, et le contrôle en fin de script vérifie qu'elle
dure bien ce qu'elle doit durer. Je n'ai pas pu tester le rendu dans PowerPoint
depuis cet environnement : si l'animation s'y remettait à tourner en boucle
rapide, ce serait que le lecteur plafonne le délai, et le contournement serait
de rendre les images de pause imperceptiblement différentes pour empêcher la
fusion.
"""
import argparse
import math
import pathlib
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

RACINE = pathlib.Path(__file__).resolve().parents[2]
RES = pathlib.Path(__file__).parent / 'ressources'
LOGO = RES / 'logo-testing-event.png'
DECK_PDF = pathlib.Path(__file__).parent / 'presentation-testing-event.pdf'
SORTIE = pathlib.Path(__file__).parent

ENCRE = (26, 26, 46)

# Le bloc du logo sur la diapo 1 : 15,0 x 3,25 cm, rendu à 200 ppp.
GIF_L, GIF_H = 1181, 256
MOUVEMENT_S = 2.6
IMAGES_MOUVEMENT = 26     # 100 ms par image, pile
PAUSE_S = 27.4
PAUSE_PAS_S = 2.0


def balayage(base, logo_alpha, position, largeur=0.30, intensite=0.85):
    """Superpose une bande lumineuse à `base`, découpée sur l'alpha du logo.

    `position` va de 0 (bande hors cadre à gauche) à 1 (hors cadre à droite).
    """
    L, H = base.size
    marge = int(L * 0.55)
    cx = int(-marge + position * (L + 2 * marge))
    demi = max(4, int(L * largeur / 2))

    bande = Image.new('L', (L, H), 0)
    trace = ImageDraw.Draw(bande)
    penche = int(H * 0.9)
    for k in range(-demi, demi + 1):
        v = int(255 * math.exp(-(k / (demi / 1.9)) ** 2))
        if v:
            trace.line([(cx + k + penche, -10), (cx + k - penche, H + 10)], fill=v, width=3)
    bande = bande.filter(ImageFilter.GaussianBlur(max(4, L // 90)))

    lumiere = Image.composite(bande, Image.new('L', (L, H), 0), logo_alpha)
    lumiere = lumiere.point(lambda v: int(v * intensite))
    return Image.composite(Image.new('RGB', (L, H), (255, 255, 255)), base, lumiere)


def images_du_mouvement(base, logo_alpha, n=IMAGES_MOUVEMENT):
    return [balayage(base, logo_alpha, i / (n - 1)) for i in range(n)]


def faire_gif():
    logo = Image.open(LOGO).convert('RGBA').resize((GIF_L, GIF_H), Image.LANCZOS)
    base = Image.new('RGB', (GIF_L, GIF_H), ENCRE)
    base.paste(logo, (0, 0), logo)
    alpha = logo.split()[3]

    images = images_du_mouvement(base, alpha)
    durees = [int(MOUVEMENT_S * 1000 / len(images))] * len(images)
    # La dernière image de pause absorbe le reste, pour que le total tombe
    # juste : 13 x 2 s + 1,4 s = 27,4 s, et non 14 x 2 s = 28 s.
    pleins = int(PAUSE_S // PAUSE_PAS_S)
    reste = int(round((PAUSE_S - pleins * PAUSE_PAS_S) * 1000))
    durees_pause = [int(PAUSE_PAS_S * 1000)] * pleins + ([reste] if reste else [])
    images += [base.copy() for _ in durees_pause]
    durees += durees_pause

    chemin = SORTIE / 'couverture-logo.gif'
    # 64 couleurs faisaient apparaître des bandes diagonales dans le
    # dégradé du balayage : le reflet doit être lisse, c'est tout son effet.
    palette = images[len(images) // 3].convert('P', palette=Image.ADAPTIVE, colors=200)
    cadres = [im.quantize(palette=palette, dither=Image.NONE) for im in images]
    cadres[0].save(chemin, save_all=True, append_images=cadres[1:],
                   duration=durees, loop=0, optimize=True, disposal=1)
    with Image.open(chemin) as ecrit:
        ecrites = ecrit.n_frames
    return chemin, ecrites, sum(durees) / 1000


def faire_mp4():
    if not DECK_PDF.exists():
        print(f'  · {DECK_PDF.name} absent : MP4 non produit '
              f'(lancez generer-presentation.py d\'abord).')
        return None
    if not shutil.which('ffmpeg'):
        print('  · ffmpeg absent : MP4 non produit.')
        return None

    import pymupdf

    page = pymupdf.open(DECK_PDF)[0]
    zoom = 1920 / page.rect.width
    px = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    couverture = Image.frombytes('RGB', (px.width, px.height), px.samples)
    couverture = couverture.resize((1920, 1080), Image.LANCZOS)

    # Le logo occupe (9,44 ; 4,60) 15,0 x 3,25 cm sur une diapo de 33,87 x 19,05.
    k = 1920 / 33.87
    boite = (int(9.44 * k), int(4.60 * 1080 / 19.05),
             int((9.44 + 15.0) * k), int((4.60 + 3.25) * 1080 / 19.05))
    logo = Image.open(LOGO).convert('RGBA').resize(
        (boite[2] - boite[0], boite[3] - boite[1]), Image.LANCZOS)
    alpha_plein = Image.new('L', (1920, 1080), 0)
    alpha_plein.paste(logo.split()[3], (boite[0], boite[1]))

    travail = SORTIE / '.animation-images'
    if travail.exists():
        shutil.rmtree(travail)
    travail.mkdir()
    for i, im in enumerate(images_du_mouvement(couverture, alpha_plein)):
        im.save(travail / f'f{i:03d}.png')

    chemin = SORTIE / 'couverture-testing-event.mp4'
    fps = IMAGES_MOUVEMENT / MOUVEMENT_S
    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error', '-framerate', f'{fps:.4f}',
        '-i', str(travail / 'f%03d.png'),
        '-vf', f'tpad=stop_mode=clone:stop_duration={PAUSE_S},fps=25,format=yuv420p',
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '20',
        '-movflags', '+faststart', str(chemin)], check=True, timeout=600)
    shutil.rmtree(travail)
    return chemin


def verifier_gif(chemin):
    """Une boucle infinie, la bonne durée, et une vraie pause à la fin."""
    anomalies = []
    with Image.open(chemin) as gif:
        if gif.info.get('loop', None) != 0:
            anomalies.append(f"la boucle n'est pas infinie (loop={gif.info.get('loop')}).")
        total, dernieres = 0, []
        for i in range(gif.n_frames):
            gif.seek(i)
            d = gif.info.get('duration', 0)
            total += d
            dernieres.append(d)
        attendu = (MOUVEMENT_S + PAUSE_S) * 1000
        if abs(total - attendu) > 400:
            anomalies.append(f'durée {total / 1000:.1f} s, {attendu / 1000:.0f} s attendues.')
        # Les images de pause sont fusionnées à l'écriture : ce qui compte est
        # que la dernière dure la pause entière, pas leur nombre.
        if dernieres[-1] < PAUSE_S * 1000 - 400:
            anomalies.append(f'pause finale de {dernieres[-1] / 1000:.1f} s, '
                             f'{PAUSE_S:.0f} s attendues.')
    return anomalies


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    gif, images, duree = faire_gif()
    print(f'{gif.relative_to(RACINE)}  {gif.stat().st_size / 1024:.0f} Ko  '
          f'{images} images  {duree:.1f} s')
    anomalies = verifier_gif(gif)
    for a in anomalies:
        print(f'  ✗ {a}')
    if not anomalies:
        print(f'  ✓ boucle infinie, {MOUVEMENT_S:.1f} s de mouvement puis '
              f'{PAUSE_S:.1f} s d\'arrêt.')

    mp4 = faire_mp4()
    if mp4:
        print(f'{mp4.relative_to(RACINE)}  {mp4.stat().st_size / 1024:.0f} Ko')
    sys.exit(1 if anomalies else 0)


if __name__ == '__main__':
    main()
