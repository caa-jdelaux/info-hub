import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  genererSvg,
  FRACTION_LOGO,
  RESPIRATION_MODULES,
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
  // La plaque épouse le format du logo : elle n'est plus carrée, et chaque
  // dimension se centre indépendamment.
  const { svg, modules, plaque } = genererSvg(URL_PROD, FAUX_LOGO, LOGO);
  const rect = svg.match(/<rect x="([\d.]+)" y="([\d.]+)"\s+width="([\d.]+)" height="([\d.]+)"/);
  assert.ok(rect, 'plaque centrale introuvable dans le SVG');
  const [x, y, l, h] = rect.slice(1).map(Number);
  assert.ok(Number.isInteger(l) && Number.isInteger(h), 'plaque non alignée sur la grille');
  assert.equal(x, MARGE_MODULES + (modules - plaque.largeur) / 2, 'plaque non centrée en X');
  assert.equal(y, MARGE_MODULES + (modules - plaque.hauteur) / 2, 'plaque non centrée en Y');
  assert.equal(l, plaque.largeur);
  assert.equal(h, plaque.hauteur);
});

test('la plaque épouse le format du logo, sans blanc perdu', () => {
  // Une plaque carrée sous un monogramme en 1,5:1 laissait du blanc en haut
  // et en bas : ce blanc recouvrait des modules sans rien afficher.
  const { plaque, logo } = genererSvg(URL_PROD, FAUX_LOGO, LOGO);
  for (const [nom, cote, dim] of [
    ['largeur', plaque.largeur, logo.largeur],
    ['hauteur', plaque.hauteur, logo.hauteur],
  ]) {
    const marge = (cote - dim) / 2;
    assert.ok(
      marge >= 0 && marge <= RESPIRATION_MODULES + 1,
      `${nom} : ${marge.toFixed(2)} module(s) de blanc, au-delà de la respiration`,
    );
  }
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

test('la taille du logo garde un facteur deux sur le point de rupture', () => {
  // Rupture mesurée à 25,3 % de surface en conditions idéales. Le papier
  // imprimé et un appareil photo en offrent bien moins : on ne s'en approche
  // pas.
  const { surfaceRecouverte } = genererSvg(URL_PROD, FAUX_LOGO, LOGO);
  assert.ok(FRACTION_LOGO > 0 && FRACTION_LOGO < 0.5);
  assert.ok(
    surfaceRecouverte * 2 <= 0.253,
    `surface ${(surfaceRecouverte * 100).toFixed(1)} % : moins d'un facteur deux sous 25,3 %`,
  );
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
