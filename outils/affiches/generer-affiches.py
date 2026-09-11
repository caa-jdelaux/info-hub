#!/usr/bin/env python3
"""Affiches A3 des kiosques, une par thème, à coller sur la porte des salles.

Hors chaîne de production : ce script n'est pas exécuté par le CI et demande
python-pptx, les polices Barlow / Barlow Condensed et LibreOffice pour le PDF.

Les dix thèmes ne sont pas ressaisis ici : ils sont lus dans la page programme,
qui reste la source unique. Une correction de pitch faite sur la page se
retrouve sur l'affiche à la prochaine exécution, et une affiche ne peut pas
diverger en silence de ce que les participants lisent sur leur téléphone.

Volontairement, l'affiche ne nomme aucune salle. Les affectations ont bougé
deux fois cette semaine ; une affiche muette sur ce point se déplace d'une
porte à l'autre au lieu de se réimprimer. Le kiosque 10 occupe deux salles :
c'est la même affiche, tirée en deux exemplaires.

Deux variantes, à comparer sur papier avant de lancer le tirage :
  affiches-kiosques-clair.pptx / .pdf    fond blanc, bandeaux sombres
  affiches-kiosques-sombre.pptx / .pdf   fond sombre, texte clair

Le PDF est ce qui part chez l'imprimeur : polices embarquées, rendu garanti.
Le .pptx sert à corriger sur place — il suppose Barlow Condensed installée,
sans quoi PowerPoint substitue et la mise en page bouge.
"""
import html
import pathlib
import re
import subprocess
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Cm, Pt

RACINE = pathlib.Path(__file__).resolve().parents[2]
PAGE = RACINE / 'worker' / 'public' / 'testing-event-2026' / 'index.html'
QR = RACINE / 'qr' / 'testing-event-2026.png'
SORTIE = pathlib.Path(__file__).parent
URL = 'info-hub.jeremy-delaux.workers.dev/testing-event-2026/'

# A3 portrait. PowerPoint ouvre en 33,87 x 19,05 cm : sans ce réglage, le
# pilote d'impression recadre ou marge la diapo, et c'est la première cause
# d'affiche ratée.
LARGEUR, HAUTEUR = Cm(29.7), Cm(42)
MARGE = Cm(2.0)
UTILE = Cm(25.7)

CONDENSEE = 'Barlow Condensed'
COURANTE = 'Barlow'

# Palette de la page programme, reprise à l'identique.
ENCRE = RGBColor(0x1A, 0x1A, 0x2E)
TEAL_FONCE = RGBColor(0x00, 0x80, 0x80)
TEAL_TEXTE = RGBColor(0x00, 0x6A, 0x6A)
CYAN = RGBColor(0x00, 0xB4, 0xB4)
BLANC = RGBColor(0xFF, 0xFF, 0xFF)
GRIS_FONCE = RGBColor(0x4A, 0x4A, 0x49)
BLEU_CLAIR = RGBColor(0xD9, 0xEF, 0xEF)
GRIS_CLAIR = RGBColor(0xE3, 0xE3, 0xE3)
NAVY_CLAIR = RGBColor(0x2E, 0x2E, 0x50)

THEMES = {
    'clair': {
        'fond': BLANC,
        'bandeau': ENCRE, 'bandeau_texte': BLANC, 'bandeau_second': CYAN,
        'pastille': TEAL_FONCE, 'pastille_texte': BLANC,
        'titre': ENCRE, 'pitch': GRIS_FONCE,
        'creneau': BLEU_CLAIR, 'creneau_heure': TEAL_TEXTE, 'creneau_label': GRIS_FONCE,
        'intertitre': TEAL_TEXTE,
        'pied': ENCRE, 'pied_texte': BLANC, 'pied_second': CYAN,
    },
    'sombre': {
        'fond': ENCRE,
        'bandeau': TEAL_FONCE, 'bandeau_texte': BLANC, 'bandeau_second': BLEU_CLAIR,
        'pastille': CYAN, 'pastille_texte': ENCRE,
        'titre': BLANC, 'pitch': GRIS_CLAIR,
        'creneau': NAVY_CLAIR, 'creneau_heure': CYAN, 'creneau_label': GRIS_CLAIR,
        'intertitre': CYAN,
        'pied': TEAL_FONCE, 'pied_texte': BLANC, 'pied_second': BLEU_CLAIR,
    },
}


