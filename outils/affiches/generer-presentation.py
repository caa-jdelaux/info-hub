#!/usr/bin/env python3
"""La présentation de la journée : quinze diapos, charte du programme.

Hors chaîne de production : ce script n'est pas exécuté par le CI et demande
python-pptx, pymupdf, LibreOffice Impress et les polices Barlow.

Format et charte repris du support en cours de préparation (16:9, 33,87 x 19,05
cm) et de la page programme : bandeau sombre à logo, bandeau rouge à signature,
fond clair, pied de page. Le deck existant était fait de captures d'écran de la
page ; ici tout est du texte, donc modifiable, cherchable et net à la
projection.

Comme pour les affiches et les écrans, les contenus viennent de la page
programme et ne sont pas ressaisis.

CE QUE LE SCRIPT NE SAIT PAS. Les noms — intervenants, animateurs, staff,
partenaires — et les lots ne figurent nulle part dans le dépôt. Ils sont donc
posés en toutes lettres comme « à compléter », en rouge, plutôt qu'inventés.
La diapo de remerciements est un gabarit à remplir, pas une liste.
"""
import html
import pathlib
import re
import subprocess
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Cm, Pt

RACINE = pathlib.Path(__file__).resolve().parents[2]
PAGE = RACINE / 'worker' / 'public' / 'testing-event-2026' / 'index.html'
RES = pathlib.Path(__file__).parent / 'ressources'
QR = RACINE / 'qr' / 'testing-event-2026.png'
LOGO = RES / 'logo-testing-event.png'
SORTIE = pathlib.Path(__file__).parent

LARGEUR, HAUTEUR = Cm(33.87), Cm(19.05)
MARGE = Cm(2.2)
UTILE = Cm(29.47)
HAUT_BANDEAU, HAUT_SIGNATURE, HAUT_PIED = Cm(2.9), Cm(1.2), Cm(1.35)
Y_CONTENU = Cm(4.7)

ENCRE = RGBColor(0x1A, 0x1A, 0x2E)
ROUGE = RGBColor(0xED, 0x1B, 0x2F)
ROUGE_FONCE = RGBColor(0xC0, 0x10, 0x20)
TEAL = RGBColor(0x00, 0x6A, 0x6A)
TEAL_FOND = RGBColor(0x00, 0x80, 0x80)
CYAN = RGBColor(0x00, 0xB4, 0xB4)
CYAN_CLAIR = RGBColor(0xE0, 0xF7, 0xF7)
BLEU_CLAIR = RGBColor(0xD9, 0xEF, 0xEF)
GRIS = RGBColor(0x4A, 0x4A, 0x49)
GRIS_CLAIR = RGBColor(0xF4, 0xF4, 0xF4)
BLANC = RGBColor(0xFF, 0xFF, 0xFF)

CONDENSEE, COURANTE = 'Barlow Condensed', 'Barlow'
A_COMPLETER = '[ à compléter ]'


# ── Lecture de la page programme ───────────────────────────────────────

def net(fragment):
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', fragment)).split())


