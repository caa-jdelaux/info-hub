# info-hub

Pages d'information statiques, servies par un Worker Cloudflare.

Contenu actuel : le **programme du Testing Event du 14 septembre 2026**
(Crédit Agricole Assurances), à `/testing-event-2026/`.

---

## Procédure du jour J — affecter les salles depuis un téléphone

Les salles des 10 kiosques ne sont connues qu'au dernier moment et peuvent
changer jusqu'au début de l'après-midi. Elles se modifient **sans outil, depuis
un navigateur mobile**, en éditant un seul bloc.

1. Ouvrir sur GitHub :
   `worker/public/testing-event-2026/index.html`, **branche `dev`**.
2. Appuyer sur l'icône crayon (✏️).
3. Le bloc à modifier est **en tête de fichier, ligne 18** — aucun défilement
   nécessaire :

   ```json
   {
     "1": "Salle Vaugirard",
     "2": "Salle 2.14",
     ...
     "10": "Auditorium"
   }
   ```

   Écrire la salle entre guillemets. Laisser `""` tant qu'elle est inconnue :
   la carte affiche alors « Salle à confirmer » en gris.
   **Ne pas oublier la virgule en fin de ligne, sauf sur la dernière (kiosque 10).**
4. Valider (*Commit changes*) sur `dev`.
5. Vérifier le rendu sur `info-hub-dev.<sous-domaine>.workers.dev/testing-event-2026/`.
6. Reporter sur `prod` (*Pull request* de `dev` vers `prod`, ou édition directe
   du même bloc sur `prod`).

Les pages déjà ouvertes sur les téléphones se mettent à jour toutes seules :
inutile de demander à qui que ce soit de recharger (voir *Rafraîchissement
automatique*).

Sous le bandeau final s'affiche la date, l'heure et la révision du déploiement
en cours : **c'est ce qui permet de distinguer sa propre version d'une copie en
cache.** Si l'horodatage n'est pas celui de la publication qu'on vient de faire,
la page affichée n'est pas à jour — recharger.

Hors production, deux repères le signalent : un **bandeau orange rayé collant
en haut de page**, visible en permanence pendant le défilement, et une **puce
DEV** devant la version en bas. Si l'un des deux est là, on ne regarde pas
l'adresse du QR code imprimé.

Les deux sont pilotés par l'attribut `data-env` de la racine du document, écrit
au déploiement depuis le même marqueur que la version. Le bandeau est masqué par
défaut et n'apparaît que si `data-env` n'est pas vide : c'est l'affichage qui est
l'exception, jamais le masquage — une règle oubliée ne peut pas le faire
surgir devant les participants.

### Si quelque chose casse

- Une erreur de syntaxe dans le bloc **bloque le déploiement** : la porte
  qualité le refuse avant toute mise en ligne. La page en ligne reste celle
  d'avant, jamais une page cassée.
- Si malgré tout le bloc devenait illisible côté navigateur, les cartes
  affichent « Voir affichage sur place ». La signalétique des portes fait foi.

---

## Architecture

```
worker/
  wrangler.jsonc                       Worker « assets seuls » (aucun script)
  public/
    _headers                           Cache-Control, en-têtes de sécurité
    _redirects                         /  ->  /testing-event-2026/  (302)
    404.html
    testing-event-2026/index.html      La page. Autonome : zéro requête externe.
    assets/fonts/                      Barlow auto-hébergée (SIL OFL 1.1)
scripts/
  check-page.mjs                       Porte qualité
  inject-version.mjs                   Version et puce d'environnement
  check-deploiement.mjs                Contrôle de ce que l'URL sert vraiment
  generer-qr.mjs                       QR code de l'URL de production
qr/
  testing-event-2026.svg               QR vectoriel — à fournir à l'imprimeur
  testing-event-2026.png               Rendu 2000 px, pour les supports non vectoriels
  monogramme-te.png                    Monogramme placé au centre du code
```

## QR code

`qr/testing-event-2026.svg` encode l'URL de production et porte le monogramme
« TE » au centre. Il se régénère par `npm run qr`.

Le logo recouvre des modules du code : c'est la correction d'erreur qui absorbe
la perte. La plaque centrale **épouse le format du monogramme** (1,5:1) au lieu
d'être carrée — une plaque carrée laissait du blanc en haut et en bas, et ce
blanc recouvrait des modules sans rien afficher.

La taille du logo est réglée par la mesure, pas à l'estime. En balayant les
tailles et en redécodant chaque rendu, le code passe encore à **21,0 %** de
surface recouverte et casse à **25,3 %**. Ces chiffres valent en conditions
idéales : rendu parfait, sans grain, sans angle, sans pli. Un appareil photo
sur du papier imprimé dispose de bien moins de marge, d'où le facteur deux
conservé : la plaque occupe **12,2 %** de la surface, et un test refuse toute
valeur qui ne garderait pas ce facteur deux.

Le code a été décodé après rendu à 150, 200, 300, 512, 1024 et 2000 px :
l'URL ressort exacte dans les six cas. Un test compare en outre le fichier
committé à ce que le script produit pour l'URL de production, afin que le SVG
parti à l'impression ne puisse pas dériver silencieusement.

**Préférer le SVG pour l'impression** : le code reste vectoriel, donc net à
toute taille. Le PNG est une rasterisation de dépannage.

## Plan des salles

Les kiosques se tiennent au rez-de-jardin du Business Center CAA. Treize salles
sont situables sur le plan : les dix magenta, Sumida et Alzette (violettes, en
bas à droite) et Donau (verte, au centre). Garonne et l'auditorium Seine n'en
font pas partie.

