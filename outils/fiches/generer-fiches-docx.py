#!/usr/bin/env python3
"""Les mêmes fiches de scène, en Word — pour celui qui doit les relire.

Le PDF ne se corrige pas, et le `.pptx` demande PowerPoint et une manipulation
par zone de texte pour changer un mot. Cette version-là est faite pour être
relue et amendée : les blancs à remplir se tapent au clavier, une phrase se
reformule, et on réimprime. C'est la version qui circule avant le jour J ; celle
qui monte sur scène reste `fiches-animateurs.pdf`.

**Le contenu n'est pas recopié.** Il est importé de
`generer-fiches-animateurs.py` : deux fichiers de contenu, ce serait deux
vérités, et la seconde serait fausse le jour où l'une des deux change.

    python3 outils/fiches/generer-fiches-docx.py

Ce que Word ne rend pas comme le PDF, et pourquoi ça ne se rattrape pas :

- **Le bandeau de titre ne va pas bord à bord.** Word compose dans ses marges ;
  un aplat de couleur pleine largeur demande un cadre flottant, qui se déplace
  dès qu'on tape une ligne de trop. Le bandeau est donc encadré par la marge.
- **Word répartit le texte, il ne le pose pas.** Une ligne ajoutée pousse tout
  ce qui suit et peut faire passer une carte sur deux pages. Le contrôle final
  compte les pages : vingt-trois cartes, vingt-trois pages, pas une de plus.

Dépendances : python-docx, python-pptx (par le module de contenu), LibreOffice
et pymupdf pour le contrôle.
"""

import importlib.util
import pathlib
import subprocess
import sys
import tempfile

import docx
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Cm, Pt, RGBColor

ICI = pathlib.Path(__file__).resolve().parent


def _contenu():
    """Charge le générateur A5, dont le nom de fichier n'est pas importable."""
    chemin = ICI / 'generer-fiches-animateurs.py'
    spec = importlib.util.spec_from_file_location('fiches_a5', chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


F = _contenu()

ENCRE, BLANC, GRIS_FONCE = '1A1A2E', 'FFFFFF', '4A4A49'
GRIS_CLAIR, BLEU_CLAIR, ROUGE, CYAN = 'E3E3E3', 'D9EFEF', 'B32D2D', '00B4B4'
COURANTE, CONDENSEE = 'Barlow', 'Barlow Condensed'

# Mêmes corps que la version imprimée : deux tailles pour un même texte
# donneraient deux documents qu'on croit identiques et qui ne le sont pas.
# Word ajoute ses propres espacements de paragraphe et de cellule, mais le
# contrôle de pagination confirme que les vingt-trois cartes tiennent quand
# même chacune sur sa page.
T_HEURE, T_TITRE = 34, 19
T_PUCE, T_DIRE, T_NOTE, T_RESERVE = F.T_PUCE, F.T_DIRE, F.T_NOTE, F.T_RESERVE


def _hex(valeur):
    return RGBColor.from_string(valeur)


def _run(paragraphe, texte, police, taille, couleur,
         gras=False, italique=False):
    r = paragraphe.add_run(texte)
    r.font.name = police
    r.font.size = Pt(taille)
    r.font.color.rgb = _hex(couleur)
    r.font.bold = gras
    r.font.italic = italique
    # Word ne suit `w:ascii` que si `w:cs` suit : sans ça, un accent peut
    # basculer sur la police par défaut au milieu d'un mot.
    r._element.rPr.rFonts.set(qn('w:cs'), police)
    return r


def _para(conteneur, texte, police, taille, couleur, gras=False,
          italique=False, align=WD_ALIGN_PARAGRAPH.LEFT,
          avant=0, apres=2, style=None):
    p = conteneur.add_paragraph(style=style)
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before, pf.space_after = Pt(avant), Pt(apres)
    pf.line_spacing = 1.0
    if texte:
        _run(p, texte, police, taille, couleur, gras, italique)
    return p


def _ombrer(cellule, couleur):
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), couleur)
    cellule._tc.get_or_add_tcPr().append(shd)


