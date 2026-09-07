/**
 * Contrôle après déploiement.
 *
 * Déployer sans vérifier que le service répond, c'est apprendre la panne par un
 * participant. Ce contrôle interroge l'URL réellement publiée et vérifie que ce
 * qu'elle sert correspond à ce qui vient d'être poussé — en particulier le bloc
 * des salles, seule donnée éditée le jour J, et depuis un téléphone.
 */

import { readFileSync } from 'node:fs';

/*
 * La propagation d'un déploiement Cloudflare n'est pas instantanée : l'URL
 * répond 200 en servant encore la version précédente. Le contrôle réessaie
 * donc jusqu'à ce que la page servie corresponde, et pas seulement jusqu'à ce
 * qu'elle réponde — c'était le défaut de la première version, qui concluait à
 * une panne au bout d'une seconde. Trente-cinq secondes d'attente ne coûtent
 * rien, même le 14 au matin ; un faux rouge, si.
 */
export const TENTATIVES = 8;
export const ATTENTE_MS = 5000;

/** Extrait le bloc de données d'une page. @returns {object|null} */
export function extraireSalles(html) {
  const bloc = html.match(
    /<script[^>]*id=["']salles-data["'][^>]*>([\s\S]*?)<\/script>/,
  );
  if (!bloc) return null;
  try {
    return JSON.parse(bloc[1]);
  } catch {
    return null;
  }
}

/**
 * Compare la page servie à ce qui a été poussé.
 * @returns {string[]} Anomalies ; vide si tout concorde.
 */
export function comparer(htmlServi, sallesAttendues, versionAttendue) {
  const anomalies = [];

  const sallesServies = extraireSalles(htmlServi);
  if (sallesServies === null) {
    anomalies.push('Bloc « salles-data » absent ou illisible dans la page servie.');
  } else {
    for (const [kiosque, valeur] of Object.entries(sallesAttendues)) {
      if (sallesServies[kiosque] !== valeur) {
        anomalies.push(
          `Kiosque ${kiosque} : la page servie annonce ` +
            `${JSON.stringify(sallesServies[kiosque])}, ` +
            `le dépôt ${JSON.stringify(valeur)}.`,
        );
      }
    }
  }

  // Preuve que l'URL sert bien le déploiement qui vient d'avoir lieu, et non
  // une version antérieure encore en cache.
  if (versionAttendue && !htmlServi.includes(versionAttendue)) {
    anomalies.push(
      `Version « ${versionAttendue} » absente de la page servie : ` +
        'le déploiement n\'est pas celui qui répond.',
    );
  }

  for (const marqueur of ['__VERSION__', '__ENV__']) {
    if (htmlServi.includes(marqueur)) {
      anomalies.push(`Marqueur « ${marqueur} » non remplacé dans la page servie.`);
    }
  }

  const distantes = [
    ...htmlServi.matchAll(/(?:src|href)=["'](https?:\/\/[^"']+)["']/g),
  ].map((m) => m[1]);
  for (const url of distantes) {
    anomalies.push(`Ressource distante servie : ${url}.`);
  }

  return anomalies;
}

/**
 * Interroge l'URL jusqu'à ce qu'elle serve la version attendue.
 *
 * Les dépendances externes sont injectables pour que la boucle soit testable
 * sans réseau ni attente réelle.
 *
 * @returns {Promise<string[]>} Anomalies restantes ; vide si tout concorde.
 */
export async function attendreConformite(url, attendues, version, options = {}) {
  const {
    tentatives = TENTATIVES,
    attenteMs = ATTENTE_MS,
    recuperer = (u) => fetch(u, { headers: { 'Cache-Control': 'no-cache' } }),
    patienter = (ms) => new Promise((r) => setTimeout(r, ms)),
    journal = () => {},
  } = options;

  let dernieres = [`${url} n'a jamais répondu.`];

  for (let n = 1; n <= tentatives; n += 1) {
    let html = null;
    try {
      const reponse = await recuperer(url);
      if (reponse.ok) {
        html = await reponse.text();
      } else {
        dernieres = [`${url} : HTTP ${reponse.status}.`];
      }
    } catch (erreur) {
      dernieres = [`${url} : ${erreur.message}`];
    }

    if (html !== null) {
      dernieres = comparer(html, attendues, version);
      if (dernieres.length === 0) {
        journal(`tentative ${n}/${tentatives} : conforme.`);
        return [];
      }
    }

    journal(`tentative ${n}/${tentatives} : ${dernieres[0]}`);
    if (n < tentatives) {
      await patienter(attenteMs);
    }
  }

  return dernieres;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const [url, cheminLocal, version] = process.argv.slice(2);
  if (!url || !cheminLocal) {
    console.error(
      'usage : node scripts/check-deploiement.mjs <url> <page-locale> [version]',
    );
    process.exit(2);
  }

  const attendues = extraireSalles(readFileSync(cheminLocal, 'utf8'));
  if (attendues === null) {
    console.error('::error::Bloc « salles-data » illisible dans le fichier local.');
    process.exit(1);
  }

  const anomalies = await attendreConformite(url, attendues, version, {
    journal: (ligne) => console.log(ligne),
  });
  if (anomalies.length === 0) {
    console.log(
      `✓ ${url} sert bien la version poussée (${Object.keys(attendues).length} kiosques).`,
    );
    process.exit(0);
  }
  for (const anomalie of anomalies) console.error(`::error::${anomalie}`);
  process.exit(1);
}