| Kiosque | Salle | Kiosque | Salle |
|---|---|---|---|
| 1 | Wisla | 6 | Tajo |
| 2 | Donau | 7 | Adige |
| 3 | Liffey | 8 | Loire |
| 4 | Douro | 9 | Moselle |
| 5 | Rhône | 10 | Sumida **+** Alzette |

Tevere et Rhin restent dans la table sans être affectées : y figurer rend une
salle **situable**, pas occupée. L'affectation, elle, tient dans le bloc
`salles-data` en tête de page — c'est le seul endroit à toucher le 14.

**Un kiosque peut occuper plusieurs salles.** Il suffit de les nommer dans la
même case (`"Sumida + Alzette"`) : la page les reconnaît toutes, perce un trou
par salle dans le voile, et n'entoure d'un seul anneau que celles assez
proches pour que deux anneaux se chevaucheraient. La phrase de repérage les
nomme alors une par une.

**Une seule image est servie** — `worker/public/assets/plans/rez-de-jardin.png`,
27 Ko, le plan nu. La mise en évidence d'une salle est dessinée par-dessus en
SVG dans la page : un voile percé d'un trou au rectangle de la salle, puis un
halo blanc et un anneau sombre. Une image gravée par salle aurait pesé une
trentaine de Ko pièce, se serait pixellisée au zoom, et changer une salle
aurait demandé de recommitter des binaires. Ici, une salle coûte quatre nombres
dans la table `PLAN_SALLES` de la page — c'est ce qui a rendu l'ajout de Sumida
et d'Alzette trivial.

Ces coordonnées viennent de `outils/plans/generer-plans.py`, qui les tient de
la segmentation des aplats de couleur. Elles sont figées dans le script comme
dans la page — un changement de plan doit être constaté et revu, pas absorbé en
silence. Le script régénère aussi les aperçus gravés, un par salle, dans
`outils/plans/apercus/` : ils servent de contrôle visuel et ne sont pas servis.
Il demande Pillow et numpy ; le CI ne l'exécute pas.

## Affiches A3 des kiosques

`outils/affiches/generer-affiches.py` produit dix affiches A3 portrait, une par
thème, à coller sur la porte des salles. Deux variantes à comparer sur papier :

| Fichier | Usage |
|---|---|
| `affiches-kiosques-clair.pdf` | fond blanc — c'est le PDF qui part à l'impression |
| `affiches-kiosques-sombre.pdf` | fond sombre, même contenu |
| `affiches-kiosques-*.pptx` | pour corriger sur place ; suppose Barlow Condensed installée |

**Les affiches ne nomment aucune salle.** Les affectations ont bougé deux fois
la semaine de l'événement ; une affiche muette sur ce point se déplace d'une
porte à l'autre au lieu de se réimprimer. Le kiosque 10 occupe deux salles :
c'est la même affiche, tirée en deux exemplaires — soit **onze feuilles pour
dix affiches**.

Les thèmes ne sont pas ressaisis dans le script : il les lit dans
`index.html`, qui reste la source unique. Une correction de pitch faite sur la
page se retrouve sur l'affiche à la prochaine exécution, et une affiche ne peut
pas diverger en silence de ce que les participants lisent sur leur téléphone.

Trois pièges que le script traite, et qui font rater une affiche autrement :

- **La taille de diapo.** PowerPoint ouvre en 33,87 × 19,05 cm ; le script fixe
  29,7 × 42 cm pour que 1 diapo = 1 page A3 exacte, sans recadrage du pilote.
- **La police.** Barlow Condensed est une police Google, absente de Windows et
  d'Office. Le PDF l'embarque, donc l'impression est fidèle ; le `.pptx`, lui,
  suppose qu'elle soit installée sur le poste qui l'ouvre.
- **Le débordement.** Le script relit le PDF qu'il vient de produire et refuse
  un titre qui mord sur le pitch, un pitch qui mord sur les horaires, ou un
  texte trop près du bord (seuil calé sur la zone non imprimable d'un copieur,
  ~10 mm). Sur un tirage A3 en onze exemplaires, l'erreur se découvre au mur.

Il demande `python-pptx`, `pymupdf`, LibreOffice Impress et les polices Barlow
et Barlow Condensed. Le CI ne l'exécute pas.


## Affiche A3 de l'événement

`outils/affiches/generer-affiche-evenement.py` produit une affiche A3 paysage
d'accueil, en deux chartes à comparer, d'après le modèle Word de signalétique
du Business Center (`01. A3 TEMPLATE.docx`).

| Fichier | Charte |
|---|---|
| `affiche-evenement-caa.pdf` | celle du modèle : photo du lieu, panneau vert #00795C à 85 %, Century Gothic et Arial Black |
| `affiche-evenement-programme.pdf` | celle du programme : fond blanc, panneau #1A1A2E, monogramme, Barlow Condensed |

Les mesures viennent du modèle lui-même (page 42 × 29,7 cm, photo 44,4 × 29,6
débordante, panneau 36,3 × 24,2, corps 72 et 48 pt), pour que la comparaison
porte sur la charte et non sur la maquette.

Deux écarts assumés au modèle :

