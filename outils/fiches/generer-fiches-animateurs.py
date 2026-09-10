#!/usr/bin/env python3
"""Les antisèches de scène des animateurs — une carte A5 par prise de parole.

Le conducteur (`docs/conducteur-14-septembre.md`) sert à préparer et à tenir la
régie. Il ne se tient pas en main sur scène : quatorze pages, du texte au kilo,
et rien qui se retrouve en deux secondes sous une lumière de poursuite.

Le découpage retenu n'est ni « une fiche par personne » ni « une fiche par
créneau », mais le croisement des deux : **un jeu par animateur, une carte par
prise de parole**, dans l'ordre chronologique et numérotées. Deux raisons.

- Une carte par créneau serait à partager : de 09h45 à 10h00, Ghislaine parle,
  Fabrice parle, Ghislaine reprend, Anas enchaîne. Une carte unique ne peut pas
  être tenue par deux mains différentes à deux moments différents.
- Une carte par personne ne tient pas non plus : Anas a onze prises de parole
  entre 09h56 et 17h00. Sur un seul recto, ou bien on écrit trop petit, ou bien
  on supprime les trois quarts.

Chaque carte porte donc une seule chose à faire, l'heure de fin visée en gros à
droite — c'est l'information la plus consultée sur scène, avant même le
contenu — et la prise de parole suivante en pied de page.

Ce qui n'est pas encore tranché n'est pas inventé : c'est imprimé sous forme de
cadre à remplir au stylo (`trou`). Une carte avec un blanc visible se complète
au briefing ; une carte où le blanc a été comblé par une supposition se dit sur
scène et devient faux.

    python3 outils/fiches/generer-fiches-animateurs.py

Produit `fiches-animateurs.pptx` (modifiable jusqu'au dernier moment) et
`fiches-animateurs.pdf`. Le contrôle relit le PDF et refuse une carte dont le
texte sort de sa zone, ou dont une phrase a été coupée.

**Impression — recto seul, 160 g minimum, et surtout à l'échelle réelle.**
Les pages font exactement 14,85 × 21 cm. Le seul moyen d'obtenir une carte plus
grande que l'A5 est de laisser la boîte de dialogue agrandir : « Ajuster à la
page » sur une imprimante chargée en A4 remonte l'A5 à l'A4 sans le dire.
Choisir « Taille réelle » / « 100 % » — ou, si le bac n'a que de l'A4,
« 2 pages par feuille », qui réduit un peu et ne dépasse donc jamais l'A5.

Dépendances : python-pptx, pymupdf, LibreOffice Impress, les polices Barlow et
Barlow Condensed.
"""

import importlib.util
import pathlib
import re
import subprocess
import sys

from pptx import Presentation
from pptx.oxml.ns import qn
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Cm, Pt

ICI = pathlib.Path(__file__).resolve().parent

# A5 portrait. Le format n'est pas un détail : un A4 tenu en main se voit du
# fond de la salle et bruisse dans le micro-cravate ; un A6 ne prend pas les
# cinq lignes qu'il faut.
LARGEUR, HAUTEUR = Cm(14.85), Cm(21)
MARGE = Cm(1.0)
LARGE = LARGEUR - 2 * MARGE

ENCRE = RGBColor(0x1A, 0x1A, 0x2E)
CYAN = RGBColor(0x00, 0xB4, 0xB4)
TEAL_FONCE = RGBColor(0x00, 0x80, 0x80)
VERT_BC = RGBColor(0x00, 0x6B, 0x4F)
BLANC = RGBColor(0xFF, 0xFF, 0xFF)
GRIS_FONCE = RGBColor(0x4A, 0x4A, 0x49)
GRIS_CLAIR = RGBColor(0xE3, 0xE3, 0xE3)
BLEU_CLAIR = RGBColor(0xD9, 0xEF, 0xEF)
ROUGE = RGBColor(0xB3, 0x2D, 0x2D)

COURANTE, CONDENSEE = 'Barlow', 'Barlow Condensed'

# Même heuristique que `outils/affiches/generer-ecran-complet.py` : on estime
# le nombre de lignes à partir d'une largeur moyenne de signe, volontairement
# pessimiste — mieux vaut une carte qui refuse de se composer qu'une carte qui
# déborde sans le dire.
#
# Deux largeurs ici, parce qu'il y a deux polices. La valeur calée sur Barlow
# Condensed sous-estimait d'un cinquième les lignes de Barlow : une puce du
# message de 12h10 a été composée sur trois lignes au lieu de quatre, et
# LibreOffice a coupé « subie. » à la sortie de la boîte. Le contrôle de
# débordement ne pouvait pas le voir — le texte n'était pas déplacé, il était
# tronqué. D'où la seconde largeur, et le contrôle de troncature en fin de
# fichier, qui relit chaque phrase dans le PDF plutôt que de la supposer.
SIGNE_COURANTE = 0.0172
SIGNE_CONDENSEE = 0.0148
POINT_EN_CM = 2.54 / 72
INTERLIGNE_NATUREL = 1.2

# ── Géométrie de la carte ────────────────────────────────────────────────
BANDEAU_H = Cm(1.25)
ACCENT_H = Cm(0.22)
HAUT_HEURE = Cm(1.95)
HAUT_TITRE = Cm(3.60)
BAS_CORPS = Cm(18.85)
HAUT_PIED = Cm(19.35)


def _haut_ligne(taille, interligne=1.15):
    return Cm(taille * INTERLIGNE_NATUREL * interligne * POINT_EN_CM)


def _lignes(texte, largeur_emu, taille, signe=SIGNE_COURANTE):
    signes = max(1, int((largeur_emu / 360000) / (signe * taille)))
    return max(1, -(-len(texte) // signes))


def _texte(diapo, x, y, l, h, texte, police, taille, couleur,
           gras=False, italique=False, interligne=1.15, align=PP_ALIGN.LEFT):
    zone = diapo.shapes.add_textbox(x, y, l, h)
    cadre = zone.text_frame
    cadre.word_wrap = True
    cadre.margin_left = cadre.margin_right = 0
    cadre.margin_top = cadre.margin_bottom = 0
    p = cadre.paragraphs[0]
    p.alignment = align
    p.line_spacing = interligne
    r = p.add_run()
    r.text = texte
    r.font.name = police
    r.font.size = Pt(taille)
    r.font.bold = gras
    r.font.italic = italique
    r.font.color.rgb = couleur
    return zone


def _pave(diapo, x, y, l, h, fond, bord=None, epaisseur=Pt(0.75)):
    forme = diapo.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, l, h)
    forme.shadow.inherit = False
    if fond is None:
        forme.fill.background()
    else:
        forme.fill.solid()
        forme.fill.fore_color.rgb = fond
    if bord is None:
        forme.line.fill.background()
    else:
        forme.line.color.rgb = bord
        forme.line.width = epaisseur
    forme.text_frame.text = ''
    return forme


def _filet(diapo, x, y, l, couleur, pointille=False):
    ligne = diapo.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x, y, x + l, y)
    ligne.line.color.rgb = couleur
    ligne.line.width = Pt(0.75)
    if pointille:
        ligne.line.dash_style = 4  # msoLineDash
    return ligne