def _bordures_cellule(cellule, couleur, epaisseur=6, cotes='tblr'):
    tcPr = cellule._tc.get_or_add_tcPr()
    bords = OxmlElement('w:tcBorders')
    noms = {'t': 'top', 'b': 'bottom', 'l': 'left', 'r': 'right'}
    for cle, nom in noms.items():
        b = OxmlElement(f'w:{nom}')
        actif = cle in cotes
        b.set(qn('w:val'), 'single' if actif else 'nil')
        b.set(qn('w:sz'), str(epaisseur))
        b.set(qn('w:color'), couleur)
        bords.append(b)
    tcPr.append(bords)


def _bordure_paragraphe(paragraphe, cote, couleur, epaisseur=6, style='single'):
    pPr = paragraphe._p.get_or_add_pPr()
    bords = pPr.find(qn('w:pBdr'))
    if bords is None:
        bords = OxmlElement('w:pBdr')
        pPr.append(bords)
    b = OxmlElement(f'w:{cote}')
    b.set(qn('w:val'), style)
    b.set(qn('w:sz'), str(epaisseur))
    b.set(qn('w:space'), '4')
    b.set(qn('w:color'), couleur)
    bords.append(b)


def _marges_cellule(cellule, haut=40, bas=40, gauche=80, droite=80):
    marges = OxmlElement('w:tcMar')
    for nom, valeur in (('top', haut), ('bottom', bas),
                        ('left', gauche), ('right', droite)):
        m = OxmlElement(f'w:{nom}')
        m.set(qn('w:w'), str(valeur))
        m.set(qn('w:type'), 'dxa')
        marges.append(m)
    cellule._tc.get_or_add_tcPr().append(marges)


def _tableau(doc, largeurs):
    """Un tableau sans style ni bordure, aux colonnes verrouillées.

    Les largeurs se posent deux fois — sur la colonne et sur chaque cellule —
    sinon Word et Google Docs les recalculent au premier rendu.
    """
    t = doc.add_table(rows=1, cols=len(largeurs))
    t.autofit = False
    t.allow_autofit = False
    for i, large in enumerate(largeurs):
        t.columns[i].width = large
        for cellule in t.columns[i].cells:
            cellule.width = large
    return t


def _vider(cellule):
    """Une cellule neuve contient déjà un paragraphe vide qui prend sa place."""
    p = cellule.paragraphs[0]
    p._p.getparent().remove(p._p)


LARGE = Cm(12.85)