- **La flèche disparaît.** Elle fait du modèle une signalétique de couloir
  (« c'est par là »), pas une affiche d'accueil. Le QR prend sa place au
  centre : c'est lui qui, ici, envoie le lecteur quelque part.
- **Les logos du modèle disparaissent.** Ce sont ceux de Crédit Agricole
  Île-de-France et de Prestige Affaires — une autre entité, un autre
  événement. À leur place, en bas à gauche du panneau, le logo CA Assurances
  repris du modèle d'écrans du Business Center.

`ressources/business-center.jpg` est la photo extraite du modèle (2722 × 1815,
soit environ 155 ppp au format A3 : c'est la résolution du modèle d'origine,
pas une dégradation).


## Écrans du Business Center

`outils/affiches/generer-ecrans.py` produit la diapo 16:9 du programme de la
journée, en deux chartes, d'après le modèle d'écrans du Business Center
(`Templates A écrans BC VF.pptx`, 1280 × 720, panneau vert #006B4F à 85 %,
Poppins).

| Fichier | Charte |
|---|---|
| `ecran-programme-caa.pptx` | celle du modèle : Poppins, panneau vert |
| `ecran-programme-testing.pptx` | celle du programme : Barlow, panneau #1A1A2E, monogramme |

**Deux fichiers et non un deck de deux diapos** : ce sont des variantes d'une
même diapo, pas une séquence. Un écran qui boucle afficherait les deux.

L'agenda du modèle tient cinq lignes ; la journée en compte neuf, et
l'après-midi est un bloc de dix kiosques. D'où **deux colonnes** — la journée à
gauche, les dix kiosques en deux fois cinq à droite — et le détail (pitch,
salle, plan) derrière le QR : un écran de hall se lit en marchant.

Deux écarts assumés au modèle :

- **Les titres de conférence sont coupés à leur deux-points.** Le sous-titre
  fait vingt mots ; il est illisible depuis un hall et reste sur la page.
- **Les emojis du programme sautent.** Décoratifs à l'écran d'un téléphone,
  ils parasitent la charte sur un panneau vert et dépendent d'une police
  installée sur la machine qui diffuse.

Le contrôle après génération vérifie le format 16:9, que rien ne sorte du
panneau, **et que rien ne recouvre le bandeau de logos** — c'est ce dernier
point qui a rattrapé les kiosques 9 et 10 écrits par-dessus les logos.

Les logos CA Assurances, « Façonner demain ! » et Prestige Affaires viennent de
ce modèle. Celui de CA Assurances sert aussi aux affiches A3 de l'événement.


## Présentation de la journée

`outils/affiches/generer-presentation.py` produit
`presentation-testing-event.pptx` — quinze diapos 16:9 à la charte du
programme, texte natif et non captures d'écran : modifiable, cherchable, net à
la projection.

| | | |
|---|---|---|
| 1 Couverture | 6 Conférence 2 | 11 Le jeu : cinq fiches, une urne |
| 2 Gabarit | 7 Table ronde | 12 Le QR et ce qu'il ouvre |
| 3 Programme de la journée | 8 Pause déjeuner | 13 Clôture et remise des lots |
| 4 Ouverture | 9 L'après-midi, mode d'emploi | 14 Merci |
| 5 Conférence 1 | 10 Les dix kiosques | 15 Fin |

Contenus lus dans `index.html` : signature de l'événement, horaires, titres et
citations des trois séances, titres et pitchs des dix kiosques.

**Ce que le script ne sait pas.** Les noms — intervenant·es, animateur·rices,
staff, partenaires — et les trois lots ne figurent nulle part dans le dépôt.
Ils sont posés en rouge comme `[ à compléter ]` plutôt qu'inventés. La diapo 14
est un gabarit à remplir, pas une liste.

Le contrôle après génération vérifie les quinze diapos, le format 16:9, et
qu'aucun texte ne sorte de la zone utile ni ne passe sous le pied de page. Il
ne mesure pas la tenue du texte *dans sa carte* : trois débordements de ce type
ont été trouvés à l'œil sur le rendu (colonne du matin en diapo 3, pitchs en
diapo 10, étapes 2 et 4 en diapo 11) et corrigés par la géométrie.


## Diapo « le programme en main »

    python3 outils/affiches/generer-diapo-en-main.py

La diapo 12 de la présentation **dit** ce que le programme contient. Celle-ci
le **montre** : deux captures d'écran du téléphone — la salle qui s'allume sur
le plan, et le bouton « Repérer ». Elle se place après la diapo du QR code.

Deux mises en page sont produites, parce que la contrainte n'est pas la place
sur la diapo mais la lisibilité depuis le fond d'un auditorium de 254 places :

| Fichier | Contenu | Hauteur des captures |
|---|---|---|
| `diapo-en-main-1-diapo.pptx` | les deux captures côte à côte | 7,65 cm |
| `diapo-en-main-2-diapos.pptx` | une capture par diapo, cartouche à gauche | 10,5 cm |

**C'est la hauteur qui limite, pas la largeur.** Sous le titre il reste 10,5 cm.
À deux captures sur une diapo, chacune cède la place du cartouche ; à une
capture par diapo, le cartouche passe à gauche et la capture prend toute la
hauteur — un tiers de plus.

**Fichiers séparés plutôt qu'insertion dans le générateur de la présentation.**
La présentation est reprise à la main : régénérer les quinze diapos écraserait
ces reprises, et insérer une diapo décalerait la numérotation du pied de page.
Un fichier de une ou deux diapos s'importe dans une présentation déjà
travaillée sans rien perdre. C'est aussi pourquoi ces diapos ne portent pas de
numéro de page : leur pagination d'accueil n'est pas connue.