# ── Les six briques du corps ─────────────────────────────────────────────
#
# Chaque brique se mesure et se dessine par la même fonction : mesurer d'un
# côté et dessiner de l'autre, c'est se garantir une dérive silencieuse le jour
# où l'un des deux change.

T_PUCE, T_DIRE, T_NOTE, T_RESERVE = 14, 14.5, 11, 9
RETRAIT = Cm(0.52)

# Corps des quatre colonnes du tableau des kiosques : numéro, thème, salle,
# porteur.
T_KIOSQUE = (13, 11, 10, 9.5)
ECART_COLONNE = 0.16


def _gabarit_kiosques(lignes, l):
    """Largeur des colonnes déduite de la plus longue chaîne de chacune.

    Écrites en dur, elles tenaient tant que les données ne bougeaient pas :
    « CRAN Quality Experts » passait à la ligne et venait écrire sur le kiosque
    suivant, « Sumida + Alzette » touchait la colonne voisine. Un porteur qui
    s'ajoute ou une salle qui change ne doit pas se découvrir à l'impression —
    d'où le calcul, et le refus net si la somme ne tient pas dans la carte.
    """
    colonnes = list(zip(*lignes))
    larges = [max(len(str(v)) for v in col) * SIGNE_COURANTE * taille
              for col, taille in zip(colonnes, T_KIOSQUE)]
    larges[0] = 0.75
    total = sum(larges) + ECART_COLONNE * (len(larges) - 1)
    if total > l / 360000:
        raise SystemExit(
            f'Tableau des kiosques : {total:.2f} cm de colonnes pour '
            f'{l / 360000:.2f} cm disponibles. Raccourcir un thème, une salle '
            f'ou un porteur.')
    positions, x = [], 0.0
    for large in larges:
        positions.append(x)
        x += large + ECART_COLONNE
    return [Cm(p) for p in positions], [Cm(v) for v in larges]


def _brique(diapo, x, y, l, element, accent, dessiner=True):
    genre = element[0]

    if genre == 'puce':
        texte = element[1]
        largeur = l - RETRAIT
        h = _lignes(texte, largeur, T_PUCE) * _haut_ligne(T_PUCE)
        if dessiner:
            _texte(diapo, x, y, RETRAIT, h, '•', COURANTE, T_PUCE, accent, True)
            _texte(diapo, x + RETRAIT, y, largeur, h, texte, COURANTE, T_PUCE, ENCRE)
        return h + Cm(0.22)

    if genre == 'dire':
        texte = '« ' + element[1] + ' »'
        largeur = l - Cm(1.0)
        h = _lignes(texte, largeur, T_DIRE) * _haut_ligne(T_DIRE, 1.2) + Cm(0.44)
        if dessiner:
            _pave(diapo, x, y, l, h, BLEU_CLAIR)
            _pave(diapo, x, y, Cm(0.12), h, accent)
            _texte(diapo, x + Cm(0.5), y + Cm(0.22), largeur, h - Cm(0.44),
                   texte, COURANTE, T_DIRE, ENCRE, False, True, 1.2)
        return h + Cm(0.26)

    if genre == 'note':
        texte = element[1]
        h = _lignes(texte, l, T_NOTE) * _haut_ligne(T_NOTE)
        if dessiner:
            _texte(diapo, x, y, l, h, texte, COURANTE, T_NOTE, GRIS_FONCE)
        return h + Cm(0.20)

    if genre == 'trou':
        libelle, nb = element[1], element[2]
        h = Cm(0.62) + nb * Cm(0.72) + Cm(0.16)
        if dessiner:
            _pave(diapo, x, y, l, h, None, GRIS_CLAIR)
            _texte(diapo, x + Cm(0.3), y + Cm(0.14), l - Cm(0.6), Cm(0.45),
                   'À REMPLIR — ' + libelle.upper(), CONDENSEE, 10, ROUGE, True)
            for i in range(nb):
                _filet(diapo, x + Cm(0.3), y + Cm(0.62) + (i + 1) * Cm(0.72) - Cm(0.12),
                       l - Cm(0.6), GRIS_CLAIR, True)
        return h + Cm(0.26)

    if genre == 'reserve':
        lignes = element[1]
        largeur = l - Cm(0.7)
        hauteurs = [_lignes(t, largeur, T_RESERVE) * _haut_ligne(T_RESERVE, 1.1)
                    for t in lignes]
        h = Cm(0.58) + sum(hauteurs, Cm(0)) + Cm(0.09) * len(lignes) + Cm(0.14)
        if dessiner:
            _pave(diapo, x, y, l, h, None, GRIS_CLAIR)
            _texte(diapo, x + Cm(0.35), y + Cm(0.14), l - Cm(0.7), Cm(0.42),
                   'LE TEXTE DU PORTEUR — À LIRE AVANT, PAS EN SCÈNE',
                   CONDENSEE, 9, GRIS_FONCE, True)
            ly = y + Cm(0.58)
            for texte, haut in zip(lignes, hauteurs):
                _texte(diapo, x + Cm(0.35), ly, largeur, haut, texte,
                       COURANTE, T_RESERVE, GRIS_FONCE, interligne=1.1)
                ly += haut + Cm(0.09)
        return h + Cm(0.24)

    if genre == 'kiosques':
        lignes = element[1]
        # Les cinq kiosques de l'animateur ressortent ; les cinq autres sont là
        # pour qu'il sache quand vient son tour, pas pour qu'il les dise.
        miens = element[2] if len(element) > 2 else None
        cols, larges = _gabarit_kiosques(lignes, l)
        h = Cm(0.52) + len(lignes) * Cm(0.66)
        if dessiner:
            entetes = ('N°', 'KIOSQUE', 'SALLE', 'PORTÉ PAR')
            for cx, cl, titre in zip(cols, larges, entetes):
                _texte(diapo, x + cx, y, cl, Cm(0.42), titre,
                       CONDENSEE, 9.5, GRIS_FONCE, True)
            _filet(diapo, x, y + Cm(0.46), l, GRIS_CLAIR)
            for i, (num, theme, salle, qui) in enumerate(lignes):
                ly = y + Cm(0.52) + i * Cm(0.66)
                mien = miens is None or num in miens
                cellules = (
                    (str(num), CONDENSEE, accent if mien else GRIS_FONCE, True),
                    (theme, COURANTE, ENCRE if mien else GRIS_FONCE, False),
                    (salle, COURANTE, ENCRE if mien else GRIS_FONCE, mien),
                    (qui, COURANTE, GRIS_FONCE, False))
                for c, (txt, police, couleur, gras) in enumerate(cellules):
                    _texte(diapo, x + cols[c], ly, larges[c], Cm(0.55), txt,
                           police, T_KIOSQUE[c], couleur, gras)
        return h + Cm(0.24)

    if genre == 'horaires':
        lignes = element[1]
        h = len(lignes) * Cm(0.78)
        if dessiner:
            for i, (heure, quoi) in enumerate(lignes):
                ly = y + i * Cm(0.78)
                _texte(diapo, x, ly, Cm(3.1), Cm(0.62), heure,
                       CONDENSEE, 15, accent, True)
                _texte(diapo, x + Cm(3.2), ly + Cm(0.05), l - Cm(3.2), Cm(0.62),
                       quoi, COURANTE, 12, ENCRE)
        return h + Cm(0.2)

    raise ValueError(f'brique inconnue : {genre}')