def lire_programme():
    page = PAGE.read_text(encoding='utf-8')

    signature = re.search(r'class="theme-bar-titre">(.*?)</p>', page, re.S)

    moments = {}
    for m in re.finditer(r'<div class="special-slot"[^>]*data-debut="(\d+)"[^>]*data-fin="(\d+)".*?'
                         r'<div class="slot-label[^"]*">(.*?)</div>', page, re.S):
        libelle = re.sub(r'<span aria-hidden="true">.*?</span>', '', m.group(3), flags=re.S)
        moments[int(m.group(1))] = (int(m.group(2)), net(libelle))

    seances = []
    for m in re.finditer(r'<article class="conf-card"[^>]*data-debut="(\d+)"[^>]*>(.*?)</article>',
                         page, re.S):
        corps = m.group(2)
        seances.append({
            'debut': int(m.group(1)),
            # conf-type porte une classe de couleur en plus, et son étoile est
            # décorative ; le titre est un <h3>, pas un <div>.
            'genre': net(re.sub(r'<span aria-hidden="true">.*?</span>', '',
                                re.search(r'class="conf-type[^"]*">(.*?)</div>',
                                          corps, re.S).group(1), flags=re.S)),
            'titre': net(re.search(r'<h3 class="conf-title">(.*?)</h3>', corps, re.S).group(1)),
            'citation': net(re.search(r'class="conf-pitch">(.*?)</div>', corps, re.S).group(1)),
        })

    kiosques = []
    for m in re.finditer(r'<article class="kiosque-card" data-kiosque="(\d+)">(.*?)</article>',
                         page, re.S):
        nom = re.search(r'<h3 class="kiosque-name">(.*?)</h3>', m.group(2), re.S).group(1)
        kiosques.append({
            'numero': m.group(1),
            'titre': net(re.sub(r'<span aria-hidden="true">.*?</span>', '', nom)),
            'pitch': net(re.search(r'class="kiosque-pitch">(.*?)</div>', m.group(2), re.S).group(1)),
        })

    rotations = [(int(a), int(b)) for a, b in re.findall(
        r'<div class="rotation-slot"[^>]*data-debut="(\d+)" data-fin="(\d+)"', page)]

    if (signature is None or len(seances) != 3 or len(kiosques) != 10
            or len(rotations) != 5 or len(moments) != 5):
        sys.exit(f'programme illisible : {len(moments)} moments, {len(seances)} séances, '
                 f'{len(kiosques)} kiosques, {len(rotations)} rotations')
    return {'signature': net(signature.group(1)), 'moments': moments,
            'seances': seances, 'kiosques': kiosques, 'rotations': rotations}


def hhmm(minutes):
    return f'{minutes // 60}h{minutes % 60:02d}'


# ── Primitives de mise en page ─────────────────────────────────────────

def bloc(diapo, x, y, l, h, couleur, forme=MSO_SHAPE.RECTANGLE):
    f = diapo.shapes.add_shape(forme, x, y, l, h)
    f.fill.solid()
    f.fill.fore_color.rgb = couleur
    f.line.fill.background()
    f.shadow.inherit = False
    # LibreOffice applique l'ombre du thème malgré le <a:effectLst/> vide.
    style = f._element.find(qn('p:style'))
    if style is not None:
        f._element.remove(style)
    return f


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


def ligne(contenu, police=COURANTE, taille=14, couleur=ENCRE, gras=False, interligne=1.3):
    return ([(contenu, police, taille, couleur, gras)], interligne)


def chrome(diapo, prog, numero):
    """Le bandeau, la signature et le pied, identiques sur toutes les diapos."""
    bloc(diapo, 0, 0, LARGEUR, HAUTEUR, GRIS_CLAIR)
    bloc(diapo, 0, 0, LARGEUR, HAUT_BANDEAU, ENCRE)
    diapo.shapes.add_picture(str(LOGO), MARGE, Cm(0.72), Cm(6.9), Cm(6.9 * 104 / 480))
    texte(diapo, Cm(20.0), Cm(0.6), Cm(11.67), Cm(2.0), [
        ligne('14 SEPTEMBRE 2026', CONDENSEE, 20, CYAN, True, 1.0),
        ligne('Business Center · 36/44 bd de Vaugirard', COURANTE, 10, BLEU_CLAIR,
              interligne=1.35),
        ligne('Crédit Agricole Assurances · Paris', COURANTE, 10, BLEU_CLAIR, interligne=1.3),
    ], align=PP_ALIGN.RIGHT)

    bloc(diapo, 0, HAUT_BANDEAU, LARGEUR, HAUT_SIGNATURE, ROUGE)
    texte(diapo, MARGE, Cm(3.18), UTILE, Cm(0.8),
          [ligne('★  ' + prog['signature'].upper() + '  ★', CONDENSEE, 14, BLANC, True, 1.0)],
          align=PP_ALIGN.CENTER)

    bloc(diapo, 0, HAUTEUR - HAUT_PIED, LARGEUR, HAUT_PIED, ENCRE)
    texte(diapo, MARGE, HAUTEUR - Cm(0.95), Cm(24), Cm(0.6),
          [ligne('Testing Event · Crédit Agricole Assurances · 14 septembre 2026',
                 COURANTE, 9, BLEU_CLAIR, interligne=1.0)])
    if numero:
        texte(diapo, Cm(28.0), HAUTEUR - Cm(0.95), Cm(3.67), Cm(0.6),
              [ligne(str(numero), CONDENSEE, 11, CYAN, True, 1.0)], align=PP_ALIGN.RIGHT)