**Les captures sont recadrées, pas reprises telles quelles.** Sur la capture du
plan, les bandes sombres du fond assombri passeraient pour un défaut une fois
projetées : on ne garde que la carte de la modale. Sur la capture des kiosques,
deux cartes suffisent — une non repérée, une repérée, ce qui montre les deux
états côte à côte ; la troisième portait le bouton flottant du téléphone, qui
n'appartient pas à la page.

Le contrôle relit le PDF produit et refuse trois choses : un nombre de pages
inattendu, un format qui n'est pas du 16:9, et **tout texte qui passerait sous
une capture ou sur le pied de page**. Ce dernier point a été ajouté après coup :
la première version à une diapo avait une légende qui débordait sur deux
lignes, la seconde disparaissant derrière la capture voisine — visible à l'œil,
invisible pour un contrôle qui ne compare pas les encombrements.

Les captures sont figées dans `outils/affiches/ressources/`. Elles datent d'un
état de la page où les salles étaient déjà publiées : **si les affectations
changent, il faut refaire les captures**, relancer le script ne suffit pas.

## Écran complet de l'espace hospitalité

    python3 outils/affiches/generer-ecran-complet.py

Produit `ecran-programme-complet.pptx` : **tout le programme sur un seul
écran**, pour l'espace hospitalité. Ce n'est pas la diapo 3 en plus dense, c'est
un autre problème. La diapo 3 est projetée dans un auditorium et se lit depuis
le fond : peu de mots, gros. Cet écran est regardé à deux ou trois mètres par
quelqu'un qui passe, et il doit **se suffire à lui-même** — personne ne
s'arrêtera pour scanner un QR code.

D'où la densité assumée : les trois conférences avec leur accroche, les dix
kiosques avec leur phrase de présentation **et leur salle**. Ce sont les deux
informations qui manquaient à `generer-ecrans.py`, et sans lesquelles il faut
aller chercher ailleurs. Le QR code reste en bas de colonne, pour qui voudra la
version qui suit les changements de salle — mais l'écran ne repose pas dessus.

Les salles sont lues dans le bloc `salles-data` de la page, celui qu'on rouvre
le 14 au matin. Un kiosque sans salle publiée n'arrête rien : le script le
signale et écrit « Salle à confirmer », comme la page.

### Deux contrôles, et pourquoi il en fallait deux

Le premier compare chaque fragment de texte du PDF aux **cellules dessinées** :
rien ne doit sortir de sa case. Il fonctionne au fragment et non au bloc, parce
que l'extracteur regroupe volontiers deux textes distants posés sur la même
ligne de base — les deux intitulés de colonne arrivaient fusionnés en un pavé
large de 18 cm qui ne correspondait à rien.

Le second vérifie que **deux fragments ne se recouvrent jamais**. Il est
indépendant du premier, et c'est lui qui compte : un titre trop long qui vient
écrire par-dessus sa propre accroche reste à l'intérieur de sa cellule, donc
invisible pour le contrôle de débordement. C'est exactement ce qui est arrivé à
la conférence 2.

### Les cartes de séance se dimensionnent sur leur contenu

Le titre de la conférence 2 fait le double des autres. Les trois cartes mesurent
donc ce qu'il leur faut — nombre de lignes du titre et de l'accroche — puis se
partagent le reliquat, plutôt que d'être à hauteur fixe.

Le calcul du nombre de lignes a demandé deux corrections. La première version
tablait sur une hauteur de ligne devinée. La deuxième la calculait, mais oubliait
que **l'interligne donné en nombre à python-pptx multiplie la hauteur naturelle
de la police — environ 1,2 fois le corps — et non le corps lui-même** : chaque
ligne était sous-estimée d'un cinquième. Les deux fois, c'est le contrôle de
recouvrement qui l'a dit.

## Diapo 3 — le programme de la journée

La première version reprenait la page web presque à l'identique, les dix
kiosques compris : dense, et redondante avec la diapo 10 qui les détaille déjà.
La deuxième était lisible mais grise. La version actuelle garde la structure
aérée de la seconde et reprend **les couleurs de la page**, créneau par créneau :

| Moment | Pavé de l'heure | Fond du libellé |
|---|---|---|
| Accueil café, clôture | `#008080` | `#E0F7F7` |
| Mot d'ouverture, 13h40 | `#1A1A2E` | `#F0F0F8` |
| Cocktail | `#C01020` | `#FFF3E0`, texte `#8B4500` |
| Conférence 1 / 2 / table ronde | `#1A1A2E` | blanc, barre `#00B4B4` / `#ED1B2F` / `#9EBE38` |
| Bande des rotations | — | `#1A1A2E`, texte `#00B4B4` |
| Pastilles de rotation | — | `#D9EFEF`, filet `#008080` |

**C'est le couple pavé d'heure plein + fond teinté qui porte la couleur**, pas
un liseré de 2 mm : à la projection, un filet ne se voit pas depuis le fond de
la salle. Les trois couleurs de séance sont celles des badges de la page.

La colonne de l'après-midi ne liste pas les dix kiosques — c'est la diapo 10.
Elle porte le créneau de 13h40, la bande « 10 kiosques · 5 rotations », les cinq
pastilles horaires et la clôture. Les deux colonnes occupent 8,85 cm et
finissent à la même hauteur.

### Le programme avec les dix kiosques

    python3 outils/affiches/generer-presentation.py --variante programme-kiosques

