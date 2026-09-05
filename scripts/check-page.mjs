/**
 * Porte qualité de la page programme.
 *
 * Les contrôles portent sur ce qui peut réellement casser ici : le bloc de
 * données édité à la main le jour J, la correspondance entre ce bloc et les
 * cartes, et l'autonomie réseau de la page. Un typecheck ou une suite de tests
 * unitaires n'auraient rien à vérifier sur un fichier statique sans dépendance.
 *
 * Le script décide, le workflow exécute : toute la logique est ici, et elle est
 * testée dans check-page.test.mjs.
 */

export const NOMBRE_DE_KIOSQUES = 10;

/** Blocs horodatés : 5 créneaux simples, 3 conférences, 5 rotations. */
export const NOMBRE_DE_CRENEAUX = 13;

/** Rotations de l'après-midi. Un participant fait un kiosque par rotation. */
export const NOMBRE_DE_ROTATIONS = 5;

/**
 * @param {string} html Contenu de la page.
 * @returns {string[]} Liste des anomalies. Vide si la page est conforme.
 */
export function verifierPage(html) {
  const anomalies = [];

  // ── Bloc de données ──────────────────────────────────────────────────
  const bloc = html.match(
    /<script[^>]*id=["']salles-data["'][^>]*>([\s\S]*?)<\/script>/,
  );
  if (!bloc) {
    anomalies.push('Bloc de données « salles-data » introuvable.');
    return anomalies; // Sans lui, les contrôles suivants n'ont plus de sens.
  }

  let salles;
  try {
    salles = JSON.parse(bloc[1]);
  } catch (erreur) {
    anomalies.push(`Bloc « salles-data » : JSON invalide — ${erreur.message}`);
    return anomalies;
  }

  if (salles === null || typeof salles !== 'object' || Array.isArray(salles)) {
    anomalies.push('Bloc « salles-data » : un objet est attendu.');
    return anomalies;
  }

  const attendues = Array.from({ length: NOMBRE_DE_KIOSQUES }, (_, i) => String(i + 1));
  const fournies = Object.keys(salles);

  for (const clef of attendues) {
    if (!fournies.includes(clef)) {
      anomalies.push(`Bloc « salles-data » : kiosque ${clef} absent.`);
    }
  }
  for (const clef of fournies) {
    if (!attendues.includes(clef)) {
      anomalies.push(`Bloc « salles-data » : clef inattendue « ${clef} ».`);
    }
  }
  for (const [clef, valeur] of Object.entries(salles)) {
    if (typeof valeur !== 'string') {
      anomalies.push(
        `Bloc « salles-data » : kiosque ${clef} — une chaîne est attendue, ` +
          `reçu ${typeof valeur}. Les guillemets ont probablement sauté.`,
      );
    }
  }

  // ── Cartes kiosques ──────────────────────────────────────────────────
  // Indépendant de la balise : les cartes sont des <article> depuis le passage
  // à une structure sémantique, et ce contrôle ne doit pas casser au prochain
  // changement de ce genre.
  const cartes = [...html.matchAll(/<\w+ class="kiosque-card" data-kiosque="(\d+)">/g)];
  if (cartes.length !== NOMBRE_DE_KIOSQUES) {
    anomalies.push(
      `${cartes.length} carte(s) kiosque trouvée(s), ${NOMBRE_DE_KIOSQUES} attendue(s).`,
    );
  }
  for (const [, numero] of cartes) {
    if (!Object.hasOwn(salles, numero)) {
      anomalies.push(`Carte du kiosque ${numero} sans entrée dans le bloc de données.`);
    }
  }

  // Chaque carte doit porter son emplacement de salle. Un comptage global de
  // « data-salle » ne conviendrait pas : le script de bas de page emploie le
  // même nom comme sélecteur. On borne donc chaque carte au début de la
  // suivante, et la dernière à la fin de la grille.
  const finDeGrille = html.indexOf(
    '<div class="special-slot"',
    cartes.length > 0 ? cartes[cartes.length - 1].index : 0,
  );
  for (let i = 0; i < cartes.length; i += 1) {
    const debut = cartes[i].index;
    const fin =
      i + 1 < cartes.length
        ? cartes[i + 1].index
        : finDeGrille === -1
          ? html.length
          : finDeGrille;
    if (!/data-salle/.test(html.slice(debut, fin))) {
      anomalies.push(`Carte du kiosque ${cartes[i][1]} sans emplacement « data-salle ».`);
    }
  }

  // ── Horaires exploitables ────────────────────────────────────────────
  // Le repère « en ce moment » lit ces bornes. Une valeur incohérente ne se
  // verrait qu'un seul jour, le 14, et seulement pendant le créneau concerné.
  const creneaux = [...html.matchAll(/data-debut="(\d+)"\s+data-fin="(\d+)"/g)];
  if (creneaux.length !== NOMBRE_DE_CRENEAUX) {
    anomalies.push(
      `${creneaux.length} créneau(x) horodaté(s), ${NOMBRE_DE_CRENEAUX} attendu(s).`,
    );
  }
  let precedent = null;
  for (const [, debut, fin] of creneaux) {
    const d = Number(debut);
    const f = Number(fin);
    if (f <= d) {
      anomalies.push(`Créneau ${d}–${f} : la fin ne suit pas le début.`);
    }
    if (d < 0 || f > 24 * 60) {
      anomalies.push(`Créneau ${d}–${f} : hors d'une journée.`);
    }
    // Les créneaux se suivent dans l'ordre du document. Un chevauchement
    // ferait clignoter deux repères « en ce moment » en même temps.
    if (precedent !== null && d < precedent) {
      anomalies.push(`Créneau ${d}–${f} : chevauche ou précède le créneau précédent.`);
    }
    precedent = f;
  }

  // ── Plafond de sélection ─────────────────────────────────────────────
  // Le plafond n'est pas un réglage d'affichage : il vaut le nombre de
  // rotations, puisqu'un participant fait un kiosque par rotation. Ajouter
  // une rotation sans relever le plafond passerait inaperçu jusqu'au jour J.
  const rotations = [...html.matchAll(/class="rotation-slot"/g)].length;
  if (rotations !== NOMBRE_DE_ROTATIONS) {
    anomalies.push(
      `${rotations} rotation(s) trouvée(s), ${NOMBRE_DE_ROTATIONS} attendue(s).`,
    );
  }
  const plafond = html.match(/var MAX_SELECTION = (\d+);/);
  if (!plafond) {
    anomalies.push('Plafond de sélection « MAX_SELECTION » introuvable.');
  } else if (Number(plafond[1]) !== rotations) {
    anomalies.push(
      `Plafond de sélection à ${plafond[1]} pour ${rotations} rotation(s) : ` +
        `un participant fait un kiosque par rotation.`,
    );
  }

  // ── Autonomie réseau ─────────────────────────────────────────────────
  // Le wifi invité d'un centre d'affaires peut passer par un portail captif.
  // Une seule ressource distante suffit à dégrader la page sur place, et
  // l'oubli ne se voit pas depuis un poste connecté.
  const distantes = [
    ...html.matchAll(/(?:src|href)=["'](https?:\/\/[^"']+)["']/g),
    ...html.matchAll(/url\(\s*["']?(https?:\/\/[^)"']+)/g),
  ].map((m) => m[1]);
  for (const url of distantes) {
    anomalies.push(`Ressource distante : ${url} — la page doit être autonome.`);
  }

  // ── Marqueur de version ──────────────────────────────────────────────
  // Il est remplacé au déploiement. S'il manque dans le dépôt, c'est qu'un
  // fichier déjà injecté a été committé : la page figerait alors une version
  // périmée en pied de page.
  for (const marqueur of ['__VERSION__', '__ENV__']) {
    if (!html.includes(marqueur)) {
      anomalies.push(`Marqueur « ${marqueur} » absent du pied de page.`);
    }
  }

  // ── Socle mobile ─────────────────────────────────────────────────────
  if (!/<meta[^>]+name=["']viewport["']/.test(html)) {
    anomalies.push('Balise meta viewport absente.');
  }
  if (!/<html[^>]+lang=["']fr["']/.test(html)) {
    anomalies.push('Attribut lang="fr" absent.');
  }
  if (!/<title>[^<]+<\/title>/.test(html)) {
    anomalies.push('Balise title absente ou vide.');
  }

  return anomalies;
}

// ── Exécution en ligne de commande ─────────────────────────────────────
if (import.meta.url === `file://${process.argv[1]}`) {
  const { readFileSync } = await import('node:fs');
  const chemin = process.argv[2];
  if (!chemin) {
    console.error('usage : node scripts/check-page.mjs <chemin-de-la-page>');
    process.exit(2);
  }

  const anomalies = verifierPage(readFileSync(chemin, 'utf8'));
  if (anomalies.length === 0) {
      console.log(
      `✓ ${chemin} — ${NOMBRE_DE_KIOSQUES} kiosques, ${NOMBRE_DE_CRENEAUX} créneaux, page autonome.`,
    );
    process.exit(0);
  }
  for (const anomalie of anomalies) {
    console.error(`::error::${anomalie}`);
  }
  console.error(`\n${anomalies.length} anomalie(s) dans ${chemin}.`);
  process.exit(1);
}