def titre_diapo(diapo, titre, chapeau=None):
    texte(diapo, MARGE, Y_CONTENU, UTILE, Cm(1.4),
          [ligne(titre.upper(), CONDENSEE, 30, ENCRE, True, 1.0)])
    bloc(diapo, MARGE, Cm(6.45), Cm(6.0), Cm(0.09), TEAL_FOND)
    if chapeau:
        texte(diapo, MARGE, Cm(6.9), UTILE, Cm(1.0),
              [ligne(chapeau, COURANTE, 14, GRIS, interligne=1.3)])
        return Cm(8.3)
    return Cm(7.2)


def carte(diapo, x, y, l, h, fond=BLANC, liseré=None):
    bloc(diapo, x, y, l, h, fond)
    if liseré:
        bloc(diapo, x, y, Cm(0.16), h, liseré)


# ── Les quinze diapos ──────────────────────────────────────────────────

def d01_couverture(diapo, prog):
    bloc(diapo, 0, 0, LARGEUR, HAUTEUR, ENCRE)
    bloc(diapo, 0, Cm(12.1), LARGEUR, Cm(1.5), ROUGE)
    diapo.shapes.add_picture(str(LOGO), Cm(9.44), Cm(4.6), Cm(15.0),
                             Cm(15.0 * 104 / 480))
    texte(diapo, MARGE, Cm(12.42), UTILE, Cm(1.0),
          [ligne('★  ' + prog['signature'].upper() + '  ★', CONDENSEE, 18, BLANC, True, 1.0)],
          align=PP_ALIGN.CENTER)
    texte(diapo, MARGE, Cm(14.3), UTILE, Cm(2.4), [
        ligne('LUNDI 14 SEPTEMBRE 2026', CONDENSEE, 30, CYAN, True, 1.0),
        ligne('Business Center · 36/44 bd de Vaugirard · Crédit Agricole Assurances · Paris',
              COURANTE, 13, BLEU_CLAIR, interligne=1.5),
    ], align=PP_ALIGN.CENTER)
    bloc(diapo, Cm(29.3), Cm(15.5), Cm(2.9), Cm(2.9), BLANC)
    diapo.shapes.add_picture(str(QR), Cm(29.5), Cm(15.7), Cm(2.5), Cm(2.5))


def d02_gabarit(diapo, prog):
    chrome(diapo, prog, 2)
    y = titre_diapo(diapo, 'Titre de la diapositive',
                    'Chapeau facultatif : une phrase qui annonce ce que la diapo montre.')
    carte(diapo, MARGE, y, UTILE, Cm(8.4), BLANC, TEAL_FOND)
    texte(diapo, Cm(3.0), y + Cm(0.7), Cm(28.0), Cm(7.0), [
        ligne('ZONE DE CONTENU', CONDENSEE, 16, TEAL, True, 1.0),
        ligne('Dupliquez cette diapositive pour en créer une nouvelle : le bandeau, '
              'la signature et le pied de page suivront.', COURANTE, 13, GRIS, interligne=1.5),
        ligne('La zone utile va de 2,2 cm à 31,7 cm en largeur, et de 4,7 cm à 17,3 cm '
              'en hauteur. Barlow Condensed pour les titres, Barlow pour le texte.',
              COURANTE, 13, GRIS, interligne=1.4),
        ligne('Cette diapositive est un gabarit : retirez-la avant de présenter.',
              COURANTE, 13, ROUGE_FONCE, True, 1.6),
    ])


