#!/usr/bin/env python3
"""Les affiches A3 des kiosques en Word, variante claire, avec les porteurs.

Ce que cette version ajoute par rapport aux affiches PowerPoint / PDF : **qui
anime le kiosque**, entité et noms, exactement comme la page programme
l'affiche aux participants. Quelqu'un qui hésite devant une porte lit un
numéro, un titre, une phrase — et maintenant le nom de la personne qu'il va
trouver derrière.

    python3 outils/affiches/generer-affiches-docx.py

Sortie unique : `affiches-kiosques-clair.docx`, dix pages A3 portrait, une par
kiosque. Pas de variante sombre : un aplat de couleur pleine page en Word
s'imprime mal et vide les cartouches pour rien.

**Le contenu n'est pas ressaisi.** Titres, pitches, porteurs et rotations sont
lus dans la page programme par `lire_programme()` de `generer-affiches.py`,
qui reste l'unique analyseur. Une correction faite sur la page se retrouve ici
à la prochaine exécution.

Ce que Word ne rend pas comme le PDF, et pourquoi :

- **Les bandeaux ne vont pas bord à bord.** Word compose dans ses marges. Un
  aplat pleine largeur demanderait un cadre flottant, qui se déplace dès qu'une
  ligne s'allonge. Les bandeaux s'arrêtent donc à la marge — et de toute façon
  aucun copieur de bureau n'imprime à fond perdu.
- **Word répartit le texte, il ne le pose pas.** Une ligne de trop pousse la
  suite et fait passer une affiche sur deux pages, sans erreur ni avertissement.
  Le contrôle final compte les pages : dix affiches, dix pages, et relit chaque
  phrase dans le PDF produit pour attraper une troncature.

Les briques Word (ombrage, marges de cellule, bordures) sont importées de
`outils/fiches/generer-fiches-docx.py` plutôt que recopiées. C'est une
dépendance des affiches vers les fiches, ce qui n'est pas le bon sens de
lecture : à remettre dans un module commun après l'événement, pas trois jours
avant, alors que le générateur de fiches est validé et imprimé.

Dépendances : python-docx, python-pptx (via le module d'affiches), LibreOffice
et pymupdf pour le contrôle.
"""

import importlib.util
import pathlib
import subprocess
import sys
import tempfile

import docx
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.shared import Cm, Pt

ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parents[1]


