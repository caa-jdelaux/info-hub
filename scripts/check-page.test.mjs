import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { verifierPage, NOMBRE_DE_KIOSQUES } from './check-page.mjs';

const PAGE = 'worker/public/testing-event-2026/index.html';

/** Page minimale conforme, pour isoler chaque contrôle. */
function pageValide(salles = Object.fromEntries(
  Array.from({ length: NOMBRE_DE_KIOSQUES }, (_, i) => [String(i + 1), '']),
)) {
  const cartes = Object.keys(salles)
    .map((n) => `<div class="kiosque-card" data-kiosque="${n}">` +
                `<div data-salle>Salle à confirmer</div></div>`)
    .join('\n');
  return `<html lang="fr"><head><meta name="viewport" content="width=device-width"/>` +
    `<title>T</title>` +
    `<script type="application/json" id="salles-data">${JSON.stringify(salles)}</script>` +
    `</head><body>${cartes}` +
    `<p><span>__ENV__</span><span>__VERSION__</span></p></body></html>`;
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