def _carte(prs, deck, accent, numero, total, fiche):
    diapo = prs.slides.add_slide(prs.slide_layouts[6])

    _pave(diapo, 0, 0, LARGEUR, BANDEAU_H, ENCRE)
    _pave(diapo, 0, BANDEAU_H, LARGEUR, ACCENT_H, accent)
    _texte(diapo, MARGE, Cm(0.3), Cm(9.0), Cm(0.7), deck.upper(),
           CONDENSEE, 15, BLANC, True)
    _texte(diapo, LARGEUR - MARGE - Cm(4.0), Cm(0.34), Cm(4.0), Cm(0.7),
           f'{numero} / {total}', CONDENSEE, 13, CYAN, True, align=PP_ALIGN.RIGHT)

    _texte(diapo, MARGE, HAUT_HEURE, Cm(6.0), Cm(1.3), fiche['heure'],
           CONDENSEE, 34, ENCRE, True)
    if fiche.get('fin'):
        large_fin = Cm(4.6)
        # Une heure tient en cinq signes, un nom de salle pas toujours :
        # « Sumida + Alzette » sortait du pavé au corps d'une heure.
        taille_fin = 19 if len(fiche['fin']) <= 8 else 12
        _pave(diapo, LARGEUR - MARGE - large_fin, HAUT_HEURE + Cm(0.08),
              large_fin, Cm(1.35), accent)
        _texte(diapo, LARGEUR - MARGE - large_fin, HAUT_HEURE + Cm(0.22),
               large_fin - Cm(0.3), Cm(0.4), fiche.get('etiquette', 'FIN VISÉE'),
               CONDENSEE, 9, BLANC, True, 1.0, align=PP_ALIGN.RIGHT)
        _texte(diapo, LARGEUR - MARGE - large_fin,
               HAUT_HEURE + (Cm(0.56) if taille_fin > 14 else Cm(0.72)),
               large_fin - Cm(0.3), Cm(0.85), fiche['fin'],
               CONDENSEE, taille_fin, BLANC, True, interligne=1.0,
               align=PP_ALIGN.RIGHT)

    # Le titre prend une ou deux lignes selon sa longueur, et c'est lui qui
    # fixe le haut du corps. Réserver deux lignes pour tout le monde coûtait
    # huit millimètres à vingt-trois cartes pour en servir deux.
    haut_titre = _lignes(fiche['titre'], LARGE, 19, SIGNE_CONDENSEE) * _haut_ligne(19, 1.02)
    _texte(diapo, MARGE, HAUT_TITRE, LARGE, haut_titre, fiche['titre'],
           CONDENSEE, 19, ENCRE, True, interligne=1.02)
    haut_corps = HAUT_TITRE + haut_titre + Cm(0.42)
    _filet(diapo, MARGE, haut_corps - Cm(0.28), LARGE, GRIS_CLAIR)

    y = haut_corps
    if fiche.get('alerte'):
        h = _lignes(fiche['alerte'], LARGE - Cm(0.9), 12) * _haut_ligne(12, 1.15) + Cm(0.4)
        _pave(diapo, MARGE, y, LARGE, h, None, ROUGE)
        _texte(diapo, MARGE + Cm(0.35), y + Cm(0.2), LARGE - Cm(0.9), h - Cm(0.4),
               fiche['alerte'], COURANTE, 12, ROUGE, True)
        y += h + Cm(0.3)

    for element in fiche['corps']:
        y += _brique(diapo, MARGE, y, LARGE, element, accent)

    if y > BAS_CORPS:
        raise SystemExit(
            f'{deck} — carte {numero} « {fiche["titre"]} » : le corps '
            f'descend à {y / 360000:.1f} cm, la limite est '
            f'{BAS_CORPS / 360000:.1f} cm. Raccourcir ou scinder la carte.')

    _filet(diapo, MARGE, HAUT_PIED - Cm(0.3), LARGE, GRIS_CLAIR)
    # Pas de flèche « → » dans ce pied de page : elle n'existe pas dans Barlow,
    # LibreOffice va la chercher dans une autre fonte, et le rendu comme
    # l'extraction du PDF s'en ressentent. Un tiret cadratin fait le même office.
    _texte(diapo, MARGE, HAUT_PIED, LARGE, Cm(1.2), fiche['ensuite'],
           COURANTE, 11.5, GRIS_FONCE, interligne=1.15)
    return diapo


# ═══ CONTENU ═════════════════════════════════════════════════════════════
#
# Sources, et rien d'autre :
#   · les horaires et les salles      → worker/public/testing-event-2026/index.html
#   · les thèmes et porteurs de kiosque → Liste_des_kiosques.xlsx
#   · le déroulé et les messages      → conducteur d'animation, version PDF du
#                                       10/09/2026 (annotée par l'organisation)
# Tout ce qui n'y figure pas est un `trou`, pas une hypothèse.

PAGE = ICI.parents[1] / 'worker' / 'public' / 'testing-event-2026' / 'index.html'


