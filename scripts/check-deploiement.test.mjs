import { test } from 'node:test';
import assert from 'node:assert/strict';
import { extraireSalles, comparer } from './check-deploiement.mjs';

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