def _brique(doc, element, accent):
    genre = element[0]

    if genre == 'puce':
        p = _para(doc, None, COURANTE, T_PUCE, ENCRE, style='List Bullet')
        p.paragraph_format.space_after = Pt(3)
        _run(p, element[1], COURANTE, T_PUCE, ENCRE)
        return

    if genre == 'note':
        _para(doc, element[1], COURANTE, T_NOTE, GRIS_FONCE, apres=4)
        return

    if genre == 'dire':
        t = _tableau(doc, [LARGE])
        cellule = t.rows[0].cells[0]
        _ombrer(cellule, BLEU_CLAIR)
        _bordures_cellule(cellule, accent, 18, 'l')
        _marges_cellule(cellule, 60, 60, 140, 140)
        _vider(cellule)
        _para(cellule, '« ' + element[1] + ' »', COURANTE, T_DIRE, ENCRE,
              italique=True, apres=0)
        _para(doc, None, COURANTE, 4, ENCRE, apres=0)
        return

    if genre == 'trou':
        libelle, nb = element[1], element[2]
        t = _tableau(doc, [LARGE])
        cellule = t.rows[0].cells[0]
        _bordures_cellule(cellule, GRIS_CLAIR, 6)
        _marges_cellule(cellule, 60, 60, 120, 120)
        _vider(cellule)
        _para(cellule, 'À REMPLIR — ' + libelle.upper(), CONDENSEE, 10, ROUGE,
              gras=True, apres=6)
        for _ in range(nb):
            ligne = _para(cellule, None, COURANTE, T_PUCE, ENCRE, apres=8)
            _bordure_paragraphe(ligne, 'bottom', GRIS_CLAIR, 6, 'dotted')
        _para(doc, None, COURANTE, 4, ENCRE, apres=0)
        return

    if genre == 'reserve':
        t = _tableau(doc, [LARGE])
        cellule = t.rows[0].cells[0]
        _bordures_cellule(cellule, GRIS_CLAIR, 6)
        _marges_cellule(cellule, 60, 60, 120, 120)
        _vider(cellule)
        _para(cellule, 'LE TEXTE DU PORTEUR — À LIRE AVANT, PAS EN SCÈNE',
              CONDENSEE, 9, GRIS_FONCE, gras=True, apres=4)
        for ligne in element[1]:
            _para(cellule, ligne, COURANTE, T_RESERVE, GRIS_FONCE, apres=3)
        _para(doc, None, COURANTE, 4, ENCRE, apres=0)
        return

    if genre == 'pitch':
        # Même brique que sur la carte imprimée : en-tête, phrase à dire,
        # porteurs. Un filet d'accent à gauche tient lieu du pavé de la version
        # PowerPoint — Word ne sait pas dessiner une barre libre dans le flux.
        numero = element[1]
        t_ent, t_ph, t_qui = F.T_PITCH
        t = _tableau(doc, [LARGE])
        cellule = t.rows[0].cells[0]
        _bordures_cellule(cellule, accent, 18, 'l')
        _marges_cellule(cellule, 0, 0, 140, 0)
        _vider(cellule)
        _para(cellule, f'{numero} · {F.SALLES[numero]} — {F.TITRES[numero]}',
              CONDENSEE, t_ent, accent, gras=True, apres=1)
        _para(cellule, F.PITCH_COURT[numero], COURANTE, t_ph, ENCRE, apres=1)
        _para(cellule, f'Porté par {F.PORTEURS[numero]}.', COURANTE, t_qui,
              GRIS_FONCE, apres=0)
        _para(doc, None, COURANTE, 3, ENCRE, apres=0)
        return

    if genre == 'kiosques':
        miens = element[2] if len(element) > 2 else None
        largeurs = [Cm(0.9), Cm(5.3), Cm(3.0), Cm(3.65)]
        t = _tableau(doc, largeurs)
        entetes = ('N°', 'KIOSQUE', 'SALLE', 'PORTÉ PAR')
        for cellule, titre in zip(t.rows[0].cells, entetes):
            _marges_cellule(cellule, 20, 30, 0, 60)
            _bordures_cellule(cellule, GRIS_CLAIR, 6, 'b')
            _vider(cellule)
            _para(cellule, titre, CONDENSEE, 9.5, GRIS_FONCE, gras=True, apres=0)
        for num, theme, salle, qui in element[1]:
            cellules = t.add_row().cells
            for i, large in enumerate(largeurs):
                cellules[i].width = large
                _marges_cellule(cellules[i], 30, 30, 0, 60)
                _vider(cellules[i])
            mien = miens is None or num in miens
            _para(cellules[0], str(num), CONDENSEE, F.T_KIOSQUE[0],
                  accent if mien else GRIS_FONCE, gras=True, apres=0)
            _para(cellules[1], theme, COURANTE, F.T_KIOSQUE[1],
                  ENCRE if mien else GRIS_FONCE, apres=0)
            _para(cellules[2], salle, COURANTE, F.T_KIOSQUE[2],
                  ENCRE if mien else GRIS_FONCE, gras=mien, apres=0)
            _para(cellules[3], qui, COURANTE, F.T_KIOSQUE[3], GRIS_FONCE, apres=0)
        _para(doc, None, COURANTE, 5, ENCRE, apres=0)
        return

    if genre == 'horaires':
        t = _tableau(doc, [Cm(3.0), Cm(9.85)])
        premiere = True
        for heure, quoi in element[1]:
            cellules = t.rows[0].cells if premiere else t.add_row().cells
            premiere = False
            for cellule, large in zip(cellules, (Cm(3.0), Cm(9.85))):
                cellule.width = large
                _marges_cellule(cellule, 40, 40, 0, 60)
                _vider(cellule)
            _para(cellules[0], heure, CONDENSEE, 15, accent, gras=True, apres=0)
            _para(cellules[1], quoi, COURANTE, 12, ENCRE, apres=0)
        _para(doc, None, COURANTE, 5, ENCRE, apres=0)
        return

    raise ValueError(f'brique inconnue : {genre}')


