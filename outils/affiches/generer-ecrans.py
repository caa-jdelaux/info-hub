#!/usr/bin/env python3
"""Le programme de la journée sur les écrans du Business Center, en deux chartes.

Hors chaîne de production : ce script n'est pas exécuté par le CI et demande
python-pptx, pymupdf, LibreOffice Impress et les polices Poppins et Barlow.

Le modèle fourni (« Templates A écrans BC VF.pptx ») est un 16:9 de 1280 x 720,
dont la quatrième diapo est un agenda. On en reprend les mesures exactes,
relevées dans le fichier :

    diapo             33,87 x 19,05 cm (1280 x 720 px)
    photo             pleine page
    panneau           (2,0 ; 2,0) 29,8 x 15,0 cm, vert #006B4F à 85 %
    police            Poppins (ExtraBold pour le titre, Medium pour le corps)
    bandeau de pied   Prestige Affaires, « Façonner demain ! », CA Assurances

L'agenda du modèle tient cinq lignes ; la journée en compte neuf, et le sujet
de l'après-midi est un bloc de dix kiosques. D'où deux colonnes plutôt qu'une
liste : la journée à gauche, les dix kiosques à droite. Le détail de chaque
kiosque — le pitch, la salle, le plan — reste derrière le QR : un écran de hall
se lit en marchant, pas en s'arrêtant.

Comme pour les affiches, les contenus sont lus dans la page programme et non
ressaisis : l'écran ne peut pas dériver de ce que les participants ont dans la
main.

Deux sorties :
    ecran-programme-caa.pptx / .pdf        charte du modèle
    ecran-programme-testing.pptx / .pdf    charte du programme
"""
import html
import pathlib
import re
import subprocess
import sys

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Cm, Pt

RACINE = pathlib.Path(__file__).resolve().parents[2]
PAGE = RACINE / 'worker' / 'public' / 'testing-event-2026' / 'index.html'
QR = RACINE / 'qr' / 'testing-event-2026.png'
MONOGRAMME = RACINE / 'qr' / 'monogramme-te.png'
RES = pathlib.Path(__file__).parent / 'ressources'
SORTIE = pathlib.Path(__file__).parent
URL = 'info-hub.jeremy-delaux.workers.dev/testing-event-2026/'

LARGEUR, HAUTEUR = Cm(33.87), Cm(19.05)
PANNEAU = (Cm(2.0), Cm(2.0), Cm(29.8), Cm(15.0))

VERT_BC = RGBColor(0x00, 0x6B, 0x4F)
ENCRE = RGBColor(0x1A, 0x1A, 0x2E)
CYAN = RGBColor(0x00, 0xB4, 0xB4)
BLEU_CLAIR = RGBColor(0xD9, 0xEF, 0xEF)
VERT_CLAIR = RGBColor(0xB2, 0xD2, 0xCA)
BLANC = RGBColor(0xFF, 0xFF, 0xFF)

CHARTES = {
    'caa': {
        'panneau': VERT_BC, 'opacite': 85,
        'titre_police': 'Poppins ExtraBold', 'titre_gras': False,
        'corps': 'Poppins', 'corps_fort': 'Poppins SemiBold',
        'accent': VERT_CLAIR, 'intertitre': BLANC,
        'fort_gras': False, 'titre_y': 3.3, 'monogramme': False,
    },
    'testing': {
        'panneau': ENCRE, 'opacite': 88,
        'titre_police': 'Barlow Condensed', 'titre_gras': True,
        'corps': 'Barlow', 'corps_fort': 'Barlow Condensed',
        'accent': BLEU_CLAIR, 'intertitre': CYAN,
        'fort_gras': True, 'titre_y': 3.7, 'monogramme': True,
    },
}


def sans_balises(fragment):
    return html.unescape(re.sub(r'<[^>]+>', ' ', fragment)).split()


