import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  genererSvg,
  FRACTION_PLAQUE,
  SURFACE_MAX,
  MARGE_MODULES,
} from './generer-qr.mjs';

const URL_PROD = 'https://info-hub.jeremy-delaux.workers.dev/testing-event-2026/';
const LOGO = { largeur: 156, hauteur: 104 };
const FAUX_LOGO = 'data:image/png;base64,iVBORw0KGgo=';

test('la plaque centrale reste très en deçà du budget du niveau H', () => {
  // Le niveau H tolère ~30 % de perte, mais cette marge sert aussi aux
  // salissures, aux plis et à l'éclairage d'un hall. On ne la dépense pas
  // toute pour un logo.
  const { surfaceRecouverte } = genererSvg(URL_PROD, FAUX_LOGO, LOGO);
  assert.ok(
    surfaceRecouverte <= SURFACE_MAX,
    `surface recouverte ${(surfaceRecouverte * 100).toFixed(1)} % > ${SURFACE_MAX * 100} %`,
  );
});

test('la marge silencieuse fait au moins 4 modules', () => {
  // En deçà de 4, des lecteurs échouent à isoler le code de son fond.
  assert.ok(MARGE_MODULES >= 4);
  const { svg, modules } = genererSvg(URL_PROD, FAUX_LOGO, LOGO);
  assert.match(svg, new RegExp(`viewBox="0 0 ${modules + 8} ${modules + 8}"`));
});

test('la plaque est centrée et alignée sur la grille', () => {
  const { svg, modules } = genererSvg(URL_PROD, FAUX_LOGO, LOGO);
  const plaque = svg.match(/<rect x="([\d.]+)" y="([\d.]+)"\s+width="([\d.]+)"/);
  assert.ok(plaque, 'plaque centrale introuvable dans le SVG');
  const [x, y, cote] = plaque.slice(1).map(Number);
  assert.equal(x, y, 'plaque non centrée');
  assert.ok(Number.isInteger(cote), 'côté non aligné sur la grille');
  assert.equal(x, MARGE_MODULES + (modules - cote) / 2);
});

test('le logo est présent dans le SVG', () => {
  const { svg } = genererSvg(URL_PROD, FAUX_LOGO, LOGO);
  assert.ok(svg.includes(FAUX_LOGO));
});

test('les proportions du logo sont conservées', () => {
  const { svg } = genererSvg(URL_PROD, FAUX_LOGO, LOGO);
  const dims = svg.match(/<image[\s\S]*?width="([\d.]+)" height="([\d.]+)"/);
  const [l, h] = dims.slice(1).map(Number);
  assert.ok(
    Math.abs(l / h - LOGO.largeur / LOGO.hauteur) < 0.01,
    `rapport ${l / h} au lieu de ${LOGO.largeur / LOGO.hauteur}`,
  );
});

test('la fraction de plaque reste dans une plage raisonnable', () => {
  assert.ok(FRACTION_PLAQUE > 0 && FRACTION_PLAQUE <= 0.3);
});

test("le QR du dépôt encode bien l'URL de production", () => {
  // Le fichier committé part à l'impression : son URL ne doit pas dériver
  // silencieusement de celle du Worker de production.
  const png = readFileSync('qr/monogramme-te.png');
  const dataUri = `data:image/png;base64,${png.toString('base64')}`;
  const { svg } = genererSvg(URL_PROD, dataUri, LOGO);
  const committe = readFileSync('qr/testing-event-2026.svg', 'utf8');
  assert.equal(
    svg.trim(),
    committe.trim(),
    'qr/testing-event-2026.svg ne correspond plus à l\'URL de production — relancer « npm run qr ».',
  );
});
