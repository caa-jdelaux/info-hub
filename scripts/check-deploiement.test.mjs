import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  extraireSalles,
  comparer,
  attendreConformite,
} from './check-deploiement.mjs';

const page = (salles, version = '14/09/2026 09:12 · a1b2c3d') =>
  `<html><script type="application/json" id="salles-data">${JSON.stringify(salles)}</script>` +
  `<p>${version}</p></html>`;

test('le bloc de données est extrait', () => {
  assert.deepEqual(extraireSalles(page({ 1: 'Salle A' })), { 1: 'Salle A' });
});

test('un bloc illisible renvoie null plutôt que de lever', () => {
  assert.equal(extraireSalles('<html></html>'), null);
  assert.equal(
    extraireSalles('<script id="salles-data">{ pas du json }</script>'),
    null,
  );
});

test('une page conforme ne remonte rien', () => {
  const salles = { 1: 'Salle A', 2: 'Salle B' };
  assert.deepEqual(comparer(page(salles), salles, '14/09/2026 09:12 · a1b2c3d'), []);
});

test('une salle périmée côté serveur est signalée', () => {
  // Le scénario redouté : le déploiement passe au vert mais l'URL sert encore
  // l'affectation de la veille.
  const anomalies = comparer(page({ 1: 'Salle A' }), { 1: 'Salle B' }, null);
  assert.equal(anomalies.length, 1);
  assert.match(anomalies[0], /Kiosque 1/);
});

test('une version antérieure encore servie est signalée', () => {
  const salles = { 1: 'Salle A' };
  const anomalies = comparer(page(salles, 'vieille version'), salles, '14/09/2026 09:12 · a1b2c3d');
  assert.ok(anomalies.some((a) => /n'est pas celui qui répond/.test(a)));
});

test('un marqueur non remplacé est signalé', () => {
  const salles = { 1: 'Salle A' };
  const anomalies = comparer(page(salles, '__VERSION__'), salles, null);
  assert.ok(anomalies.some((a) => /non remplacé/.test(a)));
});

test('une ressource distante servie est signalée', () => {
  const salles = { 1: 'Salle A' };
  const html = page(salles).replace('</html>', '<link href="https://cdn.example/x.css"/></html>');
  const anomalies = comparer(html, salles, null);
  assert.ok(anomalies.some((a) => /Ressource distante servie/.test(a)));
});

// ── Attente de la propagation ──────────────────────────────────────────
// Le défaut corrigé ici : Cloudflare répond 200 en servant encore la version
// précédente. La première version du contrôle sortait de sa boucle dès la
// première réponse valide et concluait à une panne au bout d'une seconde.

/** Réponse factice, façon fetch. */
function reponse(html, ok = true, status = 200) {
  return { ok, status, text: async () => html };
}

/** Page témoin servie, avec ses salles et sa version. */
function pageServie(salles, version) {
  return `<html><script type="application/json" id="salles-data">` +
    `${JSON.stringify(salles)}</script><p>${version}</p></html>`;
}

test('une page encore périmée est réinterrogée jusqu\'à propagation', async () => {
  const attendues = { 1: 'Douro', 2: '' };
  const reponses = [
    reponse(pageServie({ 1: '', 2: '' }, 'v1')),
    reponse(pageServie({ 1: '', 2: '' }, 'v1')),
    reponse(pageServie(attendues, 'v2')),
  ];
  let attentes = 0;
  const anomalies = await attendreConformite('https://exemple.test/', attendues, 'v2', {
    tentatives: 5,
    recuperer: async () => reponses.shift(),
    patienter: async () => { attentes += 1; },
  });
  assert.deepEqual(anomalies, []);
  assert.equal(attentes, 2, 'deux attentes avant la troisième tentative');
});

test('une page qui reste périmée finit par être signalée', async () => {
  const attendues = { 1: 'Douro' };
  const anomalies = await attendreConformite('https://exemple.test/', attendues, 'v2', {
    tentatives: 3,
    recuperer: async () => reponse(pageServie({ 1: '' }, 'v1')),
    patienter: async () => {},
  });
  assert.equal(anomalies.length, 2);
  assert.match(anomalies[0], /Kiosque 1/);
  assert.match(anomalies[1], /Version/);
});

test('une erreur HTTP passagère n\'empêche pas la réussite', async () => {
  const attendues = { 1: 'Douro' };
  const reponses = [
    reponse('', false, 502),
    reponse(pageServie(attendues, 'v2')),
  ];
  const anomalies = await attendreConformite('https://exemple.test/', attendues, 'v2', {
    tentatives: 4,
    recuperer: async () => reponses.shift(),
    patienter: async () => {},
  });
  assert.deepEqual(anomalies, []);
});

test('une URL injoignable est signalée après épuisement des tentatives', async () => {
  const anomalies = await attendreConformite('https://exemple.test/', { 1: '' }, 'v2', {
    tentatives: 2,
    recuperer: async () => { throw new Error('ECONNREFUSED'); },
    patienter: async () => {},
  });
  assert.equal(anomalies.length, 1);
  assert.match(anomalies[0], /ECONNREFUSED/);
});