Écrit `diapo-variante-programme-kiosques.pptx` : la même diapo 3, mais la
colonne de l'après-midi porte les dix kiosques au lieu des pastilles de
rotation. **Sans les pitchs** — dans 6,9 cm de large et 0,92 cm de haut ils
tomberaient sous 7 pt et ne se liraient plus. Le titre du kiosque suffit à
situer, le pitch reste sur la diapo 10.

La bande des rotations se réduit alors à une ligne, `14h00 – 16h30 · 5
rotations de 30 min · 10 kiosques en simultané`, pour libérer les cinq lignes
de kiosques.

### Diapo 10 — les dix kiosques

Les kiosques sont rangés **dans l'ordre de lecture**, impairs à gauche et pairs
à droite, et la couleur du numéro **alterne d'un kiosque au suivant** : c'est la
règle de la page (`nth-child(odd)` cyan, `nth-child(even)` rouge). La version
précédente mettait 1 à 5 à gauche, 6 à 10 à droite, et coloriait par colonne —
deux écarts avec le programme que les participants auront sous les yeux.

Le numéro est posé dans un pavé plein, pas signalé par un liseré, pour la même
raison que sur la diapo 3.

### Remplacer une seule diapo

    python3 outils/affiches/generer-presentation.py --diapo 3

Écrit `diapo-03-seule.pptx`, avec son numéro de page. La présentation est
reprise à la main (les noms, les lots) : quand une diapo change, on la remplace
dans le fichier déjà travaillé plutôt que de régénérer les quinze et d'écraser
les reprises.

### Ce que le contrôle refuse désormais

Le vérificateur ne regardait que le texte, et seulement celui qui *commençait*
au-dessus du pied de page. Deux angles morts, tous deux exploités par le premier
jet de cette diapo :

- une ligne entièrement enfoncée dans le pied n'était pas signalée ;
- **un pavé de couleur pouvait déborder sans aucun texte en cause** — le texte
  est centré dans la carte, c'est le bas de la carte qui mord.

Les deux sont contrôlés. Les fonds pleine page et la bande du pied elle-même
sont écartés, la couverture et la diapo de fin aussi, qui n'ont pas de pied.

## Animation de la page de garde

`outils/affiches/generer-animation.py` produit un balayage lumineux qui
traverse le logo : **2,6 s de mouvement, puis 27,4 s d'arrêt, en boucle**. Sur
trente secondes d'affichage il ne se passe quelque chose que pendant deux —
c'est la traduction de « en boucle, mais pas trop constant ».

| Fichier | Usage |
|---|---|
| `couverture-logo.gif` | le bloc du logo seul, posé sur la diapo 1 du PPTX |
| `couverture-testing-event.mp4` | la couverture entière en 1920 × 1080, pour un écran |

**Un GIF et non une vidéo dans le PPTX.** Un GIF animé boucle de lui-même :
rien à régler, donc rien qui puisse ne pas se déclencher. Une vidéo demande
« lecture automatique » et « en boucle jusqu'à l'arrêt », deux réglages qui
dépendent de la version de PowerPoint et de la machine. Le GIF ne couvre que le
bloc du logo : la signature, la date et le QR restent du texte natif.

La lumière est découpée sur l'alpha du logo — elle ne passe que sur les
lettres, jamais sur le fond marine, sinon le calque se verrait.

Le MP4 est composé à partir de la **page 1 du PDF de la présentation** : il
montre la diapo elle-même, pas une reconstitution qui pourrait en diverger.
D'où l'ordre d'exécution :

```
python3 outils/affiches/generer-animation.py     # le GIF
python3 outils/affiches/generer-presentation.py  # le deck, qui l'embarque
python3 outils/affiches/generer-animation.py     # le MP4, tiré du PDF produit
```

Le contrôle vérifie que la boucle est infinie, que le total fait bien trente
secondes et que la pause finale dure ce qu'elle doit durer. Il a servi dès le
premier essai : le codeur GIF fusionne les images de pause identiques, et la
durée totale tombait à côté.

**Non vérifié :** le rendu dans PowerPoint. Cet environnement n'a que
LibreOffice. Ce qui est mesuré, c'est le fichier — 20 images, boucle infinie,
30,0 s — et son intégration dans le `.pptx`.


## Page de garde animée par vidéo

`outils/affiches/generer-couverture-video.py` produit
`couverture-testing-event.pptx` — **une diapo**, celle de garde, où une vidéo
de dix secondes prend la place du logo, joue, puis reste vingt secondes sur sa
dernière image avant de recommencer. La présentation à quinze diapos garde, elle,
la version GIF.

Quatre choses sont refaites sur la source (`ressources/couverture-source.mov`),
et chacune évite une panne :

| | |
|---|---|
| **Conteneur** | HEVC/.mov → **H.264/.mp4**. PowerPoint lit le second sans extension de codec ; le premier n'est pas garanti sur un poste d'entreprise. |
| **Son** | La source porte une piste AAC. Une page de garde qui boucle avec du son toutes les trente secondes est intenable : la piste est retirée. |
| **Niveaux** | Source en `yuvj420p` (échelle pleine) : convertie sans précaution, noirs bouchés ou délavés selon le lecteur. La conversion est explicite. |
| **Bords** | Fondus vers l'encre de la charte. |

Le dernier point ne se voit qu'une fois la vidéo posée. Le fond de la source
est un marine proche du nôtre au centre, mais son canal bleu s'effondre sur les
bords gauche et droit — de 43 à 24, quand la charte est à 46. Posée telle
quelle, la vidéo dessinait un rectangle plus sombre au milieu de la page de
garde. Après fondu **et pré-compensation de l'échelle télé** (`#1D1C2F` pour
retomber sur `#1A1A2E` après codage), l'écart mesuré entre l'intérieur et
l'extérieur du cadre sur la diapo rendue est de **0**.