def _carte(doc, deck, accent, numero, total, fiche, premiere):
    if not premiere:
        saut = _para(doc, None, COURANTE, 1, ENCRE, apres=0)
        saut.paragraph_format.page_break_before = True

    # ── Bandeau ───────────────────────────────────────────────────────────
    bandeau = _tableau(doc, [Cm(8.0), Cm(4.85)])
    for cellule in bandeau.rows[0].cells:
        _ombrer(cellule, ENCRE)
        _marges_cellule(cellule, 70, 70, 120, 120)
        _vider(cellule)
    _para(bandeau.rows[0].cells[0], deck.upper(), CONDENSEE, 15, BLANC,
          gras=True, apres=0)
    _para(bandeau.rows[0].cells[1], f'{numero} / {total}', CONDENSEE, 13,
          CYAN, gras=True, align=WD_ALIGN_PARAGRAPH.RIGHT, apres=0)
    # Le filet d'accent est une seconde ligne du même tableau, pas un
    # paragraphe bordé : un paragraphe garde sa hauteur de ligne et son
    # espacement de bordure, ce qui décollait le filet du bandeau de deux
    # millimètres — visible, et faux.
    filet = bandeau.add_row()
    filet.height, filet.height_rule = Cm(0.12), WD_ROW_HEIGHT_RULE.EXACTLY
    for cellule in filet.cells:
        cellule.width = LARGE
        _ombrer(cellule, accent)
        _marges_cellule(cellule, 0, 0, 0, 0)
        _vider(cellule)
        _para(cellule, None, COURANTE, 1, ENCRE, apres=0)
    _para(doc, None, COURANTE, 4, ENCRE, apres=0)

    # ── Heure et fin visée ────────────────────────────────────────────────
    entete = _tableau(doc, [Cm(7.5), Cm(5.35)])
    gauche, droite = entete.rows[0].cells
    for cellule in (gauche, droite):
        _vider(cellule)
        cellule.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    _marges_cellule(gauche, 0, 0, 0, 60)
    _para(gauche, fiche['heure'], CONDENSEE, T_HEURE, ENCRE, gras=True, apres=0)
    if fiche.get('fin'):
        _ombrer(droite, accent)
        _marges_cellule(droite, 60, 60, 120, 140)
        _para(droite, fiche.get('etiquette', 'FIN VISÉE'), CONDENSEE, 9, BLANC,
              gras=True, align=WD_ALIGN_PARAGRAPH.RIGHT, apres=0)
        _para(droite, fiche['fin'], CONDENSEE,
              19 if len(fiche['fin']) <= 8 else 12, BLANC, gras=True,
              align=WD_ALIGN_PARAGRAPH.RIGHT, apres=0)
    else:
        _para(droite, None, COURANTE, 8, ENCRE, apres=0)

    titre = _para(doc, fiche['titre'], CONDENSEE, T_TITRE, ENCRE, gras=True,
                  avant=4, apres=6)
    _bordure_paragraphe(titre, 'bottom', GRIS_CLAIR, 6)

    if fiche.get('alerte'):
        t = _tableau(doc, [LARGE])
        cellule = t.rows[0].cells[0]
        _bordures_cellule(cellule, ROUGE, 8)
        _marges_cellule(cellule, 70, 70, 140, 140)
        _vider(cellule)
        _para(cellule, fiche['alerte'], COURANTE, 12, ROUGE, gras=True, apres=0)
        _para(doc, None, COURANTE, 4, ENCRE, apres=0)

    for element in fiche['corps']:
        _brique(doc, element, accent)

    # 10 pt au-dessus du filet de pied : deux cartes de bloc dépassaient d'un
    # millimètre, et Word ne dépasse pas — il renvoie la ligne page suivante.
    pied = _para(doc, None, COURANTE, T_NOTE, GRIS_FONCE, avant=6, apres=0)
    _bordure_paragraphe(pied, 'top', GRIS_CLAIR, 6)
    _run(pied, fiche['ensuite'], COURANTE, T_NOTE, GRIS_FONCE)