def lire_programme():
    """La journée et les dix kiosques, tels qu'ils sont publiés."""
    page = PAGE.read_text(encoding='utf-8')

    journee = []
    # On vise le libellé du créneau, pas tout ce qui suit : borner sur le
    # bloc voisin ramassait le bandeau « 10 kiosques en simultané… » dans la
    # ligne de 13h40, et le filtrage des chiffres en faisait une bouillie.
    for m in re.finditer(
            r'<div class="special-slot"[^>]*data-debut="(\d+)".*?'
            r'<div class="slot-label[^"]*">(.*?)</div>', page, re.S):
        # L'emoji est décoratif dans la page ; sur un écran de hall il
        # parasite la charte et dépend d'une police installée.
        libelle = re.sub(r'<span aria-hidden="true">.*?</span>', '', m.group(2), flags=re.S)
        journee.append((int(m.group(1)), ' '.join(sans_balises(libelle))))
    for m in re.finditer(r'<article class="conf-card"[^>]*data-debut="(\d+)"[^>]*>(.*?)</article>',
                         page, re.S):
        genre = re.search(r'class="conf-type">(.*?)<', m.group(2), re.S)
        titre = re.search(r'class="conf-title">(.*?)<', m.group(2), re.S)
        # « Conférence 1 » → « Conférence » : le numéro est déjà donné par
        # l'ordre des lignes. Et le titre est coupé à son deux-points : ce qui
        # suit est un sous-titre de vingt mots, illisible depuis un hall.
        etiquette = re.sub(r'\s*\d+$', '', ' '.join(sans_balises(genre.group(1)))) if genre else ''
        intitule = ' '.join(sans_balises(titre.group(1))).split(' : ')[0]
        journee.append((int(m.group(1)),
                        (etiquette + ' — ' if etiquette else '') + intitule))

    rotations = re.findall(r'<div class="rotation-slot"[^>]*data-debut="(\d+)"', page)
    if rotations:
        journee.append((int(rotations[0]),
                        '10 kiosques en simultané · 5 rotations de 30 min'))
    journee.sort()

    kiosques = []
    for carte in re.finditer(
            r'<article class="kiosque-card" data-kiosque="(\d+)">(.*?)</article>', page, re.S):
        nom = re.search(r'<h3 class="kiosque-name">(.*?)</h3>', carte.group(2), re.S).group(1)
        titre = re.sub(r'<span aria-hidden="true">.*?</span>', '', nom)
        kiosques.append((carte.group(1), ' '.join(sans_balises(titre))))

    if len(journee) != 9 or len(kiosques) != 10:
        sys.exit(f'programme illisible : {len(journee)} moments, '
                 f'{len(kiosques)} kiosques (attendu 9 et 10)')
    return journee, kiosques


def bloc(diapo, forme_type, x, y, l, h, couleur, opacite=100):
    forme = diapo.shapes.add_shape(forme_type, x, y, l, h)
    forme.fill.solid()
    forme.fill.fore_color.rgb = couleur
    if opacite < 100:
        srgb = forme.fill.fore_color._xFill.find(qn('a:srgbClr'))
        alpha = etree.SubElement(srgb, qn('a:alpha'))
        alpha.set('val', str(int(opacite * 1000)))
    forme.line.fill.background()
    forme.shadow.inherit = False
    # LibreOffice applique l'ombre portée du thème malgré le <a:effectLst/>
    # vide posé par python-pptx : on retire le style de thème.
    style = forme._element.find(qn('p:style'))
    if style is not None:
        forme._element.remove(style)
    return forme


def texte(diapo, x, y, l, h, paragraphes, align=PP_ALIGN.LEFT, ancre=MSO_ANCHOR.TOP):
    """paragraphes : (runs, interligne) ; runs = (texte, police, pt, couleur, gras)."""
    zone = diapo.shapes.add_textbox(x, y, l, h)
    cadre = zone.text_frame
    cadre.word_wrap = True
    cadre.vertical_anchor = ancre
    for marge in ('margin_left', 'margin_right', 'margin_top', 'margin_bottom'):
        setattr(cadre, marge, 0)
    for i, (runs, interligne) in enumerate(paragraphes):
        p = cadre.paragraphs[0] if i == 0 else cadre.add_paragraph()
        p.alignment = align
        p.line_spacing = interligne
        for contenu, police, taille, couleur, gras in runs:
            r = p.add_run()
            r.text = contenu
            r.font.name = police
            r.font.size = Pt(taille)
            r.font.bold = gras
            r.font.color.rgb = couleur
    return zone