La pause de vingt secondes fige la dernière image : vingt secondes d'images
identiques ne coûtent presque rien au codeur. La source fait 5,1 Mo, la vidéo
de trente secondes 518 Ko.

**Non vérifié :** le déclenchement automatique et la répétition sont inscrits
dans le XML de la diapo, mais cet environnement n'a pas PowerPoint. Le réglage
manuel, s'il le fallait : onglet **Lecture** → *Démarrer : Automatiquement* et
*En boucle jusqu'à l'arrêt*. L'image d'affiche est la dernière image de la
vidéo : la diapo reste juste même si rien ne se lance.


## Qui anime — sur les cartes du programme

Les trois séances du matin portent leurs intervenants, les dix kiosques leurs
animateurs. La source des kiosques est `Liste_des_kiosques.xlsx`, colonne C ;
celle des conférences et de la table ronde est la liste transmise le 14/09, sans
document de référence. Trois partis pris :

- **L'entité avant les noms.** « Smartesting · Arnaud BOUZY » se lit dans cet
  ordre parce que l'entité situe le kiosque avant qu'on lise le nom : équipe
  interne, filiale, partenaire. C'est ce qui sert à choisir ; le nom sert à
  reconnaître un collègue, ce qui vient après.
- **Une ligne par entité.** Trois kiosques sont co-animés par deux structures
  (6, 8, 9) et le 8 réunit quatre personnes. Sur une seule ligne il aurait fallu
  inventer un séparateur qui tienne à 160 px de large ; empilées, les deux
  lignes se lisent sans ponctuation acrobatique.
- **Aucun verbe.** Ni « animé par », ni « présenté par ». Le kiosque 10 est en
  libre service : personne ne l'anime, Elena TOMAS en est le contact. Un verbe
  aurait contredit le pitch de la carte à trois lignes d'intervalle. Seule
  exception, la table ronde, où « Animée par Fabrice CHATRON » distingue le
  modérateur des trois intervenants — sans quoi la liste en compterait quatre.

**Le mode compact masque le « qui » avec le pitch**, pour la même raison : il
existe pour tenir les dix kiosques sur un écran quand on choisit ses cinq
rotations, et deux lignes de plus par carte le videraient de son sens.
**L'impression le rétablit**, comme le pitch — le papier n'a pas de mode
compact.

**La casse des noms de famille a été uniformisée en capitales**, la convention
du fichier source pour huit kiosques sur dix. C'est le seul écart : les lettres
sont celles du fichier, accents compris — donc aussi accents *absents*. Passer
« BEAUGE » en « Beauge » aurait affirmé une absence d'accent que rien ne
vérifie ; en capitales, l'ambiguïté reste visible et se corrige d'une ligne.

## Comportements de la page

**Le logo du bandeau porte un reflet**, sur un cycle 50/50 : 2,6 s de
passage, 2,6 s d'attente. Le mouvement dure le même temps que sur la page
de garde de la présentation, où il est suivi de 27,4 s d'arrêt ; sur la
page web l'attente vaut la durée du passage, et le logo est donc allumé la
moitié du temps. Il ne coûte
aucun octet d'image : la source du logo est déclarée une seule fois dans
`--te-logo`, sert de fond au bandeau **et** de masque au reflet. Écrite deux
fois, elle aurait ajouté 26 Ko à une page qui en fait 95.

**Une onde signale la salle sur le plan.** À l'ouverture de la modale, un
anneau turquoise part du contour de la salle, s'écarte et s'éteint, toutes les
1,5 s. Trois choix, chacun contraint par un constat plutôt que par le goût :

- **Une onde et non un reflet.** L'effet du bandeau ne se transpose pas : une
  bande qui met 2,6 s à traverser 240 px de logo traverse Sumida, large de
  40 px sur le plan, en moins d'une demi-seconde. Ce serait un clignotement.
- **Un cycle court.** La modale reste ouverte quelques secondes — on l'ouvre,
  on situe la salle, on ferme. Une animation dont le premier temps tombe à 2 s
  ne serait vue par personne.
- **Une distance de propagation constante, pas un pourcentage.** Un facteur
  d'agrandissement fixe donne une distance proportionnelle à la salle : mesuré
  sur Donau, 190 px de large, l'onde traversait Douro et Rhône avant de
  s'éteindre. Le facteur est donc calculé au tracé pour que l'onde parcoure
  toujours 16 unités de plan, quelle que soit la salle.

L'onde passe sous l'anneau et ne revient jamais sur la salle elle-même :
vérifié dans Chromium à sept instants du cycle, la zone de la salle est
strictement identique d'un instant à l'autre. Elle disparaît sous
`prefers-reduced-motion` et à l'impression.

Trois précautions, chacune vérifiée dans le navigateur :

- **Le masque, sinon rien.** Sans masquage, la bande claire barrerait tout le
  bandeau. Le bloc est donc sous `@supports` : là où le masquage n'existe pas,
  il n'y a pas de reflet du tout.
- **L'image de repos est le logo nu.** C'est elle qu'on voit 27,4 s sur 30.
  Régler la position de repos du dégradé ne suffisait pas — il est incliné, son
  emprise dépasse ce que les pourcentages laissent prévoir, et il restait un
  voile sur le monogramme. Le reflet est donc éteint par `opacity` hors de son
  passage. Mesuré : à 10 s et à 29 s, la capture est **strictement identique**
  à celle du logo sans reflet.
