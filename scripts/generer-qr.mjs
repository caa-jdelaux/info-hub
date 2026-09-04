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

/** Côté de la plaque centrale, en fraction du côté du code (hors marge). */
export const FRACTION_PLAQUE = 0.24;

/** Plafond de surface recouverte, très en deçà des ~30 % du niveau H. */
export const SURFACE_MAX = 0.08;

/** Marge silencieuse, en modules. En deçà de 4, des lecteurs échouent. */
export const MARGE_MODULES = 4;

export const COULEUR_MODULES = '#1A1A2E';

/**
 * @param {string} url
 * @param {string} logoDataUri Monogramme, en data URI.
 * @param {{largeur: number, hauteur: number}} logoTaille Dimensions natives,
 *   pour conserver les proportions dans la plaque.
 * @returns {{svg: string, surfaceRecouverte: number, modules: number}}
 */
export function genererSvg(url, logoDataUri, logoTaille) {
  const code = QRCode.create(url, { errorCorrectionLevel: 'H' });
  const n = code.modules.size;
  const bits = code.modules.data;
  const total = n + MARGE_MODULES * 2;

  // La plaque est alignée sur la grille : elle recouvre des modules entiers,
  // ce qui évite les demi-modules ambigus sur les bords.
  let cotePlaque = Math.round(n * FRACTION_PLAQUE);
  if ((n - cotePlaque) % 2 !== 0) cotePlaque += 1; // centrage exact
  const debutPlaque = (n - cotePlaque) / 2;

  const carres = [];
  for (let y = 0; y < n; y += 1) {
    for (let x = 0; x < n; x += 1) {
      if (!bits[y * n + x]) continue;
      // Inutile de dessiner ce que la plaque recouvre.
      const sousPlaque =
        x >= debutPlaque && x < debutPlaque + cotePlaque &&
        y >= debutPlaque && y < debutPlaque + cotePlaque;
      if (sousPlaque) continue;
      carres.push(`M${x + MARGE_MODULES} ${y + MARGE_MODULES}h1v1h-1z`);
    }
  }

  // Le logo occupe la plaque en conservant ses proportions, avec une respiration.
  const respiration = cotePlaque * 0.14;
  const dispo = cotePlaque - respiration * 2;
  const ratio = logoTaille.largeur / logoTaille.hauteur;
  const logoL = ratio >= 1 ? dispo : dispo * ratio;
  const logoH = ratio >= 1 ? dispo / ratio : dispo;

  const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     viewBox="0 0 ${total} ${total}" width="1024" height="1024"
     shape-rendering="crispEdges" role="img"
     aria-label="QR code vers le programme du Testing Event 2026">
  <rect width="${total}" height="${total}" fill="#FFFFFF"/>
  <path d="${carres.join('')}" fill="${COULEUR_MODULES}"/>
  <rect x="${MARGE_MODULES + debutPlaque}" y="${MARGE_MODULES + debutPlaque}"
        width="${cotePlaque}" height="${cotePlaque}" rx="${cotePlaque * 0.12}"
        fill="#FFFFFF"/>
  <image xlink:href="${logoDataUri}"
         x="${MARGE_MODULES + debutPlaque + (cotePlaque - logoL) / 2}"
         y="${MARGE_MODULES + debutPlaque + (cotePlaque - logoH) / 2}"
         width="${logoL}" height="${logoH}"
         preserveAspectRatio="xMidYMid meet"/>
</svg>
`;

  return {
    svg,
    surfaceRecouverte: (cotePlaque * cotePlaque) / (n * n),
    modules: n,
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
