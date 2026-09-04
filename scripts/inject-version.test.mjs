import { test } from 'node:test';
import assert from 'node:assert/strict';
import { injecterVersion, MARQUEUR } from './inject-version.mjs';

test('le marqueur est remplacé', () => {
  const sortie = injecterVersion(`<p>${MARQUEUR}</p>`, '2026-09-14 09:12 · a1b2c3d');
  assert.equal(sortie, '<p>2026-09-14 09:12 · a1b2c3d</p>');
});

test('un marqueur absent lève une erreur plutôt que de ne rien faire', () => {
  // Un remplacement sans effet laisserait « __VERSION__ » visible en ligne.
  assert.throws(() => injecterVersion('<p>rien</p>', 'v1'), /introuvable/);
});

test('une version vide lève une erreur', () => {
  assert.throws(() => injecterVersion(`<p>${MARQUEUR}</p>`, '   '), /vide/);
});

test('la version est échappée avant insertion', () => {
  const sortie = injecterVersion(`<p>${MARQUEUR}</p>`, '<script>x</script>');
  assert.equal(sortie, '<p>&lt;script&gt;x&lt;/script&gt;</p>');
});