- **`prefers-reduced-motion`** éteint l'animation, et l'impression aussi.

Tout est facultatif : **sans JavaScript, le programme reste complet et juste.**
Seuls la bascule, la sélection personnelle et le repère « en ce moment »
n'apparaissent pas ; les cartes, elles, portent leur salle dans le HTML.

- **Repère « en ce moment ».** Le créneau en cours reçoit un contour et une
  étiquette. Aucune couleur ni mise en forme de bloc n'est modifiée. L'heure est
  celle de **Paris**, pas celle de l'appareil : un téléphone réglé sur un autre
  fuseau afficherait le mauvais créneau. Le repère ne s'active **que le
  14 septembre 2026** — les autres jours, la page est strictement celle qui a
  été communiquée. Les horaires vivent dans le markup (`data-debut` /
  `data-fin`, en minutes) et la porte qualité vérifie qu'ils sont croissants et
  sans chevauchement.
- **Bascule compact / détaillé.** Replie les descriptions des kiosques : la
  section après-midi passe de 3 719 à 2 909 px, soit 22 % de moins. Le choix
  est retenu d'une visite à l'autre.
- **Sélection personnelle (jusqu'à 5 kiosques).** Une étoile par carte marque
  les kiosques qu'on veut faire. Le plafond n'est pas un réglage d'affichage :
  **10 kiosques en simultané, 5 rotations identiques**, donc cinq kiosques par
  participant. Au sixième clic la page refuse et le dit, plutôt que de laisser
  constituer une liste qu'aucun après-midi ne permet. La porte qualité vérifie
  que le plafond du script et le nombre de rotations du markup restent égaux.

  La sélection est rangée sous le **numéro** de kiosque, jamais sous la salle ni
  la position dans la grille : les salles sont saisies le jour J, les numéros
  non. Une publication en cours de journée laisse donc la sélection intacte.

  Elle vit dans le `localStorage` de l'appareil, **pas dans un cookie** : un
  cookie partirait avec chaque requête vers le Worker, alors que rien ici n'a à
  quitter le téléphone. Conséquences à assumer : la sélection est **propre à un
  navigateur** — le QR scanné ouvre souvent un navigateur intégré, et rouvrir
  l'URL dans Safari repart de zéro — et elle disparaît en navigation privée. La
  page le dit sous le compteur.

  **Ce n'est pas une réservation.** Aucune place n'est décomptée, l'organisation
  ne lit pas ces sélections, et l'accès aux salles se fait sur place. Le libellé
  affiché ne dit jamais autre chose.

  Côté droit : l'article 82 de la loi 78-17 vise les lectures et écritures dans
  le terminal, cookie ou non. Les lignes directrices de la CNIL exemptent de
  consentement les traceurs de personnalisation de l'interface quand celle-ci
  est un élément intrinsèque et attendu du service — ce qui est le cas d'une
  sélection déclenchée par l'utilisateur lui-même. Pas de bandeau de
  consentement. Référence : [délibération n° 2020-091 du 17 septembre
  2020](https://www.legifrance.gouv.fr/cnil/id/CNILTEXT000042398005).
- **Plan de localisation.** Quand la salle saisie est reconnue, la pastille de
  salle devient une commande — un chevron l'indique — et ouvre le plan du
  rez-de-jardin avec cette salle mise en évidence.

  Le nom de la salle, lui, reste affiché en clair : c'est la réponse à « je
  vais où », elle se lit en marchant. Le plan est une aide de second rang, pour
  qui ne connaît pas le bâtiment — d'où le clic, qui aurait été un contresens
  sur le nom.

  L'image n'est téléchargée qu'à la première ouverture : personne ne paie
  27 Ko pour une aide qu'il n'ouvrira pas. La modale est un `<dialog>` natif —
  mise en retrait de l'arrière-plan, piège de focus, fermeture par Échap et
  fond assombri sont fournis par le navigateur plutôt que réimplémentés. Sans
  `showModal`, rien n'est activé : la pastille reste inerte.

  À 390 px de large, le nom gravé sur le plan fait 5 px de haut, et un plan est
  de toute façon muet pour un lecteur d'écran. **La position est donc aussi
  donnée en toutes lettres** sous l'image (« au centre-bas du plan, à droite de
  Douro, au-dessus de la salle Donau »), et la porte qualité refuse une salle
  sans cette description.

  La saisie du 14 reste du texte libre : elle est normalisée (minuscules,
  accents retirés) puis cherchée dans les dix noms connus, donc « Salle Rhône
  (RDJ) » trouve Rhône. Aucun des dix noms n'étant contenu dans un autre, la
  recherche ne peut pas se tromper de salle — la porte qualité le vérifie. Si
  rien ne correspond, la valeur reste affichée telle quelle, simplement sans
  plan : aucune saisie ne peut casser la page.
- **Titres de section collants.** Le titre de la demi-journée reste visible
  pendant qu'on parcourt sa section. Le décalage tient compte du bandeau
  d'environnement, mesuré et non codé en dur — il vaut zéro en production.

### Rafraîchissement automatique

Le problème que cela règle : un téléphone qui a ouvert la page à 9h05 et l'a
laissée dans un onglet continue d'afficher les salles de ce moment-là, même si
elles ont changé à 11h. **Les en-têtes HTTP ne peuvent rien pour un document
déjà rendu** — `Cache-Control` n'agit qu'au chargement suivant.

La page se ré-interroge donc elle-même, au retour sur l'onglet, à la reprise du
focus, et toutes les cinq minutes si elle reste visible. Quand la version
publiée diffère de celle affichée, **les salles sont mises à jour sur place,
sans rechargement**, et un avis discret propose — sans l'imposer — de recharger
pour le reste. Personne n'aime voir sa page sauter en pleine lecture.

La requête est conditionnelle (`cache: 'no-cache'`) : tant que rien n'a été
republié, le serveur répond **304** et il ne passe presque rien sur le réseau.
Un corps complet n'est téléchargé que lorsque la version a réellement changé.

Ce mécanisme **ne porte jamais l'affichage initial** : les salles sont dans le
HTML dès le premier octet. Si le réseau tombe — portail captif du wifi invité,
sous-sol —, la page reste celle qui a été chargée et le participant garde une
information juste, seulement plus ancienne. C'est la différence avec un service
worker, qui servirait activement une copie périmée.

## Accessibilité

Deux défauts structurels ont été corrigés, sans qu'un pixel bouge :

- **Le `h1` était le slogan de l'événement**, pas le sujet de la page. Le thème
  est redevenu un paragraphe ; un titre réel, lisible par les lecteurs d'écran
  sans occuper de place, nomme le document.
- **Aucun des 13 contenus n'était un titre.** Les 3 conférences et les
  10 kiosques sont désormais des `h3` dans des `article`, à l'intérieur de
  `section` par demi-journée. La page passe de **3 à 17 titres navigables** :
  un lecteur d'écran saute de l'un à l'autre au lieu de tout lire en linéaire.

S'y ajoutent un lien d'évitement, des repères de focus visibles, et
`aria-hidden` sur les emoji et les ★ décoratifs — sans quoi la synthèse vocale
annonce « dé à jouer Ludopédagogie ».

Les teintes vives de la charte ne portent pas de texte : blanc sur `#00B4B4`
donne 2,56:1 et blanc sur `#ED1B2F` 4,38:1, tous deux sous le seuil WCAG AA de
4,5:1. Des variantes foncées (`#008080`, `#006A6A`, `#C01020`) les remplacent
partout où du texte est posé, entre 4,77:1 et 8,16:1.

### Choix structurants

- **Page autonome.** Aucune ressource distante : polices auto-hébergées, logo
  en ligne. Le wifi invité d'un centre d'affaires peut passer par un portail
  captif, et cela évite aussi de transmettre l'IP des visiteurs à un tiers.
- **Salles affichées directement sur la carte**, pas derrière une fenêtre à
  ouvrir. C'est l'information qu'on consulte debout, en marchant, entre deux
  rotations : la cacher derrière une interaction serait un contresens.
- **Bloc de données en tête de fichier** plutôt que dans un fichier séparé
  chargé au vol : un seul fichier, donc pas de désynchronisation possible entre
  la page en cache et des données plus récentes, et aucune requête réseau
  supplémentaire.
- **Pas de TypeScript, ni lint, ni audit de dépendances.** La page servie n'a
  aucune dépendance d'exécution ; ces contrôles ne vérifieraient rien. Le dépôt
  a en revanche deux dépendances de développement, `wrangler` et `qrcode` : les
  jobs qui exécutent les tests font donc `npm ci`. Seul le contrôle du bloc des
  salles s'en passe, pour rester immédiat le 14 au matin.
- **Pas de porte `changelog.json`.** Une version à incrémenter à la main
  obligerait à éditer un second fichier depuis un téléphone, sous pression — la
  porte deviendrait le principal mode de défaillance. La version est injectée
  automatiquement à la place.

---

## Branches et déploiement

| Branche | Worker         | Usage                                  |
|---------|----------------|----------------------------------------|
| `dev`   | `info-hub-dev` | Relecture avant mise en ligne          |
| `prod`  | `info-hub`     | **URL du QR code imprimé**             |

Déploiement par GitHub Actions et `wrangler` (pas par Workers Builds), pour
rester aligné sur les autres dépôts.

Chaque déploiement enchaîne : porte qualité → injection de version →
`wrangler deploy` → **contrôle après déploiement**. Ce dernier interroge l'URL
publiée et compare le bloc des salles qu'elle sert à celui du dépôt. Il ferme le
scénario redouté : déploiement au vert, mais URL servant encore l'affectation
de la veille.

La propagation Cloudflare n'étant pas instantanée, l'URL répond 200 en servant
encore la version précédente pendant quelques secondes. Le contrôle réessaie
donc **jusqu'à ce que la page servie corresponde**, huit fois à cinq secondes
d'intervalle — et non jusqu'à ce qu'elle réponde, ce qui produisait un rouge
au bout d'une seconde sur un déploiement parfaitement sain.

### Prérequis à configurer une seule fois

Secrets du dépôt (*Settings → Secrets and variables → Actions*) :

- `CLOUDFLARE_API_TOKEN` — portée **Workers Scripts: Edit**
- `CLOUDFLARE_ACCOUNT_ID`

Tant qu'ils sont absents, la porte qualité passe mais le déploiement échoue.

### En local

```bash
npm run quality   # porte qualité + tests
npm run deploy    # déploiement manuel (nécessite les identifiants Cloudflare)
```

---

## Licences tierces

Polices **Barlow** et **Barlow Condensed** — SIL Open Font License 1.1,
Copyright 2017 The Barlow Project Authors (<https://github.com/jpt/barlow>).
Texte de la licence : `worker/public/assets/fonts/OFL.txt`.