def d03_programme(diapo, prog):
    chrome(diapo, prog, 3)
    y = titre_diapo(diapo, 'Le programme de la journée')
    m, s, r = prog['moments'], prog['seances'], prog['rotations']

    # Les clefs sont des minutes depuis minuit, pas des heures écrites.
    matin = [(540, m[540][1]), (585, m[585][1])]
    # Le genre (« Conférence 1 », « Table ronde ») est retiré ici : avec lui,
    # trois cartes passaient à deux lignes et la colonne du matin descendait
    # dans le pied de page. Il est porté par les diapos 5 à 7.
    matin += [(x['debut'], x['titre'].split(' : ')[0]) for x in s]
    matin += [(735, m[735][1])]
    matin.sort()
    apresmidi = [(820, m[820][1]),
                 (r[0][0], f"5 rotations de 30 min · 10 kiosques en simultané"),
                 (990, m[990][1])]

    for colonne, (intitule, entrees) in enumerate((
            ('MATIN — CONFÉRENCES', matin), ('APRÈS-MIDI — KIOSQUES & ATELIERS', apresmidi))):
        x = MARGE + Cm(colonne * 15.1)
        texte(diapo, x, y, Cm(14.2), Cm(0.9),
              [ligne(intitule, CONDENSEE, 17, TEAL if colonne == 0 else ROUGE_FONCE, True, 1.0)])
        yy = y + Cm(1.2)
        for debut, libelle in entrees:
            carte(diapo, x, yy, Cm(14.2), Cm(1.28), BLANC,
                  TEAL_FOND if colonne == 0 else ROUGE)
            texte(diapo, x + Cm(0.6), yy + Cm(0.32), Cm(2.4), Cm(0.8),
                  [ligne(hhmm(debut), CONDENSEE, 16, ENCRE, True, 1.0)])
            texte(diapo, x + Cm(3.2), yy + Cm(0.36), Cm(10.6), Cm(0.9),
                  [ligne(libelle, COURANTE, 12, ENCRE, interligne=1.1)])
            yy += Cm(1.5)


def _seance(diapo, prog, index, numero):
    chrome(diapo, prog, numero)
    s = prog['seances'][index]
    fin = s['debut'] + 45
    y = titre_diapo(diapo, s['genre'], f"{hhmm(s['debut'])} – {hhmm(fin)} · Auditorium Seine")
    carte(diapo, MARGE, y, UTILE, Cm(7.6), BLANC, ROUGE)
    texte(diapo, Cm(3.2), y + Cm(0.8), Cm(27.5), Cm(3.4),
          [ligne(s['titre'], CONDENSEE, 26, ENCRE, True, 1.05)])
    texte(diapo, Cm(3.2), y + Cm(4.3), Cm(27.5), Cm(1.6),
          [ligne(s['citation'], COURANTE, 15, TEAL, True, 1.35)])
    texte(diapo, Cm(3.2), y + Cm(6.2), Cm(27.5), Cm(0.9), [([
        ('Intervenant·es : ', COURANTE, 13, GRIS, False),
        (A_COMPLETER, COURANTE, 13, ROUGE_FONCE, True),
    ], 1.0)])


def d04_ouverture(diapo, prog):
    chrome(diapo, prog, 4)
    m = prog['moments']
    y = titre_diapo(diapo, 'Ouverture de la journée')
    for i, (debut, detail) in enumerate((
            (540, "Café, viennoiseries et premiers échanges dans le hall du Business Center."),
            (585, "Le cadre de la journée, en quelques minutes, avant la première conférence."))):
        yy = y + Cm(i * 4.2)
        carte(diapo, MARGE, yy, UTILE, Cm(3.4), BLANC, TEAL_FOND)
        texte(diapo, Cm(3.0), yy + Cm(0.7), Cm(4.4), Cm(1.4),
              [ligne(hhmm(debut), CONDENSEE, 34, ENCRE, True, 1.0)])
        texte(diapo, Cm(8.0), yy + Cm(0.72), Cm(22.5), Cm(2.2), [
            ligne(m[debut][1], CONDENSEE, 22, TEAL, True, 1.0),
            ligne(detail, COURANTE, 13, GRIS, interligne=1.6),
        ])