def _module(chemin, nom):
    """Charge un script dont le nom de fichier n'est pas importable."""
    spec = importlib.util.spec_from_file_location(nom, chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = _module(ICI / 'generer-affiches.py', 'affiches_a3')
W = _module(RACINE / 'outils' / 'fiches' / 'generer-fiches-docx.py', 'briques_docx')

_para, _run, _ombrer = W._para, W._run, W._ombrer
_marges_cellule, _tableau, _vider = W._marges_cellule, W._tableau, W._vider

COURANTE, CONDENSEE = 'Barlow', 'Barlow Condensed'
ENCRE, BLANC, GRIS_FONCE = '1A1A2E', 'FFFFFF', '4A4A49'
TEAL_FONCE, TEAL_TEXTE, CYAN, BLEU_CLAIR = '008080', '006A6A', '00B4B4', 'D9EFEF'

# A3 portrait, marges de 1,5 cm : la maquette PowerPoint en garde 2, mais elle
# peut mordre dedans avec ses aplats. Word ne le peut pas, donc la marge est la
# seule réserve de rognage.
PAGE_L, PAGE_H = Cm(29.7), Cm(42)
MARGE_LATERALE, MARGE_HAUTE = Cm(1.5), Cm(1.2)
UTILE = PAGE_L - 2 * MARGE_LATERALE

QR = RACINE / 'qr' / 'testing-event-2026.png'

# Le kiosque 10 occupe deux salles, et depuis l'arbitrage du 11/09 elles ne
# montrent pas la même chose. Les deux affiches ne sont donc plus
# interchangeables : ce qui les distingue est écrit dessus, pas le nom de la
# salle — qui peut encore bouger le matin même.
SEANCES = {
    '10': [
        {
            'label': 'SÉANCE PRÉSENTÉE',
            'titre': 'Le principe de la série, puis l’épisode 4 en exclusivité',
            'texte': 'On vous présente TESTY et les coulisses de la série, puis '
                     'on diffuse le dernier épisode — le 4 — que personne n’a '
                     'encore vu.',
        },
        {
            'label': 'EN LIBRE SERVICE',
            'titre': 'Les trois premiers épisodes, en continu',
            'texte': 'Les épisodes 1, 2 et 3 se succèdent. Entrez et sortez '
                     'quand vous voulez : il n’y a pas de séance à attendre.',
        },
    ],
}
URL = 'info-hub.jeremy-delaux.workers.dev/testing-event-2026/'

# Corps de texte, calés sur la maquette PowerPoint. Une première version plus
# prudente laissait neuf centimètres de blanc en bas de page : sur une porte,
# ce blanc ne sert à rien et la lisibilité de loin, si. Le contrôle final dit
# si ça tient — il a refusé avant d'accepter.
T_MARQUE, T_DATE, T_SURTITRE = 40, 17, 24
T_NUMERO, T_EMOJI, T_TITRE, T_TITRE_LONG = 170, 72, 60, 46
T_PITCH, T_PITCH_SEANCE = 34, 26
T_SEANCE_LABEL, T_SEANCE_TITRE, T_SEANCE = 17, 30, 20
T_INTERTITRE, T_ORG, T_NOMS = 24, 19, 26
T_HEURE, T_FIN, T_LABEL = 34, 19, 14
T_PIED_TITRE, T_PIED, T_URL = 30, 17, 14


def _mise_en_page(doc):
    section = doc.sections[0]
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width, section.page_height = PAGE_L, PAGE_H
    section.left_margin = section.right_margin = MARGE_LATERALE
    section.top_margin = section.bottom_margin = MARGE_HAUTE
    section.header_distance = section.footer_distance = Cm(0.6)
    normal = doc.styles['Normal']
    normal.font.name = COURANTE
    # 11 pt et non le corps du pitch : le style Normal fixe la hauteur des
    # paragraphes qui n'ont pas de taille à eux — le saut de page en est un, et
    # à 34 pt il suffisait à créer une page blanche après huit affiches sur dix.
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.line_spacing = 1.0


def _hauteur_exacte(ligne, hauteur):
    ligne.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    ligne.height = hauteur


def _hauteur_minimale(ligne, hauteur):
    """Pour un bloc dont le contenu varie : il pousse, il ne se fait pas couper.

    Une hauteur exacte coupe en silence — « Référentiel de tests X-Ray » y
    perdait sa seconde ligne sans que rien ne le signale. Une hauteur minimale
    laisse l'affiche déborder, et le contrôle de pagination le voit.
    """
    ligne.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
    ligne.height = hauteur


def _bandeau_tete(doc):
    """Une seule cellule, pas deux : deux cellules laissent un liseré blanc."""
    t = _tableau(doc, [UTILE])
    cellule = t.rows[0].cells[0]
    _ombrer(cellule, ENCRE)
    _marges_cellule(cellule, 200, 200, 200, 200)
    _vider(cellule)
    p = _para(cellule, None, CONDENSEE, T_MARQUE, BLANC, apres=0)
    p.paragraph_format.tab_stops.add_tab_stop(UTILE - Cm(0.4),
                                              WD_TAB_ALIGNMENT.RIGHT)
    _run(p, 'TESTING EVENT', CONDENSEE, T_MARQUE, BLANC, gras=True)
    _run(p, '\t', CONDENSEE, T_MARQUE, BLANC)
    _run(p, 'APRÈS-MIDI · KIOSQUES', CONDENSEE, T_SURTITRE, CYAN, gras=True)
    _para(cellule, 'Lundi 14 septembre 2026 · Business Center CAA',
          COURANTE, T_DATE, CYAN, apres=0)
    _para(doc, None, COURANTE, 10, ENCRE, apres=0)


def _identite(doc, kiosque):
    """Le numéro d'abord : c'est le seul repère lisible depuis le couloir."""
    t = _tableau(doc, [Cm(8.6), UTILE - Cm(8.6)])
    _hauteur_minimale(t.rows[0], Cm(8.6))
    pastille, corps = t.rows[0].cells

    _ombrer(pastille, TEAL_FONCE)
    _marges_cellule(pastille, 0, 0, 0, 0)
    pastille.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    _vider(pastille)
    _para(pastille, kiosque['numero'], CONDENSEE, T_NUMERO, BLANC, gras=True,
          align=WD_ALIGN_PARAGRAPH.CENTER, apres=0)

    _marges_cellule(corps, 0, 0, 340, 0)
    corps.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    _vider(corps)
    _para(corps, kiosque['emoji'], COURANTE, T_EMOJI, ENCRE, apres=6)
    # Un titre long passe à deux lignes et pousse le bas de l'affiche : on le
    # compose plus petit plutôt que de rogner le reste de la page.
    taille = T_TITRE if len(kiosque['titre']) <= 20 else T_TITRE_LONG
    _para(corps, kiosque['titre'], CONDENSEE, taille, ENCRE, gras=True, apres=0)
    _para(doc, None, COURANTE, 12, ENCRE, apres=0)


def _pitch(doc, kiosque, seance):
    # Plus petit quand une séance suit : le pitch dit ce qu'est le kiosque, la
    # séance dit ce qui se passe derrière cette porte-là. La seconde prime.
    taille = T_PITCH_SEANCE if seance else T_PITCH
    p = _para(doc, kiosque['pitch'], COURANTE, taille, GRIS_FONCE, apres=0)
    p.paragraph_format.line_spacing = 1.25
    _para(doc, None, COURANTE, 12, ENCRE, apres=0)


def _seance(doc, seance):
    """Ce qui distingue deux salles d'un même kiosque, dit en toutes lettres."""
    t = _tableau(doc, [UTILE])
    cellule = t.rows[0].cells[0]
    _ombrer(cellule, TEAL_FONCE)
    _marges_cellule(cellule, 200, 200, 240, 240)
    _vider(cellule)
    _para(cellule, seance['label'], CONDENSEE, T_SEANCE_LABEL, BLEU_CLAIR,
          gras=True, apres=4)
    _para(cellule, seance['titre'], CONDENSEE, T_SEANCE_TITRE, BLANC,
          gras=True, apres=6)
    p = _para(cellule, seance['texte'], COURANTE, T_SEANCE, BLANC, apres=0)
    p.paragraph_format.line_spacing = 1.2
    _para(doc, None, COURANTE, 12, ENCRE, apres=0)


def _porteurs(doc, kiosque):
    """Ce que l'affiche PowerPoint ne dit pas encore : qui anime.

    Une ligne par groupe, entité puis noms, dans l'ordre de la page. Un seul
    bloc « TFC · X / DF Dommages · Y » se lit mal de loin, et c'est de loin
    qu'on lit une porte.
    """
    _para(doc, 'ANIMÉ PAR', CONDENSEE, T_INTERTITRE, TEAL_TEXTE, gras=True,
          apres=4)
    t = _tableau(doc, [UTILE])
    cellule = t.rows[0].cells[0]
    _ombrer(cellule, BLEU_CLAIR)
    _marges_cellule(cellule, 160, 160, 220, 220)
    _vider(cellule)
    for i, (org, noms) in enumerate(kiosque['qui']):
        p = _para(cellule, None, COURANTE, T_NOMS, ENCRE,
                  apres=0 if i == len(kiosque['qui']) - 1 else 6)
        _run(p, org, CONDENSEE, T_ORG, TEAL_TEXTE, gras=True)
        _run(p, '   ', COURANTE, T_NOMS, ENCRE)
        _run(p, noms, COURANTE, T_NOMS, ENCRE)
    _para(doc, None, COURANTE, 12, ENCRE, apres=0)


def _rotations(doc, rotations):
    debut = rotations[0][0].split(' – ')[0]
    fin = rotations[-1][0].split(' – ')[-1]
    # Pas de flèche « → » : elle n'existe pas dans Barlow, LibreOffice va la
    # chercher ailleurs et le rendu comme la relecture du PDF s'en ressentent.
    _para(doc, f'5 ROTATIONS DE 30 MINUTES · {debut} à {fin}',
          CONDENSEE, T_INTERTITRE, TEAL_TEXTE, gras=True, apres=4)

    largeur = int(UTILE / 5)
    t = _tableau(doc, [largeur] * 5)
    _hauteur_exacte(t.rows[0], Cm(4.0))
    for cellule, (heure, label) in zip(t.rows[0].cells, rotations):
        depart, arrivee = heure.split(' – ')
        _ombrer(cellule, BLEU_CLAIR)
        _marges_cellule(cellule, 120, 120, 60, 60)
        cellule.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        _vider(cellule)
        _para(cellule, depart, CONDENSEE, T_HEURE, TEAL_TEXTE, gras=True,
              align=WD_ALIGN_PARAGRAPH.CENTER, apres=0)
        _para(cellule, f'jusqu’à {arrivee}', CONDENSEE, T_FIN, TEAL_TEXTE,
              align=WD_ALIGN_PARAGRAPH.CENTER, apres=2)
        _para(cellule, label, COURANTE, T_LABEL, GRIS_FONCE,
              align=WD_ALIGN_PARAGRAPH.CENTER, apres=0)
    _para(doc, None, COURANTE, 12, ENCRE, apres=0)


def _pied(doc):
    t = _tableau(doc, [UTILE - Cm(7.0), Cm(7.0)])
    _hauteur_exacte(t.rows[0], Cm(6.6))
    gauche, droite = t.rows[0].cells
    for cellule in (gauche, droite):
        _ombrer(cellule, ENCRE)
        cellule.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    _marges_cellule(gauche, 160, 160, 220, 120)
    _marges_cellule(droite, 120, 120, 60, 120)
    _vider(gauche)
    _vider(droite)
    _para(gauche, 'LE PROGRAMME COMPLET', CONDENSEE, T_PIED_TITRE, CYAN,
          gras=True, apres=6)
    p = _para(gauche, 'Les dix kiosques, les conférences du matin et le plan '
                      'du rez-de-jardin, salle par salle.',
              COURANTE, T_PIED, BLANC, apres=6)
    p.paragraph_format.line_spacing = 1.25
    _para(gauche, URL, COURANTE, T_URL, CYAN, apres=0)
    # Plaque blanche sous le QR : la zone de silence fait partie du code, et un
    # QR noir sur fond sombre ne se lit pas.
    _ombrer(droite, BLANC)
    p = _para(droite, None, COURANTE, 10, ENCRE,
              align=WD_ALIGN_PARAGRAPH.CENTER, apres=0)
    p.add_run().add_picture(str(QR), width=Cm(5.6))


def _saut_de_page(doc):
    """Un saut de page qui ne pèse rien.

    `add_page_break()` pose un paragraphe au corps du style Normal. Posé après
    un tableau qui finit près du bas de page, ce paragraphe ne tient plus et
    part seul sur une page vide — l'affiche suivante n'arrive qu'à la page
    d'après. Une page blanche entre deux affiches, invisible tant qu'on ne les
    compte pas.
    """
    p = _para(doc, None, COURANTE, 1, ENCRE, apres=0)
    p.add_run().add_break(WD_BREAK.PAGE)


def _affiche(doc, kiosque, rotations, seance=None):
    _bandeau_tete(doc)
    _identite(doc, kiosque)
    _pitch(doc, kiosque, seance)
    if seance:
        _seance(doc, seance)
    _porteurs(doc, kiosque)
    _rotations(doc, rotations)
    _pied(doc)


def _attendus(kiosque, rotations, seance=None):
    """Tout ce qui doit se relire dans le PDF, exactement comme il y est écrit.

    L'emoji n'en fait pas partie : Barlow ne l'a pas, LibreOffice le prend
    ailleurs, et l'extraction le rend dans un ordre qui n'est pas le sien.
    """
    textes = ['TESTING EVENT', 'APRÈS-MIDI · KIOSQUES',
              'Lundi 14 septembre 2026 · Business Center CAA',
              kiosque['numero'], kiosque['titre'], kiosque['pitch'],
              'ANIMÉ PAR']
    if seance:
        textes += [seance['label'], seance['titre'], seance['texte']]
    for org, noms in kiosque['qui']:
        textes += [org, noms]
    for heure, label in rotations:
        depart, arrivee = heure.split(' – ')
        textes += [depart, f'jusqu’à {arrivee}', label]
    textes += ['LE PROGRAMME COMPLET', URL]
    return textes


def _aplati(texte):
    return ' '.join(texte.split())


def verifier(chemin, attendues):
    """Convertit et relit : une affiche par page, et rien de coupé.

    Compter les pages ne suffit pas. Une phrase trop longue n'est pas déplacée
    par Word, elle peut être rendue au-delà de sa cellule et disparaître à
    l'impression. On relit donc chaque phrase dans le PDF produit.
    """
    import pymupdf

    cm = 72 / 2.54
    anomalies = []
    # Conversion dans un dossier temporaire : le `.docx` et le `.pdf` des
    # affiches PowerPoint ne diffèrent que par l'extension, et une conversion
    # posée à côté écraserait le PDF qui part à l'impression.
    with tempfile.TemporaryDirectory(prefix='affiches-docx-') as bac:
        subprocess.run(
            ['soffice', '--headless',
             '-env:UserInstallation=file:///tmp/soffice-affiches-docx',
             '--convert-to', 'pdf', '--outdir', bac, str(chemin)],
            check=True, capture_output=True, timeout=300)
        pdf = pathlib.Path(bac) / chemin.with_suffix('.pdf').name
        doc = pymupdf.open(pdf)
        if doc.page_count != len(attendues):
            anomalies.append(f'{doc.page_count} pages pour {len(attendues)} '
                             'affiches : une affiche au moins déborde sur une '
                             'seconde page.')
        for n, page in enumerate(doc, 1):
            if (abs(page.rect.width / cm - 29.7) > 0.05
                    or abs(page.rect.height / cm - 42) > 0.05):
                anomalies.append(f'p{n} : {page.rect.width / cm:.1f} x '
                                 f'{page.rect.height / cm:.1f} cm, '
                                 'A3 portrait attendu.')
            if n <= len(attendues):
                lu = _aplati(page.get_text())
                for phrase in attendues[n - 1]:
                    if _aplati(phrase) not in lu:
                        anomalies.append(
                            f'p{n} : coupé ou absent — « {phrase[:60]}… »')
        doc.close()
    return anomalies


def _produire(nom, pages, rotations):
    """pages : liste de (kiosque, séance ou None). Une page par élément."""
    doc = docx.Document()
    _mise_en_page(doc)
    for i, (kiosque, seance) in enumerate(pages):
        if i:
            _saut_de_page(doc)
        _affiche(doc, kiosque, rotations, seance)

    chemin = ICI / nom
    doc.save(chemin)
    print(f'{chemin.relative_to(RACINE)}  '
          f'{chemin.stat().st_size / 1024:.0f} Ko')
    anomalies = verifier(chemin, [_attendus(k, rotations, s) for k, s in pages])
    for a in anomalies:
        print(f'  · {a}')
    if not anomalies:
        print(f'  ✓ {len(pages)} affiches, {len(pages)} pages A3 portrait, '
              'rien de coupé.')
    return anomalies


def main():
    kiosques, rotations = A.lire_programme()
    par_numero = {k['numero']: k for k in kiosques}

    # Le jeu complet garde une seule affiche par kiosque : c'est celui qu'on
    # tire pour les dix portes. Les deux salles du kiosque 10 ont leur propre
    # fichier, parce qu'elles ne montrent pas la même chose et qu'une affiche
    # de trop dans le jeu complet se colle au mauvais endroit.
    anomalies = _produire('affiches-kiosques-clair.docx',
                          [(k, None) for k in kiosques], rotations)
    anomalies += _produire(
        'affiches-kiosque-10-clair.docx',
        [(par_numero['10'], seance) for seance in SEANCES['10']], rotations)
    return 1 if anomalies else 0


if __name__ == '__main__':
    sys.exit(main())