def sans_balises(fragment):
    return html.unescape(re.sub(r'<[^>]+>', '', fragment)).strip()


def lire_programme():
    """Les dix kiosques et les cinq rotations, tels qu'ils sont publiés."""
    page = PAGE.read_text(encoding='utf-8')

    kiosques = []
    for carte in re.finditer(
            r'<article class="kiosque-card" data-kiosque="(\d+)">(.*?)</article>',
            page, re.S):
        numero, corps = carte.group(1), carte.group(2)
        nom = re.search(r'<h3 class="kiosque-name">(.*?)</h3>', corps, re.S).group(1)
        emoji = re.search(r'<span aria-hidden="true">(.*?)</span>', nom).group(1)
        pitch = re.search(r'<div class="kiosque-pitch">(.*?)</div>', corps, re.S).group(1)
        # Les porteurs, un couple (entité, noms) par groupe, dans l'ordre de la
        # page. L'affiche A3 ne les utilise pas encore ; la variante Word, si.
        groupes = [(sans_balises(o), sans_balises(n)) for o, n in re.findall(
            r'<span class="qui-groupe"><span class="qui-org">(.*?)</span>(.*?)</span>',
            corps, re.S)]
        kiosques.append({
            'numero': numero,
            'emoji': emoji,
            'titre': sans_balises(re.sub(r'<span aria-hidden="true">.*?</span>', '', nom)),
            'pitch': sans_balises(pitch),
            'qui': groupes,
        })

    rotations = []
    for creneau in re.finditer(r'<div class="rotation-slot"[^>]*>(.*?)</div>',
                               page, re.S):
        heure = re.search(r'class="rs-time">(.*?)</span>', creneau.group(1), re.S)
        label = re.search(r'class="rs-label">(.*?)</span>', creneau.group(1), re.S)
        if heure and label:
            rotations.append((sans_balises(heure.group(1)), sans_balises(label.group(1))))

    if len(kiosques) != 10 or len(rotations) != 5:
        sys.exit(f'programme illisible : {len(kiosques)} kiosques, '
                 f'{len(rotations)} rotations (attendu 10 et 5)')
    muets = [k['numero'] for k in kiosques if not k['qui']]
    if muets:
        sys.exit('porteurs illisibles dans la page pour les kiosques '
                 + ', '.join(muets))
    return kiosques, rotations


def bloc(diapo, x, y, l, h, couleur):
    forme = diapo.shapes.add_shape(1, x, y, l, h)   # 1 = rectangle
    forme.fill.solid()
    forme.fill.fore_color.rgb = couleur
    forme.line.fill.background()
    forme.shadow.inherit = False
    # LibreOffice applique l'ombre portée du thème (<a:effectRef>) malgré le
    # <a:effectLst/> vide que pose python-pptx. On retire le style de thème :
    # le remplissage et le contour sont fixés explicitement juste au-dessus.
    style = forme._element.find(qn('p:style'))
    if style is not None:
        forme._element.remove(style)
    return forme


def texte(diapo, x, y, l, h, lignes, align=PP_ALIGN.LEFT, ancre=MSO_ANCHOR.TOP):
    """lignes : liste de (contenu, police, taille, couleur, gras, interligne)."""
    zone = diapo.shapes.add_textbox(x, y, l, h)
    cadre = zone.text_frame
    cadre.word_wrap = True
    cadre.vertical_anchor = ancre
    for marge in ('margin_left', 'margin_right', 'margin_top', 'margin_bottom'):
        setattr(cadre, marge, 0)
    for i, (contenu, police, taille, couleur, gras, interligne) in enumerate(lignes):
        p = cadre.paragraphs[0] if i == 0 else cadre.add_paragraph()
        p.alignment = align
        p.line_spacing = interligne
        r = p.add_run()
        r.text = contenu
        r.font.name = police
        r.font.size = Pt(taille)
        r.font.bold = gras
        r.font.color.rgb = couleur
    return zone