def d08_cocktail(diapo, prog):
    chrome(diapo, prog, 8)
    m = prog['moments']
    y = titre_diapo(diapo, 'Pause déjeuner')
    carte(diapo, MARGE, y, UTILE, Cm(7.2), BLANC, ROUGE)
    texte(diapo, Cm(3.2), y + Cm(1.0), Cm(27.5), Cm(2.0),
          [ligne(f"{hhmm(735)} · {m[735][1]}", CONDENSEE, 34, ENCRE, True, 1.0)])
    texte(diapo, Cm(3.2), y + Cm(3.4), Cm(27.5), Cm(2.6), [
        ligne("Une heure et demie pour déjeuner, prolonger les échanges du matin "
              "et repérer les kiosques de l'après-midi.", COURANTE, 15, GRIS, interligne=1.5),
        ligne("Reprise à 13h40 avec la présentation de l'organisation des kiosques.",
              COURANTE, 15, TEAL, True, 1.8),
    ])


def d09_apresmidi(diapo, prog):
    chrome(diapo, prog, 9)
    r = prog['rotations']
    y = titre_diapo(diapo, "L'après-midi, mode d'emploi",
                    "Dix kiosques tournent en même temps, cinq fois de suite. "
                    "Vous en faites cinq, dans l'ordre que vous voulez.")
    etapes = [
        ('10', 'kiosques en simultané', 'Dix sujets, dix salles au rez-de-jardin.'),
        ('5', 'rotations identiques', 'Le même kiosque est joué cinq fois : rien à rater.'),
        ('20', 'minutes d\'atelier', 'Puis 5 minutes de questions avant de changer de salle.'),
        ('5', 'kiosques par personne', 'Un par rotation — à vous de composer votre parcours.'),
    ]
    largeur = Cm((29.47 - 3 * 0.7) / 4)
    for i, (chiffre, quoi, detail) in enumerate(etapes):
        x = MARGE + int(i * (largeur + Cm(0.7)))
        carte(diapo, x, y, largeur, Cm(5.4), BLANC, TEAL_FOND)
        texte(diapo, x + Cm(0.7), y + Cm(0.6), largeur - Cm(1.4), Cm(1.8),
              [ligne(chiffre, CONDENSEE, 46, TEAL, True, 1.0)])
        texte(diapo, x + Cm(0.7), y + Cm(2.5), largeur - Cm(1.4), Cm(2.4), [
            ligne(quoi, CONDENSEE, 17, ENCRE, True, 1.0),
            ligne(detail, COURANTE, 11, GRIS, interligne=1.6),
        ])

    yy = y + Cm(6.2)
    carte(diapo, MARGE, yy, UTILE, Cm(2.5), ENCRE)
    texte(diapo, Cm(3.0), yy + Cm(0.45), Cm(8.0), Cm(1.6),
          [ligne('LES 5 ROTATIONS', CONDENSEE, 15, CYAN, True, 1.0)])
    # Cinq cases entre 11,6 cm et le bord droit de la zone utile : la
    # largeur se déduit, elle ne se choisit pas.
    large = int((Cm(31.67) - Cm(11.6) - 4 * Cm(0.4)) / 5)
    for i, (debut, fin) in enumerate(r):
        x = Cm(11.6) + int(i * (large + Cm(0.4)))
        bloc(diapo, x, yy + Cm(0.5), large, Cm(1.5), TEAL_FOND)
        texte(diapo, x, yy + Cm(0.78), large, Cm(1.0),
              [ligne(f'{hhmm(debut)} → {hhmm(fin)}', CONDENSEE, 15, BLANC, True, 1.0)],
              align=PP_ALIGN.CENTER)


