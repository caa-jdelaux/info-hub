#!/usr/bin/env python3
"""La page de garde animée par une vidéo, en une diapo.

Hors chaîne de production : ce script n'est pas exécuté par le CI et demande
python-pptx, python-pptx, ffmpeg et les polices Barlow.

Il part de `ressources/couverture-source.mov` — dix secondes d'animation du
logo — et en fait une diapo unique où la vidéo prend la place du logo, joue,
puis reste vingt secondes sur sa dernière image avant de recommencer.

Trois choses sont refaites sur la source, et chacune évite une panne :

  Le conteneur. La source est du HEVC dans un .mov. PowerPoint lit le H.264
  dans un .mp4 sans extension de codec ; l'inverse n'est pas garanti sur un
  poste d'entreprise. Le fichier est donc réencodé.

  Le son. La source porte une piste audio. Une page de garde qui boucle avec
  du son toutes les trente secondes est intenable ; la piste est retirée.

  Les niveaux. La source est en yuvj420p (échelle pleine). Convertie sans
  précaution, elle s'affiche avec des noirs bouchés ou délavés selon le
  lecteur ; la conversion d'échelle est explicite.

Et une quatrième, qui ne se voit qu'une fois la vidéo posée sur la diapo : ses
bords sont fondus vers l'encre de la charte. Le fond de la source est un marine
proche du nôtre au centre, mais son canal bleu s'effondre sur les bords
gauche et droit — de 43 à 24, quand la charte est à 46. Posée telle quelle, la
vidéo dessinait un rectangle plus sombre au milieu de la page de garde. Après
fondu, le pourtour mesure (25, 23, 45) contre (26, 26, 46) attendus : l'écart
n'est plus visible.

La pause de vingt secondes est obtenue en figeant la dernière image, pas en
allongeant la vidéo : vingt secondes d'images identiques ne coûtent presque
rien au codeur.

CE QUI N'A PAS PU ÊTRE VÉRIFIÉ. Le déclenchement automatique et la répétition
sont écrits dans le XML de la diapo, mais cet environnement n'a pas PowerPoint
— seulement LibreOffice, qui ne rend pas ces attributs. Si la vidéo ne partait
pas seule, le réglage est dans PowerPoint : onglet Lecture, « Démarrer :
Automatiquement » et « En boucle jusqu'à l'arrêt ». La composition, elle, est
vérifiée ; l'image d'affiche est la dernière image de la vidéo, donc la diapo
reste juste même si rien ne se lance.
"""
import importlib.util
import pathlib
import shutil
import subprocess
import sys

from pptx import Presentation
from pptx.oxml.ns import qn
from pptx.util import Cm

RACINE = pathlib.Path(__file__).resolve().parents[2]
DOSSIER = pathlib.Path(__file__).parent
RES = DOSSIER / 'ressources'
SOURCE = RES / 'couverture-source.mov'
VIDEO = DOSSIER / 'couverture-animee-30s.mp4'
AFFICHE = RES / 'couverture-affiche.png'
PPTX = DOSSIER / 'couverture-testing-event.pptx'

PAUSE_S = 19.9          # 10,1 s de vidéo + 19,9 s d'arrêt = 30,0 s pile
# L'encre de la charte est #1A1A2E = (26, 26, 46). Remplie telle quelle, elle
# ressort à (23, 24, 45) après l'aller-retour en échelle télé du H.264 — trois
# niveaux d'écart, soit un rectangle encore perceptible de près. La valeur de
# remplissage est donc pré-compensée pour retomber sur l'encre après codage.
ENCRE = '0x1D1C2F'
FONDU_X, FONDU_Y = 70, 26   # largeur du fondu, en pixels de la source
# La vidéo fait 990 x 246 : la largeur est celle du logo qu'elle remplace, la
# hauteur s'en déduit pour ne pas la déformer.
LARGEUR_CM = 15.0


def presentation():
    """Le générateur de la présentation, chargé comme module.

    Son nom porte un tiret : il n'est pas importable tel quel. On passe par
    importlib plutôt que de recopier la composition de la couverture, qui
    finirait par diverger.
    """
    chemin = DOSSIER / 'generer-presentation.py'
    spec = importlib.util.spec_from_file_location('generer_presentation', chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sonder(chemin, champs):
    sortie = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', champs,
         '-of', 'default=nw=1', str(chemin)],
        check=True, capture_output=True, text=True).stdout
    return dict(l.split('=', 1) for l in sortie.strip().splitlines() if '=' in l)


def preparer_video():
    infos = sonder(SOURCE, 'stream=width,height')
    l, h = int(infos['width']), int(infos['height'])

    # La vidéo est fondue sur un aplat à l'encre de la charte : ses bords
    # disparaissent au lieu de dessiner un rectangle sur la page de garde.
    fondu = (f'[0:v]tpad=stop_mode=clone:stop_duration={PAUSE_S},'
             'scale=in_range=full:out_range=tv,format=rgba,'
             "geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
             f"a='255*min(1\,min(min(X\,W-1-X)/{FONDU_X}\,"
             f"min(Y\,H-1-Y)/{FONDU_Y}))'[fg];"
             f'color=c={ENCRE}:s={l}x{h}:r=30:d=30,format=rgba[bg];'
             '[bg][fg]overlay=shortest=1,format=yuv420p[v]')
    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error', '-i', str(SOURCE), '-an',
        '-filter_complex', fondu, '-map', '[v]',
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '21', '-r', '30',
        '-movflags', '+faststart', str(VIDEO)], check=True, timeout=900)

    # L'affiche est tirée de la vidéo produite, pas de la source : c'est elle
    # qui s'affiche si rien ne se lance, elle doit donc porter le même fondu.
    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error', '-sseof', '-0.2', '-i', str(VIDEO),
        '-update', '1', '-frames:v', '1', str(AFFICHE)], check=True, timeout=300)
    return l, h