def composer(diapo, kiosque, rotations, t):
    bloc(diapo, 0, 0, LARGEUR, HAUTEUR, t['fond'])

    # ── Bandeau de tête ────────────────────────────────────────────────
    bloc(diapo, 0, 0, LARGEUR, Cm(5.5), t['bandeau'])
    texte(diapo, MARGE, Cm(1.15), Cm(16), Cm(3.4), [
        ('TESTING EVENT', CONDENSEE, 40, t['bandeau_texte'], True, 0.95),
        ('Lundi 14 septembre 2026 · Business Center CAA', COURANTE, 17,
         t['bandeau_second'], False, 1.15),
    ])
    texte(diapo, Cm(18.0), Cm(1.6), Cm(9.7), Cm(2.4),
          [('APRÈS-MIDI · KIOSQUES', CONDENSEE, 24, t['bandeau_second'], True, 1.0)],
          align=PP_ALIGN.RIGHT)

    # ── Numéro et titre ────────────────────────────────────────────────
    # Le numéro est le seul repère lisible de loin : c'est lui qui dit au
    # participant qu'il est devant la bonne porte, pas le titre.
    bloc(diapo, MARGE, Cm(7.2), Cm(8.2), Cm(8.2), t['pastille'])
    texte(diapo, MARGE, Cm(7.2), Cm(8.2), Cm(8.2),
          [(kiosque['numero'], CONDENSEE, 190, t['pastille_texte'], True, 0.9)],
          align=PP_ALIGN.CENTER, ancre=MSO_ANCHOR.MIDDLE)

    texte(diapo, Cm(11.2), Cm(7.2), Cm(5), Cm(3.8),
          [(kiosque['emoji'], COURANTE, 88, t['titre'], False, 1.0)])
    # Zone ancrée en haut : un titre sur deux lignes remontait sinon dans
    # l'emoji. Relevé sur le kiosque 10, dont le titre faisait alors vingt-sept
    # signes ; il est plus court aujourd'hui, la zone reste dimensionnée pour
    # le cas long.
    texte(diapo, Cm(11.2), Cm(11.6), Cm(16.5), Cm(4.6),
          [(kiosque['titre'], CONDENSEE, 66, t['titre'], True, 0.92)])

    # ── Pitch ──────────────────────────────────────────────────────────
    texte(diapo, MARGE, Cm(17.6), UTILE, Cm(6.4),
          [(kiosque['pitch'], COURANTE, 34, t['pitch'], False, 1.35)])

    # ── Rotations ──────────────────────────────────────────────────────
    # La question de quelqu'un qui arrive à 15h10 n'est pas « c'est quoi »
    # mais « ça finit quand » : les cinq créneaux valent le tiers de la page.
    debut, fin = rotations[0][0].split(' – ')[0], rotations[-1][0].split(' – ')[-1]
    texte(diapo, MARGE, Cm(25.2), UTILE, Cm(1.2),
          [(f'5 ROTATIONS DE 30 MINUTES · {debut} → {fin}', CONDENSEE, 24,
            t['intertitre'], True, 1.0)])

    largeur = (UTILE - Cm(1.6)) / 5
    for i, (heure, label) in enumerate(rotations):
        x = MARGE + int(i * (largeur + Cm(0.4)))
        depart, arrivee = heure.split(' – ')
        bloc(diapo, x, Cm(26.8), int(largeur), Cm(4.6), t['creneau'])
        # L'heure de début en gros, la fin en dessous : la question de
        # quelqu'un qui hésite dans le couloir est « ça commence quand ».
        texte(diapo, x, Cm(27.5), int(largeur), Cm(3.4), [
            (depart, CONDENSEE, 32, t['creneau_heure'], True, 1.0),
            ('→ ' + arrivee, CONDENSEE, 20, t['creneau_heure'], False, 1.15),
            (label, COURANTE, 14, t['creneau_label'], False, 1.5),
        ], align=PP_ALIGN.CENTER)

    # ── Pied : QR vers le programme ────────────────────────────────────
    bloc(diapo, 0, Cm(33.2), LARGEUR, Cm(8.8), t['pied'])
    # Plaque blanche sous le QR : la zone de silence fait partie du code, et
    # un QR noir sur fond sombre ne se lit pas.
    bloc(diapo, Cm(20.5), Cm(34.4), Cm(7.2), Cm(7.2), BLANC)
    diapo.shapes.add_picture(str(QR), Cm(20.9), Cm(34.8), Cm(6.4), Cm(6.4))
    texte(diapo, MARGE, Cm(35.4), Cm(17.5), Cm(5.4), [
        ('LE PROGRAMME COMPLET', CONDENSEE, 30, t['pied_second'], True, 1.0),
        ('Les dix kiosques, les conférences du matin et le plan '
         'du rez-de-jardin, salle par salle.', COURANTE, 17,
         t['pied_texte'], False, 1.3),
        (URL, COURANTE, 14, t['pied_second'], False, 1.6),
    ])