def _mise_en_page(doc):
    section = doc.sections[0]
    section.page_width, section.page_height = F.LARGEUR, F.HAUTEUR
    section.left_margin = section.right_margin = Cm(1.0)
    section.top_margin = section.bottom_margin = Cm(0.9)
    section.header_distance = section.footer_distance = Cm(0.5)
    normal = doc.styles['Normal']
    normal.font.name = COURANTE
    normal.font.size = Pt(T_PUCE)
    normal.paragraph_format.space_after = Pt(2)
    normal.paragraph_format.line_spacing = 1.0


def verifier(docx_chemin, attendues):
    """Convertit et compte les pages : une carte doit tenir sur une page.

    C'est le seul contrôle qui compte ici. Le générateur A5 pose chaque bloc à
    une position choisie et sait donc dire non ; Word, lui, répartit le texte,
    et une ligne de trop se contente de pousser la suivante sur la page
    d'après — sans erreur, sans avertissement, et sans que le fichier ait l'air
    différent.
    """
    import pymupdf

    # La conversion va dans un dossier temporaire, jamais à côté du .docx :
    # `fiches-animateurs.docx` et `fiches-animateurs.pdf` ne diffèrent que par
    # l'extension, et le PDF voisin est celui de la version imprimée. Écrit ici
    # à la va-vite, ce contrôle l'a d'abord écrasé, puis supprimé en faisant le
    # ménage — sans rien signaler, puisqu'il avait « réussi ».
    anomalies = []
    with tempfile.TemporaryDirectory(prefix='fiches-docx-') as bac:
        subprocess.run(
            ['soffice', '--headless',
             '-env:UserInstallation=file:///tmp/soffice-fiches-docx',
             '--convert-to', 'pdf', '--outdir', bac, str(docx_chemin)],
            check=True, capture_output=True)
        pdf = pathlib.Path(bac) / docx_chemin.with_suffix('.pdf').name
        doc = pymupdf.open(pdf)
        anomalies += _pagination(doc, attendues)
        doc.close()
    return anomalies


def _pagination(doc, attendues):
    anomalies = []
    if doc.page_count != attendues:
        anomalies.append(f'{doc.page_count} pages pour {attendues} cartes : '
                         f'une carte au moins déborde sur une seconde page.')
    cm = 72 / 2.54
    for n, page in enumerate(doc, 1):
        if (abs(page.rect.width / cm - 14.85) > 0.05
                or abs(page.rect.height / cm - 21) > 0.05):
            anomalies.append(f'p{n} : {page.rect.width / cm:.1f} x '
                             f'{page.rect.height / cm:.1f} cm, A5 attendu.')
    return anomalies


def main():
    doc = docx.Document()
    _mise_en_page(doc)
    total = 0
    for deck, accent, fiches in F.JEUX:
        couleur = f'{accent[0]:02X}{accent[1]:02X}{accent[2]:02X}'
        for i, fiche in enumerate(fiches, 1):
            _carte(doc, deck, couleur, i, len(fiches), fiche, premiere=total == 0)
            total += 1

    chemin = ICI / 'fiches-animateurs.docx'
    doc.save(chemin)
    print(f'{chemin.relative_to(ICI.parents[1])}  '
          f'({chemin.stat().st_size // 1024} Ko)')

    anomalies = verifier(chemin, total)
    if anomalies:
        print('\nContrôle :', file=sys.stderr)
        for a in anomalies:
            print('  ·', a, file=sys.stderr)
        return 1
    print(f'\nContrôle : {total} cartes, {total} pages A5, une carte par page.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