def lecture_automatique_en_boucle(diapo, forme):
    """Règle la vidéo sur « démarrer seule » et « recommencer sans fin ».

    python-pptx écrit un déclenchement au clic. On ne réécrit pas l'arbre de
    temporisation — une erreur y ferait déclarer le fichier corrompu par
    PowerPoint — on modifie deux attributs du nœud qu'il a produit : la
    condition de départ passe de « indéfinie » (au clic) à zéro, et le nœud
    reçoit une répétition infinie.
    """
    timing = diapo._element.find(qn('p:timing'))
    if timing is None:
        return ['aucun arbre de temporisation : la vidéo ne peut pas être réglée.']
    noeuds = timing.iter(qn('p:cMediaNode'))
    anomalies = []
    for media in noeuds:
        ctn = media.find(qn('p:cTn'))
        if ctn is None:
            anomalies.append('nœud média sans p:cTn.')
            continue
        ctn.set('repeatCount', 'indefinite')
        for cond in ctn.iter(qn('p:cond')):
            if cond.get('delay') == 'indefinite':
                cond.set('delay', '0')
        return anomalies
    return anomalies + ['aucun nœud média trouvé.']


def construire(l, h):
    module = presentation()
    prog = module.lire_programme()

    prez = Presentation()
    prez.slide_width, prez.slide_height = module.LARGEUR, module.HAUTEUR
    diapo = prez.slides.add_slide(prez.slide_layouts[6])
    module.d01_couverture(diapo, prog, marque=False)

    hauteur = LARGEUR_CM * h / l
    # Centrée sur le centre du logo qu'elle remplace, pour que les deux
    # versions de la couverture se superposent exactement.
    centre_y = 4.6 + (15.0 * 104 / 480) / 2
    forme = diapo.shapes.add_movie(
        str(VIDEO), Cm(9.44), Cm(centre_y - hauteur / 2),
        Cm(LARGEUR_CM), Cm(hauteur),
        poster_frame_image=str(AFFICHE), mime_type='video/mp4')

    anomalies = lecture_automatique_en_boucle(diapo, forme)
    prez.save(PPTX)
    return anomalies


def verifier():
    anomalies = []
    infos = sonder(VIDEO, 'format=duration:stream=codec_name,codec_type,pix_fmt')
    if abs(float(infos.get('duration', 0)) - 30.0) > 0.15:
        anomalies.append(f"la vidéo dure {infos.get('duration')} s, 30 attendues.")
    if infos.get('codec_name') != 'h264':
        anomalies.append(f"codec {infos.get('codec_name')}, h264 attendu.")
    if infos.get('pix_fmt') != 'yuv420p':
        anomalies.append(f"format de pixels {infos.get('pix_fmt')}, yuv420p attendu.")
    pistes = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'a',
         '-show_entries', 'stream=index', '-of', 'csv=p=0', str(VIDEO)],
        check=True, capture_output=True, text=True).stdout.strip()
    if pistes:
        anomalies.append('la vidéo porte encore une piste audio.')

    from PIL import Image
    import numpy as np

    bord = np.asarray(Image.open(AFFICHE).convert('RGB')).astype(int)
    pourtour = np.concatenate([bord[0:4].reshape(-1, 3), bord[-4:].reshape(-1, 3),
                               bord[:, 0:4].reshape(-1, 3), bord[:, -4:].reshape(-1, 3)])
    ecart = np.abs(pourtour - np.array([26, 26, 46])).max()
    if ecart > 3:
        anomalies.append(f"le pourtour de la vidéo s'écarte de l'encre de {ecart} "
                         f'niveaux : le rectangle se verra sur la diapo.')

    import zipfile
    with zipfile.ZipFile(PPTX) as z:
        noms = z.namelist()
        if not any(n.endswith('.mp4') for n in noms):
            anomalies.append("aucune vidéo mp4 embarquée dans le pptx.")
        diapo = z.read('ppt/slides/slide1.xml').decode('utf-8')
        if 'repeatCount="indefinite"' not in diapo:
            anomalies.append("la répétition infinie n'est pas inscrite.")
        if '<p:cond delay="indefinite"/>' in diapo:
            anomalies.append("le départ est resté au clic.")
        if 'video/mp4' not in z.read('[Content_Types].xml').decode('utf-8'):
            anomalies.append("le type video/mp4 n'est pas déclaré.")
    return anomalies


def main():
    if not shutil.which('ffmpeg'):
        sys.exit('ffmpeg est nécessaire.')
    if not SOURCE.exists():
        sys.exit(f'{SOURCE.relative_to(RACINE)} introuvable.')

    l, h = preparer_video()
    anomalies = construire(l, h) + verifier()
    for f in (VIDEO, PPTX):
        print(f'{f.relative_to(RACINE)}  {f.stat().st_size / 1024:.0f} Ko')
    for a in anomalies:
        print(f'  ✗ {a}')
    if not anomalies:
        print('  ✓ 30,0 s, h264 sans audio, vidéo embarquée, '
              'départ automatique et boucle inscrits.')
    sys.exit(1 if anomalies else 0)


if __name__ == '__main__':
    main()