def d10_kiosques(diapo, prog):
    chrome(diapo, prog, 10)
    y = titre_diapo(diapo, 'Les dix kiosques')
    largeur = Cm(14.4)
    for i, k in enumerate(prog['kiosques']):
        colonne, rang = i // 5, i % 5
        x = MARGE + int(colonne * (largeur + Cm(0.67)))
        yy = y + int(rang * Cm(2.06))
        carte(diapo, x, yy, largeur, Cm(1.92), BLANC, TEAL_FOND if colonne == 0 else ROUGE)
        texte(diapo, x + Cm(0.5), yy + Cm(0.38), Cm(1.5), Cm(1.0),
              [ligne(k['numero'], CONDENSEE, 22, TEAL if colonne == 0 else ROUGE_FONCE, True, 1.0)])
        texte(diapo, x + Cm(2.3), yy + Cm(0.28), largeur - Cm(2.8), Cm(1.4), [
            ligne(k['titre'], CONDENSEE, 15, ENCRE, True, 1.0),
            ligne(k['pitch'], COURANTE, 8.5, GRIS, interligne=1.35),
        ])


def d11_jeu(diapo, prog):
    chrome(diapo, prog, 11)
    y = titre_diapo(diapo, 'Le jeu — une fiche, une urne, trois gagnants',
                    'Chaque kiosque visité vous rapproche du tirage au sort de fin de journée.')
    etapes = [
        ('1', 'Une fiche', "Vous recevez une fiche en début d'après-midi."),
        ('2', 'Cinq lignes', 'À chaque kiosque, vous y inscrivez vos nom et prénom '
                             'et le numéro du kiosque — cinq fois dans l\'après-midi.'),
        ('3', "Dans l'urne", 'En fin de parcours, vous déposez votre fiche dans '
                             "l'urne prévue à cet effet."),
        ('4', 'Trois gagnants', 'Tirage au sort de trois personnes pour trois lots '
                                'distincts, remis au mot de clôture.'),
    ]
    largeur = Cm((29.47 - 3 * 0.7) / 4)
    for i, (chiffre, quoi, detail) in enumerate(etapes):
        x = MARGE + int(i * (largeur + Cm(0.7)))
        # 7 cm et non 6 : les étapes 2 et 4 tiennent sur quatre lignes, et
        # elles débordaient sous leur carte.
        carte(diapo, x, y, largeur, Cm(7.0), BLANC, ROUGE)
        bloc(diapo, x + Cm(0.7), y + Cm(0.7), Cm(1.5), Cm(1.5), ROUGE, MSO_SHAPE.OVAL)
        texte(diapo, x + Cm(0.7), y + Cm(0.88), Cm(1.5), Cm(1.2),
              [ligne(chiffre, CONDENSEE, 20, BLANC, True, 1.0)], align=PP_ALIGN.CENTER)
        texte(diapo, x + Cm(0.7), y + Cm(2.6), largeur - Cm(1.4), Cm(4.0), [
            ligne(quoi, CONDENSEE, 19, ENCRE, True, 1.0),
            ligne(detail, COURANTE, 10.5, GRIS, interligne=1.5),
        ])

    yy = y + Cm(7.3)
    carte(diapo, MARGE, yy, UTILE, Cm(1.9), CYAN_CLAIR)
    texte(diapo, Cm(3.0), yy + Cm(0.5), Cm(27.5), Cm(1.0), [([
        ('Les trois lots : ', COURANTE, 13, GRIS, False),
        (A_COMPLETER, COURANTE, 13, ROUGE_FONCE, True),
    ], 1.0)])


def d12_qr(diapo, prog):
    chrome(diapo, prog, 12)
    y = titre_diapo(diapo, 'Le programme dans votre poche',
                    'Un QR code sur les affiches, les écrans et à chaque porte de salle.')
    bloc(diapo, MARGE, y, Cm(8.2), Cm(8.2), BLANC)
    diapo.shapes.add_picture(str(QR), MARGE + Cm(0.5), y + Cm(0.5), Cm(7.2), Cm(7.2))

    points = [
        ('Les dix kiosques en détail', 'Le sujet, le pitch, ce que vous allez y faire.'),
        ('La salle de chaque kiosque', 'Publiée le jour même — les affectations tombent tard.'),
        ('Le plan du rez-de-jardin', 'Touchez une salle : elle s\'allume sur le plan.'),
        ('Votre sélection de 5 kiosques', 'Elle reste dans votre téléphone, même après '
                                          'la mise à jour des salles.'),
    ]
    x = Cm(12.6)
    for i, (quoi, detail) in enumerate(points):
        yy = y + int(i * Cm(2.3))
        carte(diapo, x, yy, Cm(19.07), Cm(2.0), BLANC, TEAL_FOND)
        texte(diapo, x + Cm(0.7), yy + Cm(0.32), Cm(17.7), Cm(1.5), [
            ligne(quoi, CONDENSEE, 17, ENCRE, True, 1.0),
            ligne(detail, COURANTE, 11, GRIS, interligne=1.5),
        ])
    texte(diapo, MARGE, y + Cm(8.5), Cm(8.2), Cm(0.8),
          [ligne('Aucune inscription, aucun compte.', COURANTE, 10.5, GRIS, interligne=1.0)],
          align=PP_ALIGN.CENTER)


