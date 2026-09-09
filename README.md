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


## Comportements de la page

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
