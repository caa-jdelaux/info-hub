/**
 * Remplace au déploiement les deux marqueurs du pied de page : la version et
 * l'environnement.
 *
 * Rien n'est saisi à la main : le matin du 14, la seule édition doit être celle
 * du bloc des salles. La ligne obtenue répond en une seconde à la question
 * « est-ce que je regarde ma version, ou une copie en cache ? », et la puce
 * d'environnement à « est-ce que je regarde la relecture, ou la production ? ».
 */

export const MARQUEUR_VERSION = '__VERSION__';
export const MARQUEUR_ENV = '__ENV__';

/**
 * Échappe le texte destiné à être inséré dans du HTML.
 *
 * Les guillemets aussi : l'environnement atterrit dans l'attribut `data-env`
 * de la racine du document, où un guillemet non échappé refermerait
 * l'attribut.
 */
function echapper(texte) {
  return texte
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * @param {string} html Contenu de la page.
 * @param {string} version Libellé à afficher (date, heure, révision courte).
 * @param {string} [environnement] Puce affichée hors production ; chaîne vide
 *   en production, où la puce disparaît alors d'elle-même (`:empty` en CSS).
 * @returns {string} Page avec les marqueurs remplacés.
 * @throws {Error} Si un marqueur est absent — un remplacement silencieusement
 *   sans effet laisserait « __VERSION__ » visible en production.
 */
export function injecterVersion(html, version, environnement = '') {
  for (const marqueur of [MARQUEUR_VERSION, MARQUEUR_ENV]) {
    if (!html.includes(marqueur)) {
      throw new Error(`Marqueur ${marqueur} introuvable dans la page.`);
    }
  }
  if (typeof version !== 'string' || version.trim() === '') {
    throw new Error('Version vide.');
  }
  if (typeof environnement !== 'string') {
    throw new Error("Environnement : une chaîne est attendue (vide en production).");
  }

  return html
    .split(MARQUEUR_VERSION)
    .join(echapper(version))
    .split(MARQUEUR_ENV)
    .join(echapper(environnement));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const { readFileSync, writeFileSync } = await import('node:fs');
  const [chemin, version, environnement = ''] = process.argv.slice(2);
  if (!chemin || !version) {
    console.error(
      'usage : node scripts/inject-version.mjs <chemin> <version> [environnement]',
    );
    process.exit(2);
  }
  writeFileSync(
    chemin,
    injecterVersion(readFileSync(chemin, 'utf8'), version, environnement),
  );
  console.log(
    `version injectée dans ${chemin} : ` +
      `${environnement ? `[${environnement}] ` : ''}${version}`,
  );
}