def d13_cloture(diapo, prog):
    chrome(diapo, prog, 13)
    m = prog['moments']
    y = titre_diapo(diapo, 'Clôture et remise des lots')
    carte(diapo, MARGE, y, UTILE, Cm(7.2), BLANC, ROUGE)
    texte(diapo, Cm(3.2), y + Cm(1.0), Cm(27.5), Cm(2.0),
          [ligne(f'{hhmm(990)} – {hhmm(m[990][0])} · {m[990][1]}',
                 CONDENSEE, 30, ENCRE, True, 1.0)])
    texte(diapo, Cm(3.2), y + Cm(3.4), Cm(27.5), Cm(2.8), [
        ligne('Retour sur la journée, puis tirage au sort de l\'urne : trois fiches, '
              'trois gagnants, trois lots.', COURANTE, 15, GRIS, interligne=1.5),
        ligne('Il faut être présent pour repartir avec son lot.',
              COURANTE, 15, ROUGE_FONCE, True, 1.8),
    ])


def d14_merci(diapo, prog):
    chrome(diapo, prog, 14)
    y = titre_diapo(diapo, 'Merci',
                    'Cette journée est le travail de celles et ceux qui l\'ont préparée, '
                    'animée et soutenue.')
    groupes = [
        ('INTERVENANT·ES DU MATIN', 'Conférences 1 et 2, table ronde'),
        ('ANIMATEUR·RICES DES KIOSQUES', 'Les dix kiosques de l\'après-midi'),
        ('ÉQUIPE D\'ORGANISATION', 'Préparation, logistique, accueil'),
        ('PARTENAIRES', 'Éditeurs et partenaires de la journée'),
    ]
    largeur = Cm((29.47 - 3 * 0.7) / 4)
    for i, (intitule, sous) in enumerate(groupes):
        x = MARGE + int(i * (largeur + Cm(0.7)))
        carte(diapo, x, y, largeur, Cm(8.0), BLANC, TEAL_FOND)
        texte(diapo, x + Cm(0.7), y + Cm(0.7), largeur - Cm(1.4), Cm(2.4), [
            ligne(intitule, CONDENSEE, 15, TEAL, True, 1.05),
            ligne(sous, COURANTE, 10, GRIS, interligne=1.5),
        ])
        texte(diapo, x + Cm(0.7), y + Cm(3.4), largeur - Cm(1.4), Cm(4.0),
              [ligne(A_COMPLETER, COURANTE, 12, ROUGE_FONCE, True, 1.0)])


def d15_fin(diapo, prog):
    bloc(diapo, 0, 0, LARGEUR, HAUTEUR, ENCRE)
    diapo.shapes.add_picture(str(LOGO), Cm(11.44), Cm(3.6), Cm(11.0),
                             Cm(11.0 * 104 / 480))
    texte(diapo, MARGE, Cm(7.4), UTILE, Cm(3.0),
          [ligne('MERCI', CONDENSEE, 66, BLANC, True, 1.0)], align=PP_ALIGN.CENTER)
    bloc(diapo, Cm(14.94), Cm(11.2), Cm(4.0), Cm(0.1), ROUGE)
    texte(diapo, MARGE, Cm(11.9), UTILE, Cm(1.4),
          [ligne('Le programme reste en ligne — scannez, il est à jour.',
                 COURANTE, 14, BLEU_CLAIR, interligne=1.0)], align=PP_ALIGN.CENTER)
    bloc(diapo, Cm(15.09), Cm(13.4), Cm(3.7), Cm(3.7), BLANC)
    diapo.shapes.add_picture(str(QR), Cm(15.34), Cm(13.65), Cm(3.2), Cm(3.2))


