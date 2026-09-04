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

## Accessibilité

Les teintes vives de la charte ne portent plus de texte : blanc sur `#00B4B4`
donne 2,56:1 et blanc sur `#ED1B2F` 4,38:1, tous deux sous le seuil WCAG AA de
4,5:1. Des variantes foncées (`#008080`, `#006A6A`, `#C01020`) les remplacent
partout où du texte est posé, entre 4,77:1 et 8,16:1. Les teintes d'origine
restent employées comme accents décoratifs et sur fond sombre, où le rapport est
largement suffisant.

Rapports calculés selon la formule de luminance relative WCAG 2.1, vérifiables
avec n'importe quel contrôleur de contraste.

---

## Licences tierces

Polices **Barlow** et **Barlow Condensed** — SIL Open Font License 1.1,
Copyright 2017 The Barlow Project Authors (<https://github.com/jpt/barlow>).
Texte de la licence : `worker/public/assets/fonts/OFL.txt`.
