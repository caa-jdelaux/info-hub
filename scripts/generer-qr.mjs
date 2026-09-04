/**
 * Génère le QR code de l'URL de production, monogramme « TE » au centre.
 *
 * Le logo recouvre des modules du code : c'est la correction d'erreur qui
 * absorbe la perte. Le niveau H tolère environ 30 % de perte, mais cette marge
 * sert aussi aux salissures, aux plis et aux mauvais éclairages d'un hall
 * d'accueil. La plaque centrale est donc dimensionnée très en deçà, et sa
 * surface est vérifiée par les tests.
 *
 * Sortie en SVG (le QR reste vectoriel, donc net à toute taille d'impression)
 * et en PNG haute définition pour les supports qui ne prennent pas le vectoriel.
 */

import QRCode from 'qrcode';

/**
 * Largeur du logo, en fraction du côté du code (hors marge).
 *
 * Valeur réglée par la mesure, pas à l'estime : en balayant les tailles et en
 * redécodant chaque rendu, le code passe encore à 21,0 % de surface recouverte
 * et casse à 25,3 %. Ces chiffres valent en conditions idéales — rendu
 * parfait, sans grain, sans angle, sans pli. Un appareil photo sur du papier
 * imprimé dispose de bien moins de marge, d'où le facteur deux conservé.
 */
export const FRACTION_LOGO = 0.36;

/** Blanc conservé autour du logo, en modules. */
export const RESPIRATION_MODULES = 1;

/** Plafond de surface recouverte. Point de rupture mesuré : 25,3 %. */
export const SURFACE_MAX = 0.15;

/** Marge silencieuse, en modules. En deçà de 4, des lecteurs échouent. */
export const MARGE_MODULES = 4;

export const COULEUR_MODULES = '#1A1A2E';

/**
 * @param {string} url
 * @param {string} logoDataUri Monogramme, en data URI.
 * @param {{largeur: number, hauteur: number}} logoTaille Dimensions natives,
 *   pour conserver les proportions dans la plaque.
 * @param {{fractionLogo?: number}} [options] Permet de balayer des tailles
 *   candidates lors du réglage ; la valeur retenue est FRACTION_LOGO.
 * @returns {{svg: string, surfaceRecouverte: number, modules: number}}
 */
export function genererSvg(url, logoDataUri, logoTaille, options = {}) {
  const fractionLogo = options.fractionLogo ?? FRACTION_LOGO;
  const code = QRCode.create(url, { errorCorrectionLevel: 'H' });
  const n = code.modules.size;
  const bits = code.modules.data;
  const total = n + MARGE_MODULES * 2;

  // La plaque épouse le format du logo au lieu d'être carrée. Un monogramme
  // en 1,5:1 posé sur une plaque carrée laisse du blanc perdu en haut et en
  // bas, et ce blanc recouvre des modules sans rien afficher : à surface
  // égale, une plaque au bon format donne un logo plus grand.
  const ratio = logoTaille.largeur / logoTaille.hauteur;

  // Alignement sur la grille : la plaque recouvre des modules entiers, ce qui
  // évite les demi-modules ambigus sur ses bords. La parité est calée sur
  // celle du code pour que le centrage tombe juste.
  const surGrille = (valeur) => {
    let entier = Math.ceil(valeur);
    if ((n - entier) % 2 !== 0) entier += 1;
    return entier;
  };

  const plaqueL = surGrille(n * fractionLogo + 2 * RESPIRATION_MODULES);
  const plaqueH = surGrille(n * fractionLogo / ratio + 2 * RESPIRATION_MODULES);
  const debutX = (n - plaqueL) / 2;
  const debutY = (n - plaqueH) / 2;

  const carres = [];
  for (let y = 0; y < n; y += 1) {
    for (let x = 0; x < n; x += 1) {
      if (!bits[y * n + x]) continue;
      // Inutile de dessiner ce que la plaque recouvre.
      const sousPlaque =
        x >= debutX && x < debutX + plaqueL &&
        y >= debutY && y < debutY + plaqueH;
      if (sousPlaque) continue;
      carres.push(`M${x + MARGE_MODULES} ${y + MARGE_MODULES}h1v1h-1z`);
    }
  }

  // Le logo remplit la plaque moins la respiration, en conservant ses
  // proportions : il touche donc les deux bords de la dimension contraignante.
  const dispoL = plaqueL - 2 * RESPIRATION_MODULES;
  const dispoH = plaqueH - 2 * RESPIRATION_MODULES;
  const echelle = Math.min(dispoL / ratio, dispoH);
  const logoL = echelle * ratio;
  const logoH = echelle;

  const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     viewBox="0 0 ${total} ${total}" width="1024" height="1024"
     shape-rendering="crispEdges" role="img"
     aria-label="QR code vers le programme du Testing Event 2026">
  <rect width="${total}" height="${total}" fill="#FFFFFF"/>
  <path d="${carres.join('')}" fill="${COULEUR_MODULES}"/>
  <rect x="${MARGE_MODULES + debutX}" y="${MARGE_MODULES + debutY}"
        width="${plaqueL}" height="${plaqueH}" rx="${Math.min(plaqueL, plaqueH) * 0.16}"
        fill="#FFFFFF"/>
  <image xlink:href="${logoDataUri}"
         x="${MARGE_MODULES + debutX + (plaqueL - logoL) / 2}"
         y="${MARGE_MODULES + debutY + (plaqueH - logoH) / 2}"
         width="${logoL}" height="${logoH}"
         preserveAspectRatio="xMidYMid meet"/>
</svg>
`;

  return {
    svg,
    surfaceRecouverte: (plaqueL * plaqueH) / (n * n),
    modules: n,
    plaque: { largeur: plaqueL, hauteur: plaqueH },
    logo: { largeur: logoL, hauteur: logoH },
  };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const { readFileSync, writeFileSync } = await import('node:fs');
  const [url, cheminLogo, sortie] = process.argv.slice(2);
  if (!url || !cheminLogo || !sortie) {
    console.error('usage : node scripts/generer-qr.mjs <url> <logo.png> <sortie.svg>');
    process.exit(2);
  }

  const png = readFileSync(cheminLogo);
  const taille = { largeur: png.readUInt32BE(16), hauteur: png.readUInt32BE(20) };
  const dataUri = `data:image/png;base64,${png.toString('base64')}`;

  const { svg, surfaceRecouverte, modules } = genererSvg(url, dataUri, taille);

  if (surfaceRecouverte > SURFACE_MAX) {
    console.error(
      `::error::Plaque centrale trop grande : ${(surfaceRecouverte * 100).toFixed(1)} % ` +
        `de la surface, plafond ${(SURFACE_MAX * 100).toFixed(0)} %.`,
    );
    process.exit(1);
  }

  writeFileSync(sortie, svg);
  console.log(
    `✓ ${sortie} — ${modules}×${modules} modules, niveau H, ` +
      `plaque centrale ${(surfaceRecouverte * 100).toFixed(1)} % de la surface.`,
  );
  console.log(`  URL encodée : ${url}`);
}