def pied(diapo):
    """Le bandeau de pied du modèle, repris à ses coordonnées d'origine."""
    diapo.shapes.add_picture(str(RES / 'logo-prestige-affaires.png'),
                             Cm(17.9), Cm(13.9), Cm(2.6), Cm(2.5))
    bloc(diapo, MSO_SHAPE.RECTANGLE, Cm(21.4), Cm(14.2), Cm(0.05), Cm(1.9), BLANC)
    diapo.shapes.add_picture(str(RES / 'logo-faconner-demain.png'),
                             Cm(22.2), Cm(14.1), Cm(4.0), Cm(2.0))
    bloc(diapo, MSO_SHAPE.RECTANGLE, Cm(27.0), Cm(14.1), Cm(0.05), Cm(1.9), BLANC)
    diapo.shapes.add_picture(str(RES / 'logo-ca-assurances.png'),
                             Cm(27.8), Cm(14.1), Cm(2.9), Cm(1.9))


def composer(diapo, c, journee, kiosques):
    diapo.shapes.add_picture(str(RES / 'ecran-business-center.jpg'),
                             0, 0, LARGEUR, HAUTEUR)
    bloc(diapo, MSO_SHAPE.RECTANGLE, *PANNEAU, c['panneau'], c['opacite'])

    # ── En-tête ────────────────────────────────────────────────────────
    if c['monogramme']:
        # 156 x 104 px : hauteur déduite pour ne pas déformer le monogramme.
        diapo.shapes.add_picture(str(MONOGRAMME), Cm(3.5), Cm(2.3), Cm(1.5), Cm(1.0))
    texte(diapo, Cm(3.5), Cm(c['titre_y']), Cm(20), Cm(2.8), [
        ([('TESTING EVENT', c['titre_police'], 34, BLANC, c['titre_gras'])], 0.95),
        ([('Lundi 14 septembre 2026 · Business Center CAA',
           c['corps'], 14, c['accent'], False)], 1.5),
    ])

    # ── QR, à la place du pictogramme du modèle ────────────────────────
    bloc(diapo, MSO_SHAPE.RECTANGLE, Cm(27.9), Cm(2.7), Cm(3.7), Cm(3.7), BLANC)
    diapo.shapes.add_picture(str(QR), Cm(28.15), Cm(2.95), Cm(3.2), Cm(3.2))
    texte(diapo, Cm(26.4), Cm(6.6), Cm(5.0), Cm(0.6),
          [([('Le détail et le plan', c['corps'], 9, c['accent'], False)], 1.0)],
          align=PP_ALIGN.CENTER)

    bloc(diapo, MSO_SHAPE.RECTANGLE, Cm(3.5), Cm(7.0), Cm(22.9), Cm(0.05), BLANC)

    # ── Colonne gauche : la journée ────────────────────────────────────
    texte(diapo, Cm(3.5), Cm(7.5), Cm(14.2), Cm(0.8),
          [([('LA JOURNÉE', c['corps_fort'], 13, c['intertitre'], c['fort_gras'])], 1.0)])
    lignes = []
    for debut, libelle in journee:
        lignes.append(([
            (f'{debut // 60}h{debut % 60:02d}   ', c['corps_fort'], 10, BLANC, c['fort_gras']),
            (libelle, c['corps'], 10, BLANC, False),
        ], 1.5))
    texte(diapo, Cm(3.5), Cm(8.4), Cm(14.2), Cm(5.0), lignes)

    # ── Colonne droite : les dix kiosques ──────────────────────────────
    texte(diapo, Cm(18.6), Cm(7.5), Cm(12.8), Cm(0.8),
          [([('LES 10 KIOSQUES', c['corps_fort'], 13, c['intertitre'], c['fort_gras'])], 1.0)])
    # Deux colonnes de cinq plutôt qu'une de dix : une pile de dix lignes
    # descendait dans le bandeau de logos, et cinq lignes se balaient d'un
    # regard là où dix demandent de suivre du doigt.
    for moitie in (0, 1):
        lignes = []
        for numero, titre in kiosques[moitie * 5:moitie * 5 + 5]:
            lignes.append(([
                (f'{numero}   ', c['corps_fort'], 10, c['accent'], c['fort_gras']),
                (titre, c['corps'], 10, BLANC, False),
            ], 1.5))
        texte(diapo, Cm(18.6 + moitie * 6.6), Cm(8.4), Cm(6.2), Cm(3.6), lignes)

    texte(diapo, Cm(3.5), Cm(15.3), Cm(13.0), Cm(0.6),
          [([(URL, c['corps'], 9, c['accent'], False)], 1.0)])
    pied(diapo)


