#!/usr/bin/env python3
"""Affiche A3 de l'événement, en deux chartes, d'après le modèle Word fourni.

Hors chaîne de production : ce script n'est pas exécuté par le CI et demande
python-pptx, pymupdf, LibreOffice Impress et les polices Barlow.

Le modèle de départ (« 01. A3 TEMPLATE.docx ») est une signalétique
directionnelle du Business Center : photo du lieu en pleine page, panneau vert
translucide à coins arrondis, titre entre guillemets, destination en gras
italique, grosse flèche, et deux logos. On en reprend la composition et les
mesures exactes, relevées dans le document :

    page              42 x 29,7 cm (A3 paysage)
    photo             44,4 x 29,6 cm, débordante
    panneau           36,3 x 24,2 cm, vert #00795C à 85 % d'opacité
    polices           Century Gothic (titre), Arial Black italique (lieu)
    corps             72 pt et 48 pt

Deux écarts assumés au modèle :

  La flèche disparaît. Elle fait du modèle une signalétique de couloir
  (« c'est par là »), pas une affiche d'accueil. Le QR prend sa place au
  centre : c'est lui, ici, qui envoie le lecteur quelque part.

  Les deux logos disparaissent. Ce sont ceux de Crédit Agricole Île-de-France
  et de Prestige Affaires — une autre entité et un autre événement. Le bas du
  panneau leur reste réservé : y déposer le logo CAA est une ligne à ajouter.

Deux sorties :
    affiche-evenement-caa.pptx / .pdf       charte du modèle
    affiche-evenement-programme.pptx / .pdf charte du programme
"""
import pathlib
import subprocess
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Cm, Pt
from lxml import etree

RACINE = pathlib.Path(__file__).resolve().parents[2]
QR = RACINE / 'qr' / 'testing-event-2026.png'
PHOTO = pathlib.Path(__file__).parent / 'ressources' / 'business-center.jpg'
SORTIE = pathlib.Path(__file__).parent
URL = 'info-hub.jeremy-delaux.workers.dev/testing-event-2026/'

EVENEMENT = 'Testing Event'
DATE = 'Lundi 14 septembre 2026'
LIEU = 'Business Center CAA · Auditorium Seine et rez-de-jardin'

# A3 paysage, comme le modèle.
LARGEUR, HAUTEUR = Cm(42), Cm(29.7)
# Panneau du modèle, mesuré dans le document.xml puis centré.
PANNEAU = (Cm(2.85), Cm(2.75), Cm(36.3), Cm(24.2))

VERT_CAA = RGBColor(0x00, 0x79, 0x5C)
ENCRE = RGBColor(0x1A, 0x1A, 0x2E)
TEAL_FONCE = RGBColor(0x00, 0x80, 0x80)
CYAN = RGBColor(0x00, 0xB4, 0xB4)
BLEU_CLAIR = RGBColor(0xD9, 0xEF, 0xEF)
BLANC = RGBColor(0xFF, 0xFF, 0xFF)

MONOGRAMME = RACINE / 'qr' / 'monogramme-te.png'

PROPOSITIONS = {
    # Charte du modèle : photo du lieu, panneau vert translucide, polices
    # Office. Reprise telle quelle, flèche et logos en moins.
    'caa': {
        'photo': True,
        'fond': None,
        'panneau': VERT_CAA, 'opacite': 85,
        'monogramme': None,
        'titre': (f'« {EVENEMENT} »', 'Century Gothic', 72, False, False, BLANC),
        'date': (DATE, 'Arial Black', 44, False, True, BLANC),
        'lieu': (LIEU, 'Century Gothic', 22, False, False, BLANC),
        'legende': ('Le programme complet', 'Century Gothic', 24, BLANC),
        'url': ('Century Gothic', 15, BLANC),
        'y': {'titre': 4.4, 'date': 9.4, 'lieu': 12.0, 'qr': 13.9, 'legende': 23.0},
        'qr_plaque': 8.6,
    },
    # Charte du programme : le fond blanc de la page, le bandeau sombre de son
    # en-tête, le monogramme, et Barlow Condensed. Même composition que le
    # modèle pour que la comparaison porte sur la charte, pas sur la maquette.
    'programme': {
        'photo': False,
        'fond': BLANC,
        'panneau': ENCRE, 'opacite': 100,
        'monogramme': (3.4, 4.0),
        'titre': (EVENEMENT.upper(), 'Barlow Condensed', 100, True, False, BLANC),
        'date': (DATE, 'Barlow Condensed', 46, True, False, CYAN),
        'lieu': (LIEU, 'Barlow', 22, False, False, BLEU_CLAIR),
        'legende': ('LE PROGRAMME COMPLET', 'Barlow Condensed', 28, BLANC),
        'url': ('Barlow', 15, CYAN),
        'y': {'titre': 6.6, 'date': 11.4, 'lieu': 13.8, 'qr': 15.4, 'legende': 23.6},
        'qr_plaque': 7.8,
    },
}


def opacifier(forme, pourcent):
    """Applique une opacité au remplissage : python-pptx ne l'expose pas."""
    if pourcent >= 100:
        return
    srgb = forme.fill.fore_color._xFill.find(qn('a:srgbClr'))
    alpha = etree.SubElement(srgb, qn('a:alpha'))
    alpha.set('val', str(int(pourcent * 1000)))


def bloc(diapo, forme_type, x, y, l, h, couleur, opacite=100):
    forme = diapo.shapes.add_shape(forme_type, x, y, l, h)
    forme.fill.solid()
    forme.fill.fore_color.rgb = couleur
    opacifier(forme, opacite)
    forme.line.fill.background()
    forme.shadow.inherit = False
    # LibreOffice applique l'ombre portée du thème (<a:effectRef>) malgré le
    # <a:effectLst/> vide que pose python-pptx. On retire le style de thème :
    # le remplissage et le contour sont fixés explicitement juste au-dessus.
    style = forme._element.find(qn('p:style'))
    if style is not None:
        forme._element.remove(style)
    return forme