DIAPOS = [
    d01_couverture, d02_gabarit, d03_programme, d04_ouverture,
    lambda d, p: _seance(d, p, 0, 5),
    lambda d, p: _seance(d, p, 1, 6),
    lambda d, p: _seance(d, p, 2, 7),
    d08_cocktail, d09_apresmidi, d10_kiosques, d11_jeu, d12_qr,
    d13_cloture, d14_merci, d15_fin,
]


# ── Assemblage et contrôle ─────────────────────────────────────────────

def construire(prog):
    prez = Presentation()
    prez.slide_width, prez.slide_height = LARGEUR, HAUTEUR
    for composer in DIAPOS:
        composer(prez.slides.add_slide(prez.slide_layouts[6]), prog)
    chemin = SORTIE / 'presentation-testing-event.pptx'
    prez.save(chemin)
    return chemin


def en_pdf(pptx):
    subprocess.run(
        ['soffice', '--headless', '-env:UserInstallation=file:///tmp/lo-affiches',
         '--convert-to', 'pdf', '--outdir', str(pptx.parent), str(pptx)],
        check=True, capture_output=True, timeout=600)
    return pptx.with_suffix('.pdf')


def verifier(pdf):
    """Format 16:9, et rien qui déborde de la zone utile.

    Le vrai risque d'un deck généré est le texte qui sort de sa carte ou passe
    sous le pied de page : invisible dans le code, flagrant à la projection.
    """
    import pymupdf

    cm = 72 / 2.54
    anomalies = []
    doc = pymupdf.open(pdf)
    if doc.page_count != len(DIAPOS):
        anomalies.append(f'{doc.page_count} diapos, {len(DIAPOS)} attendues.')
    for n, page in enumerate(doc, 1):
        if (abs(page.rect.width / cm - 33.87) > 0.05
                or abs(page.rect.height / cm - 19.05) > 0.05):
            anomalies.append(f'd{n} : {page.rect.width / cm:.2f} x '
                             f'{page.rect.height / cm:.2f} cm, 16:9 attendu.')
        for b in page.get_text('blocks'):
            contenu = b[4].strip()
            if not contenu:
                continue
            # Le pied occupe la bande 17,70 → 19,05 cm : le texte qui y est
            # posé exprès n'est pas un débordement. La couverture et la diapo
            # de fin n'ont pas de pied et occupent toute la hauteur.
            plancher = 18.7 if n in (1, len(DIAPOS)) else 17.6
            if b[1] / cm < 17.75 and b[3] / cm > plancher:
                anomalies.append(f'd{n} : un texte passe sous le pied de page '
                                 f'({b[3] / cm:.1f} cm) — {contenu[:40]!r}')
            if b[0] / cm < 2.0 or b[2] / cm > 31.9:
                anomalies.append(f'd{n} : un texte sort de la zone utile '
                                 f'({b[0] / cm:.1f}→{b[2] / cm:.1f}) — {contenu[:40]!r}')
    return anomalies


def main():
    prog = lire_programme()
    print(f"{len(prog['seances'])} séances, {len(prog['kiosques'])} kiosques, "
          f"{len(prog['rotations'])} rotations lus dans la page.")
    pptx = construire(prog)
    pdf = en_pdf(pptx)
    for f in (pptx, pdf):
        print(f'{f.relative_to(RACINE)}  {f.stat().st_size / 1024:.0f} Ko')
    anomalies = verifier(pdf)
    for a in anomalies:
        print(f'  ✗ {a}')
    if not anomalies:
        print(f'  ✓ {len(DIAPOS)} diapos 16:9, rien hors zone utile.')
    sys.exit(1 if anomalies else 0)


if __name__ == '__main__':
    main()