def _programme():
    """Titre, pitch court et salle viennent de la page, pas d'une copie.

    Les salles rouvrent le 14 au matin : une carte qui les porte en dur
    enverrait quelqu'un dans la mauvaise pièce. Le pitch court, lui, est déjà
    calibré pour être dit — il fait sept à huit secondes, là où le texte long
    du fichier source en fait trente à quarante.
    """
    spec = importlib.util.spec_from_file_location(
        'generer_presentation',
        ICI.parents[0] / 'affiches' / 'generer-presentation.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.lire_programme()['kiosques']


def _qui():
    """Les entités et les noms, relus dans la page qui les publie déjà."""
    page = PAGE.read_text(encoding='utf-8')
    qui = {}
    for carte in re.finditer(
            r'<article class="kiosque-card" data-kiosque="(\d+)">(.*?)</article>',
            page, re.S):
        groupes = re.findall(
            r'<span class="qui-groupe">'
            r'<span class="qui-org">(.*?)</span>(.*?)</span>',
            carte.group(2), re.S)
        qui[int(carte.group(1))] = [(o.strip(), n.strip()) for o, n in groupes]
    if len(qui) != 10 or not all(qui.values()):
        sys.exit('les animateurs des kiosques sont illisibles dans la page.')
    return qui


_PAGE_KIOSQUES, _QUI = _programme(), _qui()

# (numéro, thème, salle, entités) — le tableau récapitulatif.
KIOSQUES = [(int(k['numero']), k['titre'], k['salle'],
             ' · '.join(o for o, _ in _QUI[int(k['numero'])]))
            for k in _PAGE_KIOSQUES]

# Qui tient le kiosque, entité et noms, pour que l'animateur le nomme.
PORTEURS = {n: ' / '.join(f'{o} · {noms}' for o, noms in groupes)
            for n, groupes in _QUI.items()}

PITCH_COURT = {int(k['numero']): k['pitch'] for k in _PAGE_KIOSQUES}
SALLES = {int(k['numero']): k['salle'] for k in _PAGE_KIOSQUES}
TITRES = {int(k['numero']): k['titre'] for k in _PAGE_KIOSQUES}

# Le texte long des porteurs, repris mot pour mot de `Liste_des_kiosques.xlsx`,
# colonne D (version du 10/09/2026). Il n'est pas sur la page : c'est la seule
# donnée de ce fichier qui soit recopiée ici, et donc la seule à revérifier si
# le fichier source change. Il n'est pas fait pour être lu en scène — trente à
# quarante secondes à voix haute pour un créneau qui en compte trente en tout,
# transitions comprises. Il est là pour être lu avant, et pour y prendre une
# phrase.
PITCHES_LONGS = {
    1: [
        'Option 1 : La tour de Babel',
        '"Quand les bugs s\'accumulent, tout s\'effondre."',
        "Cet atelier participatif met en scène la fragilité progressive d'un système. À chaque itération, vous construisez en gérant l'apparition croissante de défauts cachés. Plus les bugs sont découverts tard, plus leurs conséquences deviennent catastrophiques.",
        'Option 2 : Marshmallow Challenge',
        '"Tester tôt, c\'est la vraie victoire."',
        "Vous disposez de 18 minutes, 20 spaghettis, 1 chamallow. Construisez la tour la plus haute possible. Mais attention : chaque choix doit être validé rapidement ou vous risquez l'effondrement.",
    ],
    2: [
        '"Lynqa : l\'agent IA qui exécute vos tests manuels pendant que vous dormez."',
        "Savez-vous que 80% des tests fonctionnels restent manuels ? C'est normal : certains sont visuels, trop instables ou trop coûteux à automatiser. Mais ces campagnes manuelles répétitives pèsent lourd : fatigue des testeurs, risques d'erreurs, ressources mobilisées à chaque cycle.",
        'Imaginez :',
        "Un agent IA qui lit vos cas de test existants (sans modification), les exécute automatiquement 24h/24, 7j/7, et produit un rapport détaillé avec captures d'écran étape par étape. Pas de scripting, pas de no-code, pas de restructuration de vos scénarios.",
    ],
    3: [
        '"Coder, Tester, Automatiser... 3 agents IA, une chaîne de production de tests automatisés !"',
        '3 agents IA spécialisés se transmettent le travail : l’un lit le code et en extrait la structure technique, l’autre traduit le besoin métier en scénarios de tests bout en bout, le troisième assemble les deux pour produire les tests fonctionnels automatisés.',
        "le 3ième agent ferme la boucle : un libellé qui a changé, une règle métier absente, un identifiant manquant - tout écart rencontré remonte vers l'agent concerné...",
        "Chaque test automatisé produit enrichit la chaîne qui l'a produit.",
    ],
    4: [
        'De la page blanche à la mise à jour, Yest Companion vous accompagne sur le parcours.',
        'Explication',
        "À partir de vos spécifications (US JIRA, pages Confluence), Yest Companion propose un premier parcours structuré, avec ses tâches métier et son enchaînement, puis le fait évoluer quand les exigences changent. Vous gardez la main à chaque étape : l'IA propose, vous validez ou vous ajustez.",
        'Message clé',
        'Yest Companion accélère la prise en main de Yest et la maintenance des parcours, donc celle des tests.',
    ],
    5: [
        'Arrêtez les triangles et les quadrants : construisez votre VRAIE pyramide de tests !',
        'Fini les théories abstraites ! Plongez les mains dans une pyramide 3D interactive et repositionnez les bons types de test sur chaque face pour construire une stratégie cohérente. Entre tests unitaires, composants, résilience et garantie produit, trouvez le bon équilibre en mode ludique.',
        "Un jeu collaboratif où chaque équipe doit assembler sa pyramide parfaite en faisant glisser, placer et confronter ses choix—parce que comprendre par le jeu, c'est retenir pour de vrai !",
    ],
    6: [
        'Au revoir QC, bienvenue XRAY !',
        '"Moderniser notre outillage QC pour gagner en efficacité, résilience et performance opérationnelle."',
        'Après des années de fidèles services, notre système QC historique va tirer sa révérence en 2027 pour laisser place à XRAY.',
        'Venez découvrir le produit et la trajectoire de migration.',
    ],
    7: [
        'IACA et IACT les assistants des QA en Squad :',
        "Deux agents IA pour aider les QA dans la génération des critères d'acceptance et des cas de test associés sur la base d'US",
        '- Analyser les US pour en extraire les règles, leurs complétudes et leurs cohérences',
        "- Générer des critères d'acceptance et cas de test pour valider les règles identifiées",
        '- Effectuer une couverture complète et optimisée des US',
    ],
    8: [
        'JADD : Los données de production à portée de clic pour vos tests',
        'JADD est un portail offrant différentes fonctionnalités pour gérer vos données de test',
        'En quelques clics, adaptez vos besoins en données de test en un temps record : enrichissez, supprimez, réutilisez, rechargez à nouveau...',
    ],
    9: [
        'SauceLabs à portée de main : développez, testez partout et homologuez en toute confiance.',
        "Découvrez comment intégrer une plateforme de test mobile directement dans votre chaîne de développement locale et centrale, avec la possibilité d'exécuter vos tests d'homologation sur SauceLabs pour valider en conditions réelles.",
        "Des démos live pour explorer les possibilités en temps réel et voir comment vos tests parcourent l'ensemble du cycle de vie – du développement à la validation d'homologation.",
    ],
    10: [
        'TESTY : Mission Qualité Acceptée',
        "Vous ne l'avez pas encore rencontré ?",
        "Plongez dans l'univers coloré et décalé de TESTY, un personnage attachant qui vous fait découvrir les coulisses du métier de testeur à travers des épisodes courts, ludiques et accessibies, sans jargon incompréhensible. Entre des bugs improbables, des situations cocasses et des « ah-ha ! » révélateurs, découvrez que tester, c'est être un vrai détective du code.",
        'Visionnage en libre service.',
    ],
}

REPERES = ('horaires', [
    ('09h45', "Mot d'ouverture — Ghislaine, Fabrice, Anas"),
    ('10h00', 'Conférence 1 — K-LAGAN'),
    ('10h45', 'Conférence 2 — Niji'),
    ('11h30', 'Table ronde — animée par Fabrice'),
    ('12h15', 'Cocktail déjeunatoire'),
    ('13h40', "Organisation de l'après-midi"),
    ('14h00', '5 rotations de 30 min, jusqu’à 16h25'),
    ('16h30', 'Clôture et remise des lots'),
])

CARTE_REPERES = {
    'heure': 'Repères',
    'fin': None,
    'titre': 'La journée en huit lignes',
    'corps': [
        REPERES,
        ('note', "L'heure en haut à gauche de chaque carte est ton entrée en "
                 'scène. Le pavé de couleur à droite est l’heure de fin '
                 'visée : c’est elle qui tient la journée.'),
        ('note', 'Cartes numérotées, recto seul, dans l’ordre. Tu ne '
                 'regardes jamais que celle du dessus.'),
    ],
    'ensuite': 'Carte suivante : ta première prise de parole.',
}


# ── Les dix pitches, répartis entre les deux animateurs ──────────────────
#
# Ce sont les animateurs qui pitchent, pas les porteurs de kiosque : Anas les
# impairs, le second les pairs. Chacun garde son micro d'un bout à l'autre —
# ce que ça fait gagner n'est pas tant la minute de passages de main que la
# variance : deux animateurs qui ont répété tiennent cinq minutes, dix
# intervenants qui montent chacun leur tour, non.
#
# En contrepartie la salle ne voit plus le visage de qui elle retrouvera en
# atelier. D'où la consigne, sur chaque carte, de nommer le porteur et de lui
# faire lever la main : c'est gratuit en temps, et ça rend ce que la mécanique
# enlève.

IMPAIRS, PAIRS = [1, 3, 5, 7, 9], [2, 4, 6, 8, 10]


def _carte_kiosque(numero, autre):
    if numero == 10:
        ensuite = 'Ensuite — 13h49 · le tirage au sort et les lots.'
    elif numero == 9:
        ensuite = (f'Ensuite — le kiosque 10 est pour {autre}, '
                   'puis 13h49 · le tirage au sort.')
    else:
        ensuite = (f'Ensuite — le kiosque {numero + 1} est pour {autre}. '
                   f'Tu reprends au kiosque {numero + 2}.')
    carte = {
        'heure': f'Kiosque {numero}',
        'etiquette': 'SALLE',
        'fin': SALLES[numero],
        'titre': TITRES[numero],
        'corps': [
            ('puce', f'Porté par {PORTEURS[numero]}.'),
            ('note', 'Nomme-les et fais-leur lever la main : la salle doit voir '
                     'le visage qu’elle retrouvera en atelier.'),
            ('dire', PITCH_COURT[numero]),
            ('reserve', PITCHES_LONGS[numero]),
        ],
        'ensuite': ensuite,
    }
    if numero == 10:
        # Deux sources disent deux choses, et c'est ce pitch-là qui les dira à
        # la salle. Mieux vaut que l'animateur le sache avant d'ouvrir la
        # bouche que de le découvrir en salle Sumida.
        carte['alerte'] = (
            '« Libre service » selon la page ; diffusion présentée de '
            'l’épisode 4 selon le conducteur du 10/09. À trancher avant de le dire.')
    return carte


def _carte_repartition(miens, moi, autre_moitie, autre):
    return {
        'heure': '13h44', 'fin': '13h49',
        'titre': f'Les dix pitches — tu prends les {moi}',
        'corps': [
            ('note', f'Vous vous partagez les dix : toi les {moi}, {autre} les '
                     f'{autre_moitie}. Chacun garde son micro d’un bout à '
                     'l’autre — il n’y a plus aucun passage de main, et les '
                     'porteurs de kiosque restent assis.'),
            ('kiosques', KIOSQUES, set(miens)),
            ('note', 'Tes cinq sont en couleur, et chacun a sa carte juste '
                     'après celle-ci. Trente secondes chacun : la phrase à dire '
                     'en fait moins de dix, le reste c’est la salle, les noms, '
                     'et ce que tu veux y ajouter.'),
            ('note', 'Si ça déborde après 13h50 : le rappel des salles passe de '
                     '2 min à 1 min et le tirage se dit debout, sans slide. La '
                     'dispersion de 13h55 ne se sacrifie jamais.'),
        ],
        'ensuite': (f'Ensuite — le kiosque {miens[0]}, ta première carte.'
                    if miens[0] == 1 else
                    f'Ensuite — {autre} ouvre avec le kiosque 1 ; '
                    f'ta première carte est le kiosque {miens[0]}.'),
    }


PITCHS_ANAS = [_carte_kiosque(n, 'le deuxième animateur') for n in IMPAIRS]
PITCHS_SECOND = [_carte_kiosque(n, 'Anas') for n in PAIRS]


ANAS = [
    CARTE_REPERES,
    {
        'heure': '09h56', 'fin': '10h00',
        'titre': 'Relais, QR code, annonce de la conférence 1',
        'corps': [
            ('puce', 'Tu te présentes : tu accompagnes la journée jusqu’à la clôture.'),
            ('puce', 'Slide QR code plein cadre, laissée affichée pendant que tu parles.'),
            ('dire', 'Tout le programme est là, et il vit pendant la journée : '
                     'les dix kiosques, leur pitch, et le numéro de salle de chacun.'),
            ('puce', 'Vingt secondes de silence pour scanner. Compte à voix haute '
                     's’il le faut : un QR code annoncé sans temps de scan n’est pas scanné.'),
            ('puce', 'Conférence 1 — Des 7 principes du test aux 7 principes de la '
                     'qualité. Julien CAHU, K-LAGAN. Remercie K-LAGAN pour son intervention.'),
            ('note', 'Top régie : générique de 15 s, au clic sur la slide de '
                     'présentation. Tu quittes la scène pendant qu’il tourne.'),
        ],
        'ensuite': 'Ensuite — 10h33 · les questions de la conférence 1.',
    },
    {
        'heure': '10h33', 'fin': '10h45',
        'titre': 'Questions, puis annonce de la conférence 2',
        'corps': [
            ('dire', 'On a une dizaine de minutes de questions. Levez la main, un '
                     'micro vient à vous — et attendez le micro, sinon la salle ne '
                     'vous entend pas.'),
            ('puce', 'Les quatre porteurs de micro debout AVANT la fin de la '
                     'conférence, un par travée.'),
            ('puce', 'Aucune main en cinq secondes : tu poses ta première '
                     'question écrite.'),
            ('trou', 'tes deux questions de secours', 2),
            ('puce', '10h40 : « dernière question ». Ça évite de couper quelqu’un.'),
            ('puce', 'Conférence 2 — De l’IA générative aux tests « augmentés ». '
                     'Betty BEAUGE et Gilles NOUAIS, Niji : remercie-les pour le '
                     'déplacement depuis Rennes.'),
        ],
        'ensuite': 'Ensuite — 11h18 · les questions de la conférence 2.',
    },
    {
        'heure': '11h18', 'fin': '11h30',
        'titre': 'Questions, puis annonce de la table ronde',
        'corps': [
            ('puce', 'Même mécanique. Dernière question annoncée à 11h25.'),
            ('puce', 'Question trop pointue sur l’IA : « c’est exactement le sujet '
                     'du kiosque n° X cet après-midi, allez-y avec cette question. »'),
            ('note', 'Kiosques IA : 2 LynQA · 3 Écosystème d’agents · '
                     '4 Yest Companion · 7 SDSI Test & IA.'),
            ('dire', 'Les portes restent ouvertes — si vous devez sortir, n’hésitez pas.'),
            ('note', 'Une seule fois, ici : il n’y a aucune pause entre 09h45 et 12h15.'),
            ('puce', 'Table ronde — Mode produit et les tests. Ghislaine DOPIERRE (TFC), '
                     'Grégory BARRANCO (TMV), Erwan PERIGAULT (SDSI), animée par '
                     'Fabrice CHATRON. Remercie les intervenants.'),
        ],
        'ensuite': 'Ensuite — 12h03 · les questions de la table ronde.',
    },
    {
        'heure': '12h03', 'fin': '12h10',
        'titre': 'Questions de la table ronde',
        'alerte': 'Fabrice est déjà au micro. Sept minutes, pas dix : '
                  'ne promets pas une durée que tu devras reprendre.',
        'corps': [
            ('puce', 'Répartition par défaut : Fabrice ouvre les questions, tu les '
                     'cadres et tu coupes. À confirmer avec lui avant 11h25 — sinon '
                     'vous hésiterez tous les deux en même temps.'),
            ('trou', 'qui ouvre les questions de la table ronde', 1),
            ('puce', '12h08 : dernière question. Le message de 12h10 ne se sacrifie pas.'),
        ],
        'ensuite': 'Ensuite — 12h10 · le message le plus important de la matinée.',
    },
    {
        'heure': '12h10', 'fin': '12h15',
        'titre': 'Le message le plus important de la matinée',
        'alerte': 'C’est ici que la salle décide de rester ou de partir, pas à 13h40.',
        'corps': [
            ('puce', 'Le cocktail est ouvert, et on se retrouve à 13h40 dans cet '
                     'auditorium : dis l’heure deux fois.'),
            ('puce', 'L’après-midi : 10 kiosques, 5 rotations identiques de 30 min, '
                     'chacun son parcours. Des ateliers, des démos, des jeux.'),
            ('dire', 'À chaque kiosque, vous déposez une fiche à votre nom. Cinq '
                     'kiosques, cinq fiches, cinq chances. Tirage à 16h30.'),
            ('trou', 'faut-il être présent dans la salle pour gagner ?', 1),
            ('puce', 'Le QR code à nouveau : « les numéros de salle sont dessus, '
                     'repérez vos cinq pendant le cocktail. »'),
        ],
        'ensuite': 'Ensuite — 13h40 · ouverture de l’après-midi, avec le deuxième animateur.',
    },
    {
        'heure': '13h40', 'fin': '13h44',
        'titre': 'Reprise et principe des rotations',
        'corps': [
            ('puce', 'Vous êtes deux : alternez. Ce bloc n’a aucun moment de '
                     'respiration et arrive juste après le cocktail.'),
            ('dire', 'Quinze minutes, et vous saurez exactement où aller, avec qui, '
                     'et ce qu’il y a à gagner.'),
            ('puce', '10 kiosques tournent en même temps, 5 fois. Les rotations sont '
                     'identiques : rater un kiosque à 14h00 ne veut pas dire l’avoir raté.'),
            ('puce', '30 minutes : 20 d’atelier, 5 de questions, 5 pour se déplacer. '
                     'Le déplacement fait partie du créneau.'),
            ('puce', 'Salles sur le QR code et sur les affiches A3 des portes. '
                     'Horaires : 14h00 · 14h30 · 15h00 · 15h30 · 16h00.'),
        ],
        'ensuite': 'Ensuite — 13h44 · les dix pitches de 30 secondes.',
    },
    _carte_repartition(IMPAIRS, 'impairs', 'pairs', 'le deuxième animateur'),
    *PITCHS_ANAS,
    {
        'heure': '13h49', 'fin': '14h00',
        'titre': 'Lots, rappel des salles, dispersion',
        'corps': [
            ('puce', 'À chaque kiosque, une fiche : nom, prénom, numéro du kiosque. '
                     'Une seule urne, à l’accueil.'),
            ('dire', 'Cinq kiosques, cinq fiches, cinq chances. Trois gagnants, trois lots.'),
            ('trou', 'les trois lots', 3),
            ('trou', 'règle de présence (la même qu’à 12h10)', 1),
            ('puce', '13h52 QR code à l’écran. 13h54 : « on se retrouve ici à 16h30 '
                     'pour la clôture et la remise des lots. » 13h55 : on libère la salle.'),
        ],
        'ensuite': 'Ensuite — 16h33 · la clôture, avec Ghislaine.',
    },
    {
        'heure': '16h33', 'fin': '16h36',
        'titre': 'Synthèse de la journée, avec Ghislaine',
        'alerte': 'Ne commence pas à 16h30 pile : la salle se remplit jusqu’à 16h35 '
                  'depuis dix salles. Musique en fond jusque-là.',
        'corps': [
            ('puce', 'Ce qu’on a vu aujourd’hui, en trois phrases. Pas un récapitulatif.'),
            ('trou', 'nombre de participants — émargements remontés par Lou à 16h', 1),
        ],
        'ensuite': 'Ensuite — 16h36 · les remerciements.',
    },
    {
        'heure': '16h36', 'fin': '16h44',
        'titre': 'Remerciements',
        'alerte': 'Huit minutes pour trois montées sur scène. C’est la séquence '
                  'qui déraille : appelle par groupe, jamais nom par nom.',
        'corps': [
            ('puce', 'Les intervenants extérieurs du matin : K-LAGAN, Niji, et la '
                     'table ronde.'),
            ('puce', 'Les porteurs des dix kiosques.'),
            ('puce', 'Le staff de l’organisation.'),
            ('note', 'Chaque groupe prévenu la veille et déjà debout côté scène avant '
                     '16h30. On nomme les gens une fois qu’ils sont sur scène. Chaque '
                     'groupe y reste : cela évite trois allers-retours.'),
        ],
        'ensuite': 'Ensuite — 16h44 Fabrice conclut, puis 16h48 · le tirage.',
    },
    {
        'heure': '16h48', 'fin': '17h00',
        'titre': 'Tirage, remise des lots, musique de fin',
        'corps': [
            ('puce', 'Rappelle la règle AVANT de tirer : cinq kiosques, cinq fiches, '
                     'trois gagnants, trois lots.'),
            ('puce', 'Fais tirer par un participant — ni staff, ni TFC.'),
            ('puce', 'Un tirage à la fois : on tire, on lit, la personne monte, on '
                     'remet le lot, on applaudit, on passe au suivant.'),
            ('trou', 'cas du gagnant absent — à annoncer avant le premier tirage', 1),
            ('puce', 'Musique de fin sur ta dernière phrase, scène encore pleine. '
                     'Dernier message : merci aux participants.'),
        ],
        'ensuite': 'Fin de journée.',
    },
]

GHISLAINE = [
    CARTE_REPERES,
    {
        'heure': '09h45', 'fin': '09h49',
        'titre': 'Accueil et cadre de la journée',
        'corps': [
            ('puce', 'Bienvenue : le Testing Event, sa raison d’être, pourquoi Crédit '
                     'Agricole Assurances y consacre une journée entière.'),
            ('puce', 'La journée est une journée, pas une matinée : conférences le '
                     'matin, 10 kiosques l’après-midi, clôture à 16h30. Une partie de '
                     'la salle repartira après le cocktail si personne ne le dit.'),
            ('note', 'Ne déroule pas le programme heure par heure ici : c’est ta '
                     'séquence de 09h53, et le faire deux fois coûte trois minutes.'),
            ('puce', 'Annonce du sponsor et passage de parole à Fabrice.'),
            ('note', 'Tu restes en bord de scène pendant qu’il parle. Quatre minutes '
                     'annoncées deviennent huit si personne ne tient la durée : signe '
                     'discret convenu à 09h52.'),
        ],
        'ensuite': 'Ensuite — 09h53 · le programme de la journée.',
    },
    {
        'heure': '09h53', 'fin': '09h56',
        'titre': 'Le programme de la journée',
        'corps': [
            ('puce', 'Matin : deux conférences et une table ronde, questions après chacune.'),
            ('puce', 'Cocktail déjeunatoire à 12h15.'),
            ('puce', 'Reprise à 13h40 pour l’organisation de l’après-midi.'),
            ('puce', '10 kiosques, 5 rotations identiques : chacun choisit ses '
                     'sessions, on ne subit pas un parcours imposé.'),
            ('puce', 'Clôture à 16h30, avec remise de lots.'),
            ('note', 'Passage de relais à Anas, qui prend le QR code.'),
        ],
        'ensuite': 'Ensuite — 11h25 · coulisses de la table ronde.',
    },
    {
        'heure': '11h25', 'fin': '12h15',
        'titre': 'Table ronde — tu es intervenante',
        'alerte': 'Tu n’animes pas cette séquence : c’est Fabrice CHATRON qui anime. '
                  'Cette carte est un repère, pas un script.',
        'corps': [
            ('puce', 'Mode produit et les tests. Angle : « Mode produit ADE : comment '
                     'CAAS transforme ses approches de test pour accompagner la '
                     'fabrication agile ? »'),
            ('puce', 'Avec toi : Grégory BARRANCO (TMV) et Erwan PERIGAULT (SDSI).'),
            ('note', 'Table ronde 32 min au plus, questions de 12h03 à 12h10, puis '
                     'Anas reprend la main pour le message de midi.'),
        ],
        'ensuite': 'Ensuite — 16h33 · la clôture, avec Anas.',
    },
    {
        'heure': '16h33', 'fin': '16h36',
        'titre': 'Synthèse de la journée, avec Anas',
        'alerte': 'Ne commencez pas à 16h30 pile : la salle se remplit jusqu’à 16h35.',
        'corps': [
            ('puce', 'Ce qu’on a vu aujourd’hui, en trois phrases. Pas un récapitulatif.'),
            ('trou', 'nombre de participants — émargements remontés par Lou à 16h', 1),
            ('note', 'Anas enchaîne seul sur les remerciements, puis Fabrice conclut.'),
        ],
        'ensuite': 'Ensuite — 16h48 · le tirage au sort, avec Anas.',
    },
    {
        'heure': '16h48', 'fin': '16h56',
        'titre': 'Tirage au sort et remise des lots, avec Anas',
        'corps': [
            ('puce', 'La règle se rappelle AVANT de tirer : cinq kiosques, cinq '
                     'fiches, trois gagnants, trois lots.'),
            ('puce', 'C’est un participant qui tire — ni staff, ni TFC.'),
            ('puce', 'Un tirage à la fois. Trois noms lus d’affilée désorganisent la scène.'),
            ('trou', 'les trois lots', 3),
        ],
        'ensuite': 'Musique de fin sur la dernière phrase d’Anas.',
    },
]

SECOND = [
    CARTE_REPERES,
    {
        'heure': '13h40', 'fin': '13h44',
        'titre': 'Reprise et principe des rotations, avec Anas',
        'alerte': 'Alternez les prises de parole. Quinze minutes d’instructions '
                  'juste après un cocktail : à deux voix, la salle suit.',
        'corps': [
            ('puce', 'Accueil de reprise, une minute, à deux : « quinze minutes, et '
                     'vous saurez exactement où aller, avec qui, et ce qu’il y a à gagner. »'),
            ('puce', '10 kiosques en même temps, 5 fois, rotations identiques.'),
            ('puce', '30 minutes : 20 d’atelier, 5 de questions, 5 pour se déplacer.'),
            ('puce', 'Horaires : 14h00 · 14h30 · 15h00 · 15h30 · 16h00.'),
            ('trou', 'qui dit quoi — répartition convenue avec Anas', 2),
        ],
        'ensuite': 'Ensuite — 13h44 · les dix pitches, portés par les kiosques.',
    },
    _carte_repartition(PAIRS, 'pairs', 'impairs', 'Anas'),
    *PITCHS_SECOND,
    {
        'heure': '13h49', 'fin': '13h52',
        'titre': 'Le tirage au sort et les lots',
        'corps': [
            ('puce', 'À chaque kiosque, une fiche : nom, prénom, numéro du kiosque.'),
            ('dire', 'Cinq kiosques, cinq fiches, cinq chances.'),
            ('puce', 'Une seule urne, à l’accueil. Trois gagnants, trois lots, '
                     'tirés à 16h30.'),
            ('trou', 'les trois lots', 3),
            ('trou', 'règle de présence pour gagner', 1),
        ],
        'ensuite': 'Ensuite — 13h52 Anas rappelle les salles, puis dispersion à 13h55.',
    },
    {
        'heure': '16h25', 'fin': None,
        'titre': 'Clôture — présent en salle',
        'corps': [
            ('note', 'Le conducteur te demande d’être là de 16h25 à la fin, sans te '
                     'donner de prise de parole. Ce n’est pas un oubli de la carte : '
                     'c’est ce qui est écrit.'),
            ('puce', 'La clôture est tenue par Ghislaine, Anas et Fabrice.'),
            ('trou', 'prise de parole confiée en clôture, le cas échéant', 2),
        ],
        'ensuite': 'Fin de journée.',
    },
]

JEUX = [
    ('Anas', CYAN, ANAS),
    ('Ghislaine', TEAL_FONCE, GHISLAINE),
    ('Deuxième animateur', VERT_BC, SECOND),
]


def _attendus(fiche):
    """Tout ce qui doit se relire dans le PDF, exactement comme il y est écrit.

    Le contrôle qui compte : une phrase mal mesurée n'est pas déplacée, elle
    est coupée au bord de sa boîte. Aucune mesure de position ne le voit.
    """
    textes = [fiche['titre']]
    if fiche.get('fin'):
        textes += [fiche.get('etiquette', 'FIN VISÉE'), fiche['fin']]
    if fiche.get('alerte'):
        textes.append(fiche['alerte'])
    for element in fiche['corps']:
        genre = element[0]
        if genre in ('puce', 'note'):
            textes.append(element[1])
        elif genre == 'dire':
            textes.append('« ' + element[1] + ' »')
        elif genre == 'trou':
            textes.append('À REMPLIR — ' + element[1].upper())
        elif genre == 'reserve':
            textes.append('LE TEXTE DU PORTEUR — À LIRE AVANT, PAS EN SCÈNE')
            textes += element[1]
        elif genre == 'kiosques':
            for num, theme, salle, qui in element[1]:
                textes += [theme, salle, qui]
        elif genre == 'horaires':
            for heure, quoi in element[1]:
                textes += [heure, quoi]
    textes.append(fiche['ensuite'])
    return textes


def en_pdf(pptx):
    subprocess.run(
        ['soffice', '--headless',
         '-env:UserInstallation=file:///tmp/soffice-fiches',
         '--convert-to', 'pdf', '--outdir', str(pptx.parent), str(pptx)],
        check=True, capture_output=True)
    return pptx.with_suffix('.pdf')


def _aplati(texte):
    return ' '.join(texte.split())


def verifier(pdf, attendus):
    """Relit le PDF et refuse ce qui ne se verra qu'une fois imprimé.

    Deux risques, et un seul est visible dans le code : la carte trop pleine est
    déjà refusée à la composition, mais un texte qui frôle le bord se découvre
    au massicot. On mesure donc les blocs du PDF plutôt que de faire confiance
    à la maquette.
    """
    import pymupdf

    cm = 72 / 2.54
    anomalies = []
    doc = pymupdf.open(pdf)
    if doc.page_count != len(attendus):
        anomalies.append(f'{doc.page_count} pages, {len(attendus)} attendues.')
    for n, page in enumerate(doc, 1):
        if (abs(page.rect.width / cm - 14.85) > 0.05
                or abs(page.rect.height / cm - 21) > 0.05):
            anomalies.append(f'p{n} : {page.rect.width / cm:.1f} x '
                             f'{page.rect.height / cm:.1f} cm, A5 portrait attendu.')
        blocs = [(b[0] / cm, b[1] / cm, b[2] / cm, b[3] / cm)
                 for b in page.get_text('blocks') if b[4].strip()]
        for x0, y0, x1, y1 in blocs:
            # 7 mm : la zone non imprimable d'un copieur de bureau en A5.
            if x0 < 0.7 or x1 > 14.15:
                anomalies.append(f'p{n} : un texte risque le rognage '
                                 f'({x0:.1f} → {x1:.1f} cm).')
        corps = [(y0, y1) for _, y0, _, y1 in blocs if 4.5 < y0 < 19.0]
        depasse = max((y1 for _, y1 in corps), default=0)
        if depasse > 19.05:
            anomalies.append(f'p{n} : le corps mord sur le pied de page '
                             f'({depasse:.1f} cm).')
        if n <= len(attendus):
            lu = _aplati(page.get_text())
            for phrase in attendus[n - 1]:
                if _aplati(phrase) not in lu:
                    anomalies.append(f'p{n} : coupé ou absent — « {phrase[:60]}… »')
    return anomalies


def main():
    prs = Presentation()
    prs.slide_width, prs.slide_height = LARGEUR, HAUTEUR
    # python-pptx garde le type de format d'origine (« screen4x3 ») même quand
    # on impose des dimensions. Les lecteurs se fient à cx/cy, mais laisser un
    # type qui contredit les dimensions est une invitation à ce qu'un jour
    # l'un d'eux propose de « remettre au bon format ».
    prs._element.find(qn('p:sldSz')).set('type', 'custom')
    attendus = []
    for deck, accent, fiches in JEUX:
        for i, fiche in enumerate(fiches, 1):
            _carte(prs, deck, accent, i, len(fiches), fiche)
            attendus.append(_attendus(fiche))

    pptx = ICI / 'fiches-animateurs.pptx'
    prs.save(pptx)
    pdf = en_pdf(pptx)
    for f in (pptx, pdf):
        print(f'{f.relative_to(ICI.parents[1])}  ({f.stat().st_size // 1024} Ko)')

    anomalies = verifier(pdf, attendus)
    if anomalies:
        print('\nContrôle :', file=sys.stderr)
        for a in anomalies:
            print('  ·', a, file=sys.stderr)
        return 1
    print(f'\nContrôle : {len(attendus)} cartes, A5 portrait, rien qui '
          f'déborde ni ne se coupe.')
    for deck, _, fiches in JEUX:
        print(f'  · {deck} — {len(fiches)} cartes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
