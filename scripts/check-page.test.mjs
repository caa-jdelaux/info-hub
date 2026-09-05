import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  verifierPage,
  NOMBRE_DE_KIOSQUES,
  NOMBRE_DE_CRENEAUX,
  NOMBRE_DE_ROTATIONS,
} from './check-page.mjs';

const PAGE = 'worker/public/testing-event-2026/index.html';

/** Créneaux témoins : bornes croissantes, sans chevauchement. */
function creneauxValides(nombre = NOMBRE_DE_CRENEAUX) {
  return Array.from(
    { length: nombre },
    (_, i) => `<div data-debut="${540 + i * 30}" data-fin="${540 + i * 30 + 25}"></div>`,
  ).join('\n');
}

/** Rotations témoins, sans horodatage : elles ne comptent pas comme créneaux. */
function rotations(nombre = NOMBRE_DE_ROTATIONS) {
  return Array.from({ length: nombre }, () => '<div class="rotation-slot"></div>').join('');
}

/** Page minimale conforme, pour isoler chaque contrôle. */
function pageValide(salles = Object.fromEntries(
  Array.from({ length: NOMBRE_DE_KIOSQUES }, (_, i) => [String(i + 1), '']),
), creneaux = creneauxValides(), rotationsHtml = rotations(), plafond = NOMBRE_DE_ROTATIONS) {
  const cartes = Object.keys(salles)
    .map((n) => `<article class="kiosque-card" data-kiosque="${n}">` +
                `<div data-salle>Salle à confirmer</div></article>`)
    .join('\n');
  return `<html lang="fr"><head><meta name="viewport" content="width=device-width"/>` +
    `<title>T</title>` +
    `<script type="application/json" id="salles-data">${JSON.stringify(salles)}</script>` +
    `</head><body>${cartes}${creneaux}${rotationsHtml}` +
    `<p><span>__ENV__</span><span>__VERSION__</span></p>` +
    `<script>var MAX_SELECTION = ${plafond};</script></body></html>`;
}

test('la page réelle du dépôt passe tous les contrôles', () => {
  assert.deepEqual(verifierPage(readFileSync(PAGE, 'utf8')), []);
});

test('une page témoin conforme ne remonte rien', () => {
  assert.deepEqual(verifierPage(pageValide()), []);
});

test('un bloc de données absent est signalé', () => {
  const anomalies = verifierPage('<html lang="fr"></html>');
  assert.equal(anomalies.length, 1);
  assert.match(anomalies[0], /introuvable/);
});

test('une virgule de trop dans le bloc est signalée', () => {
  // Le mode de défaillance attendu d'une saisie au clavier tactile.
  const casse = pageValide().replace(/"10":""/, '"10":"",');
  const anomalies = verifierPage(casse);
  assert.equal(anomalies.length, 1);
  assert.match(anomalies[0], /JSON invalide/);
});

test('un kiosque manquant dans le bloc est signalé', () => {
  const salles = Object.fromEntries(
    Array.from({ length: NOMBRE_DE_KIOSQUES - 1 }, (_, i) => [String(i + 1), '']),
  );
  const anomalies = verifierPage(pageValide(salles));
  assert.ok(anomalies.some((a) => /kiosque 10 absent/.test(a)));
});

test('une clef inattendue est signalée', () => {
  const salles = Object.fromEntries(
    Array.from({ length: NOMBRE_DE_KIOSQUES }, (_, i) => [String(i + 1), '']),
  );
  salles['11'] = 'Salle X';
  const anomalies = verifierPage(pageValide(salles));
  assert.ok(anomalies.some((a) => /clef inattendue/.test(a)));
});

test('une valeur non textuelle est signalée', () => {
  const salles = Object.fromEntries(
    Array.from({ length: NOMBRE_DE_KIOSQUES }, (_, i) => [String(i + 1), '']),
  );
  salles['3'] = 212; // guillemets oubliés
  const anomalies = verifierPage(pageValide(salles));
  assert.ok(anomalies.some((a) => /kiosque 3.*chaîne est attendue/.test(a)));
});

