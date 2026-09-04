/**
 * Remplace le marqueur __VERSION__ du pied de page au moment du déploiement.
 *
 * La version n'est pas saisie à la main : le matin du 14, la seule édition doit
 * être celle du bloc des salles. Elle sert à répondre en une seconde à la
 * question « est-ce que je regarde ma version, ou une copie en cache ? ».
 */

export const MARQUEUR = '__VERSION__';

/**
 * @param {string} html Contenu de la page.
 * @param {string} version Libellé à afficher.
 * @returns {string} Page avec la version injectée.
 * @throws {Error} Si le marqueur est absent — un remplacement silencieusement
 *   sans effet laisserait « __VERSION__ » visible en production.
 */
export function injecterVersion(html, version) {
  if (!html.includes(MARQUEUR)) {
    throw new Error(`Marqueur ${MARQUEUR} introuvable dans la page.`);
  }
  if (typeof version !== 'string' || version.trim() === '') {
    throw new Error('Version vide.');
  }
  const echappee = version
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  return html.split(MARQUEUR).join(echappee);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const { readFileSync, writeFileSync } = await import('node:fs');
  const [chemin, version] = process.argv.slice(2);
  if (!chemin || !version) {
    console.error('usage : node scripts/inject-version.mjs <chemin> <version>');
    process.exit(2);
  }
  writeFileSync(chemin, injecterVersion(readFileSync(chemin, 'utf8'), version));
  console.log(`version injectée dans ${chemin} : ${version}`);
}