def texte(diapo, x, y, l, h, lignes, ancre=MSO_ANCHOR.TOP):
    zone = diapo.shapes.add_textbox(x, y, l, h)
    cadre = zone.text_frame
    cadre.word_wrap = True
    cadre.vertical_anchor = ancre
    for marge in ('margin_left', 'margin_right', 'margin_top', 'margin_bottom'):
        setattr(cadre, marge, 0)
    for i, (contenu, police, taille, couleur, gras, italique, interligne) in enumerate(lignes):
        p = cadre.paragraphs[0] if i == 0 else cadre.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        p.line_spacing = interligne
        r = p.add_run()
        r.text = contenu
        r.font.name = police
        r.font.size = Pt(taille)
        r.font.bold = gras
        r.font.italic = italique
        r.font.color.rgb = couleur
    return zone


def composer(diapo, p):
    if p['fond'] is not None:
        bloc(diapo, MSO_SHAPE.RECTANGLE, 0, 0, LARGEUR, HAUTEUR, p['fond'])
    if p['photo']:
        # 2722 x 1815 px, soit exactement le rapport 3:2 du cadrage voulu :
        # la photo déborde sans être déformée.
        diapo.shapes.add_picture(str(PHOTO), Cm(-1.2), Cm(0.05), Cm(44.4), Cm(29.6))

    bloc(diapo, MSO_SHAPE.ROUNDED_RECTANGLE, *PANNEAU, p['panneau'], p['opacite'])

    x, l, y = Cm(4.5), Cm(33.0), p['y']

    if p['monogramme']:
        larg, haut = p['monogramme']
        # 156 x 104 px : hauteur déduite pour ne pas déformer le monogramme.
        h = larg * 104 / 156
        diapo.shapes.add_picture(str(MONOGRAMME), int((LARGEUR - Cm(larg)) / 2),
                                 Cm(haut), Cm(larg), Cm(h))

    for clef, hauteur in (('titre', 4.6), ('date', 2.6), ('lieu', 1.4)):
        contenu, police, taille, gras, italique, couleur = p[clef]
        texte(diapo, x, Cm(y[clef]), l, Cm(hauteur),
              [(contenu, police, taille, couleur, gras, italique, 0.95)])

    # ── Le QR prend la place de la flèche du modèle ────────────────────
    # Plaque blanche obligatoire : la zone de silence fait partie du code, et
    # un QR noir sur vert ou sur bleu nuit ne se lit pas.
    plaque = p['qr_plaque']
    code = plaque - 0.8
    bloc(diapo, MSO_SHAPE.RECTANGLE, int((LARGEUR - Cm(plaque)) / 2), Cm(y['qr']),
         Cm(plaque), Cm(plaque), BLANC)
    diapo.shapes.add_picture(str(QR), int((LARGEUR - Cm(code)) / 2),
                             Cm(y['qr'] + 0.4), Cm(code), Cm(code))

    contenu, police, taille, couleur = p['legende']
    police_url, taille_url, couleur_url = p['url']
    texte(diapo, x, Cm(y['legende']), l, Cm(2.4), [
        (contenu, police, taille, couleur, True, False, 1.0),
        (URL, police_url, taille_url, couleur_url, False, False, 1.6),
    ])


def construire(nom, p):
    prez = Presentation()
    prez.slide_width, prez.slide_height = LARGEUR, HAUTEUR
    composer(prez.slides.add_slide(prez.slide_layouts[6]), p)
    chemin = SORTIE / f'affiche-evenement-{nom}.pptx'
    prez.save(chemin)
    return chemin


def en_pdf(pptx):
    subprocess.run(
        ['soffice', '--headless',
         '-env:UserInstallation=file:///tmp/lo-affiches',
         '--convert-to', 'pdf', '--outdir', str(pptx.parent), str(pptx)],
        check=True, capture_output=True, timeout=300)
    return pptx.with_suffix('.pdf')


def verifier(pdf):
    """Une page A3 paysage, et aucun texte dans la zone non imprimable."""
    import pymupdf

    cm = 72 / 2.54
    anomalies = []
    doc = pymupdf.open(pdf)
    if doc.page_count != 1:
        anomalies.append(f'{doc.page_count} pages, 1 attendue.')
    for n, page in enumerate(doc, 1):
        if (abs(page.rect.width / cm - 42) > 0.05
                or abs(page.rect.height / cm - 29.7) > 0.05):
            anomalies.append(f'p{n} : {page.rect.width / cm:.1f} x '
                             f'{page.rect.height / cm:.1f} cm, A3 paysage attendu.')
        for b in page.get_text('blocks'):
            if not b[4].strip():
                continue
            if b[0] / cm < 1.0 or b[2] / cm > 41.0:
                anomalies.append(f'p{n} : un texte risque le rognage '
                                 f'({b[0] / cm:.1f} → {b[2] / cm:.1f} cm).')
    return anomalies


def main():
    souci = 0
    for nom, p in PROPOSITIONS.items():
        pptx = construire(nom, p)
        pdf = en_pdf(pptx)
        for f in (pptx, pdf):
            print(f'{f.relative_to(RACINE)}  {f.stat().st_size / 1024:.0f} Ko')
        anomalies = verifier(pdf)
        for a in anomalies:
            print(f'  ✗ {a}')
        souci += len(anomalies)
        if not anomalies:
            print('  ✓ 1 page A3 paysage, texte dans la zone imprimable.')
    sys.exit(1 if souci else 0)


if __name__ == '__main__':
    main()