def construire(variante):
    kiosques, rotations = lire_programme()
    t = THEMES[variante]

    prez = Presentation()
    prez.slide_width, prez.slide_height = LARGEUR, HAUTEUR
    vierge = prez.slide_layouts[6]

    for kiosque in kiosques:
        composer(prez.slides.add_slide(vierge), kiosque, rotations, t)

    chemin = SORTIE / f'affiches-kiosques-{variante}.pptx'
    prez.save(chemin)
    return chemin


def en_pdf(pptx):
    subprocess.run(
        ['soffice', '--headless',
         # Profil jetable : deux conversions de suite se marchent dessus si
         # elles partagent le profil par défaut.
         '-env:UserInstallation=file:///tmp/lo-affiches',
         '--convert-to', 'pdf', '--outdir', str(pptx.parent), str(pptx)],
        check=True, capture_output=True, timeout=300)
    return pptx.with_suffix('.pdf')


def verifier(pdf):
    """Relit le PDF produit et refuse un chevauchement.

    Un pitch rallongé sur la page programme pousse le texte hors de sa zone
    sans que rien ne le signale : sur un A3 tiré en onze exemplaires, l'erreur
    se découvre au mur. On mesure donc les blocs de texte du PDF plutôt que de
    faire confiance à la mise en page.
    """
    import pymupdf

    cm = 72 / 2.54
    anomalies = []
    doc = pymupdf.open(pdf)
    if doc.page_count != 10:
        anomalies.append(f'{doc.page_count} pages, 10 attendues.')
    for n, page in enumerate(doc, 1):
        if (abs(page.rect.width / cm - 29.7) > 0.05
                or abs(page.rect.height / cm - 42) > 0.05):
            anomalies.append(f'p{n} : {page.rect.width / cm:.1f} x '
                             f'{page.rect.height / cm:.1f} cm, A3 portrait attendu.')
        blocs = [(b[0] / cm, b[1] / cm, b[2] / cm, b[3] / cm)
                 for b in page.get_text('blocks') if b[4].strip()]
        # Seuil calé sur la zone non imprimable d'un copieur de bureau
        # (~10 mm), pas sur la marge de maquette (20 mm) : le bloc de texte
        # rendu déborde son cadre de 1 à 2 mm — espace de fin, chasse du
        # dernier glyphe — sans que rien ne soit visible. Ce contrôle protège
        # du rognage réel, pas d'une dérive de 2 mm.
        for x0, y0, x1, y1 in blocs:
            if x0 < 1.0 or x1 > 28.7:
                anomalies.append(f'p{n} : un texte risque le rognage '
                                 f'({x0:.1f} → {x1:.1f} cm).')
        # Le numéro, l'emoji et le titre forment un seul bloc pour le lecteur
        # de PDF : c'est son bas qui ne doit pas mordre sur le pitch.
        identite = max((y1 for _, y0, _, y1 in blocs if 5.5 < y0 < 17.0), default=0)
        if identite > 17.6:
            anomalies.append(f'p{n} : le titre déborde sur le pitch ({identite:.1f} cm).')
        pitch = max((y1 for _, y0, _, y1 in blocs if 17.0 < y0 < 25.0), default=0)
        if pitch > 25.2:
            anomalies.append(f'p{n} : le pitch déborde sur les rotations ({pitch:.1f} cm).')
        contenu = max((y1 for _, y0, _, y1 in blocs if y0 < 32.0), default=0)
        if contenu > 33.2:
            anomalies.append(f'p{n} : du texte passe sous le bandeau de pied '
                             f'({contenu:.1f} cm).')
    return anomalies


def main():
    souci = 0
    for variante in THEMES:
        pptx = construire(variante)
        pdf = en_pdf(pptx)
        for f in (pptx, pdf):
            print(f'{f.relative_to(RACINE)}  {f.stat().st_size / 1024:.0f} Ko')
        anomalies = verifier(pdf)
        for a in anomalies:
            print(f'  ✗ {a}')
        souci += len(anomalies)
        if not anomalies:
            print('  ✓ 10 pages A3, aucun chevauchement.')
    sys.exit(1 if souci else 0)


if __name__ == '__main__':
    main()