test('une ressource distante est signalée', () => {
  const avecCdn = pageValide().replace(
    '</head>',
    '<link href="https://fonts.googleapis.com/css2?family=Barlow"/></head>',
  );
  const anomalies = verifierPage(avecCdn);
  assert.ok(anomalies.some((a) => /Ressource distante/.test(a)));
});

test('une version déjà injectée et committée est signalée', () => {
  const anomalies = verifierPage(pageValide().replace('__VERSION__', '2026-09-14 · abc1234'));
  assert.ok(anomalies.some((a) => /__VERSION__/.test(a)));
});

test('un emplacement de salle manquant est signalé', () => {
  const anomalies = verifierPage(pageValide().replace('<div data-salle>Salle à confirmer</div>', ''));
  assert.ok(anomalies.some((a) => /kiosque 1 sans emplacement/.test(a)));
});

test('la meta viewport est exigée', () => {
  const anomalies = verifierPage(pageValide().replace(/<meta name="viewport"[^>]*\/>/, ''));
  assert.ok(anomalies.some((a) => /viewport/.test(a)));
});

test('les cartes sont reconnues quelle que soit leur balise', () => {
  // Les cartes sont passées de <div> à <article> ; le contrôle ne doit pas
  // dépendre du nom de la balise.
  assert.deepEqual(verifierPage(pageValide().replace(/article/g, 'div')), []);
});

test('un créneau manquant est signalé', () => {
  const anomalies = verifierPage(pageValide(undefined, creneauxValides(NOMBRE_DE_CRENEAUX - 1)));
  assert.ok(anomalies.some((a) => /créneau\(x\) horodaté/.test(a)));
});

test('un créneau dont la fin précède le début est signalé', () => {
  const anomalies = verifierPage(
    pageValide(undefined, creneauxValides(NOMBRE_DE_CRENEAUX - 1) +
      '<div data-debut="900" data-fin="880"></div>'),
  );
  assert.ok(anomalies.some((a) => /la fin ne suit pas le début/.test(a)));
});

test('un chevauchement de créneaux est signalé', () => {
  // Deux repères « en ce moment » simultanés : le participant ne saurait
  // plus lequel lire.
  const anomalies = verifierPage(
    pageValide(undefined,
      '<div data-debut="540" data-fin="600"></div>' +
      '<div data-debut="570" data-fin="630"></div>' +
      creneauxValides(NOMBRE_DE_CRENEAUX - 2)),
  );
  assert.ok(anomalies.some((a) => /chevauche ou précède/.test(a)));
});

test('un créneau hors de la journée est signalé', () => {
  const anomalies = verifierPage(
    pageValide(undefined, creneauxValides(NOMBRE_DE_CRENEAUX - 1) +
      '<div data-debut="1500" data-fin="1600"></div>'),
  );
  assert.ok(anomalies.some((a) => /hors d'une journée/.test(a)));
});

test('un plafond de sélection décorrélé des rotations est signalé', () => {
  // Le cas qui compte : cinq rotations, un plafond resté à quatre. Personne
  // ne le verrait avant que le sixième clic soit refusé à tort le jour J.
  const anomalies = verifierPage(
    pageValide(undefined, undefined, rotations(), NOMBRE_DE_ROTATIONS - 1),
  );
  assert.equal(anomalies.length, 1);
  assert.match(anomalies[0], /un kiosque par rotation/);
});

test('une rotation ajoutée sans relever le plafond est signalée', () => {
  const anomalies = verifierPage(
    pageValide(undefined, undefined, rotations(NOMBRE_DE_ROTATIONS + 1)),
  );
  assert.equal(anomalies.length, 2);
  assert.match(anomalies[0], /rotation\(s\) trouvée\(s\)/);
  assert.match(anomalies[1], /un kiosque par rotation/);
});

test('un plafond de sélection absent est signalé', () => {
  const anomalies = verifierPage(pageValide().replace(/var MAX_SELECTION = \d+;/, ''));
  assert.equal(anomalies.length, 1);
  assert.match(anomalies[0], /MAX_SELECTION/);
});