def construire(journee, kiosques):
    chemins = []
    for nom, c in CHARTES.items():
        prez = Presentation()
        prez.slide_width, prez.slide_height = LARGEUR, HAUTEUR
        composer(prez.slides.add_slide(prez.slide_layouts[6]), c, journee, kiosques)
        chemin = SORTIE / f'ecran-programme-{nom}.pptx'
        prez.save(chemin)
        chemins.append(chemin)
    return chemins


def en_pdf(pptx):
    subprocess.run(
        ['soffice', '--headless', '-env:UserInstallation=file:///tmp/lo-affiches',
         '--convert-to', 'pdf', '--outdir', str(pptx.parent), str(pptx)],
        check=True, capture_output=True, timeout=300)
    return pptx.with_suffix('.pdf')


def verifier(pdf):
    """Format 16:9 exact, et rien qui déborde du panneau vert."""
    import pymupdf

    cm = 72 / 2.54
    anomalies = []
    doc = pymupdf.open(pdf)
    if doc.page_count != 1:
        anomalies.append(f'{doc.page_count} pages, 1 attendue.')
    for n, page in enumerate(doc, 1):
        if (abs(page.rect.width / cm - 33.87) > 0.05
                or abs(page.rect.height / cm - 19.05) > 0.05):
            anomalies.append(f'p{n} : {page.rect.width / cm:.2f} x '
                             f'{page.rect.height / cm:.2f} cm, 16:9 attendu.')
        for b in page.get_text('blocks'):
            if not b[4].strip():
                continue
            # Le panneau va de (2,0 ; 2,0) à (31,8 ; 17,0) : hors de lui, le
            # texte tombe sur la photo et devient illisible.
            if b[0] / cm < 2.2 or b[2] / cm > 31.6 or b[3] / cm > 16.8:
                anomalies.append(
                    f'p{n} : un texte sort du panneau '
                    f'({b[0] / cm:.1f}→{b[2] / cm:.1f} ; bas {b[3] / cm:.1f}) '
                    f'— {b[4].strip()[:40]!r}')
            # Le bandeau de logos du modèle occupe (17,9 ; 13,9) → (30,7 ;
            # 16,1). Borner le panneau ne suffisait pas : la colonne des
            # kiosques s'écrivait par-dessus.
            if (b[2] / cm > 17.7 and b[0] / cm < 30.9
                    and b[3] / cm > 13.7 and b[1] / cm < 16.1):
                anomalies.append(
                    f'p{n} : un texte recouvre le bandeau de logos '
                    f'(bas {b[3] / cm:.1f} cm) — {b[4].strip()[:40]!r}')
    return anomalies


def main():
    journee, kiosques = lire_programme()
    print(f'{len(journee)} moments, {len(kiosques)} kiosques lus dans la page.')
    souci = 0
    for pptx in construire(journee, kiosques):
        pdf = en_pdf(pptx)
        for f in (pptx, pdf):
            print(f'{f.relative_to(RACINE)}  {f.stat().st_size / 1024:.0f} Ko')
        anomalies = verifier(pdf)
        for a in anomalies:
            print(f'  ✗ {a}')
        souci += len(anomalies)
        if not anomalies:
            print('  ✓ 1 diapo 16:9, tout le texte dans le panneau.')
    sys.exit(1 if souci else 0)


if __name__ == '__main__':
    main()
