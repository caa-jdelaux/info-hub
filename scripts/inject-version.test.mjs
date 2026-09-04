import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  injecterVersion,
  MARQUEUR_VERSION,
  MARQUEUR_ENV,
} from './inject-version.mjs';

const gabarit = `<p class="version"><span class="version-env">${MARQUEUR_ENV}</span><span>${MARQUEUR_VERSION}</span></p>`;

test('les deux marqueurs sont remplacés', () => {
  const sortie = injecterVersion(gabarit, '14/09/2026 09:12 · a1b2c3d', 'DEV');
  assert.equal(
    sortie,
    '<p class="version"><span class="version-env">DEV</span>' +
      '<span>14/09/2026 09:12 · a1b2c3d</span></p>',
  );
});

test('en production la puce est vidée, donc masquée par :empty', () => {
  const sortie = injecterVersion(gabarit, '14/09/2026 09:12 · a1b2c3d');
  assert.match(sortie, /<span class="version-env"><\/span>/);
});

test('un marqueur de version absent lève une erreur', () => {
  // Un remplacement sans effet laisserait « __VERSION__ » visible en ligne.
  assert.throws(
    () => injecterVersion(`<span>${MARQUEUR_ENV}</span>`, 'v1'),
    /__VERSION__ introuvable/,
  );
});

test("un marqueur d'environnement absent lève une erreur", () => {
  assert.throws(
    () => injecterVersion(`<span>${MARQUEUR_VERSION}</span>`, 'v1'),
    /__ENV__ introuvable/,
  );
});

test('une version vide lève une erreur', () => {
  assert.throws(() => injecterVersion(gabarit, '   '), /vide/);
});

test('version et environnement sont échappés avant insertion', () => {
  const sortie = injecterVersion(gabarit, '<script>x</script>', '<b>');
  assert.ok(!sortie.includes('<script>'));
  assert.match(sortie, /&lt;b&gt;/);
});
