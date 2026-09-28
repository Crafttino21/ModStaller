// Updates fuer die fest installierte Linux-Variante.
//
// electron-updater kann unter Linux nur eine AppImage durch eine neuere
// ersetzen. Die installierte Kopie ist keine - sie laedt stattdessen die
// neue Setup-AppImage, prueft deren sha512 und startet sie im Update-Modus;
// das Setup tauscht die Installation aus und startet die neue Version.
//
// Welche Version: die neueste Release auf GitHub, Betas nur im Beta-Kanal
// (channel.cjs), nie ein Downgrade. Die Pruefsumme steht in
// latest-linux-setup.yml, die die Release-Pipeline neben die AppImage legt.
//
// Eigene Datei ohne Electron, damit sich die Auswahl pruefen laesst.

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const OWNER = "Crafttino21";
const REPO = "ModStaller";

/** So heisst die Datei mit Version und Pruefsumme in jeder Release. */
const SETUP_YML = "latest-linux-setup.yml";

// Bewusst ohne semver/js-yaml: beide liegen nur verschachtelt unter
// electron-updater (bzw. als Dev-Abhaengigkeit) und waeren in der gepackten
// App von hier aus nicht zu finden. Was wir brauchen, ist klein.

const SEMVER = /^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$/;

/** "1.2.1-beta.5" -> Teile, oder null. */
function parseVersion(v) {
  const m = SEMVER.exec(String(v ?? "").trim().replace(/^v/, ""));
  if (!m) return null;
  return { core: [Number(m[1]), Number(m[2]), Number(m[3])], pre: m[4] ? m[4].split(".") : [] };
}

/** Vergleich nach SemVer 2.0: <0, 0, >0. */
function compareVersions(a, b) {
  const x = parseVersion(a);
  const y = parseVersion(b);
  if (!x || !y) throw new Error(`Keine Version: ${!x ? a : b}`);
  for (let i = 0; i < 3; i++) if (x.core[i] !== y.core[i]) return x.core[i] - y.core[i];
  // Ohne Vorab-Anhang ist eine Version *neuer* als mit.
  if (!x.pre.length || !y.pre.length) return y.pre.length - x.pre.length;
  for (let i = 0; i < Math.max(x.pre.length, y.pre.length); i++) {
    const p = x.pre[i];
    const q = y.pre[i];
    if (p === undefined) return -1;
    if (q === undefined) return 1;
    const pn = /^\d+$/.test(p);
    const qn = /^\d+$/.test(q);
    if (pn && qn) { if (Number(p) !== Number(q)) return Number(p) - Number(q); }
    else if (pn !== qn) return pn ? -1 : 1;
    else if (p !== q) return p < q ? -1 : 1;
  }
  return 0;
}

/** Die paar Felder aus der yml, die electron-builder schreibt - flach gelesen. */
function ymlFields(text) {
  const out = { files: [] };
  let file = null;
  for (const raw of String(text).split(/\r?\n/)) {
    const item = /^\s*-\s+(\w+):\s*(.*)$/.exec(raw);
    const field = /^(\s*)(\w+):\s*(.*)$/.exec(raw);
    const unquote = (v) => v.trim().replace(/^(['"])(.*)\1$/, "$2");
    if (item) {
      file = { [item[1]]: unquote(item[2]) };
      out.files.push(file);
    } else if (field && field[1].length && file) {
      file[field[2]] = unquote(field[3]);
    } else if (field && !field[1].length) {
      file = null;
      if (field[3].trim()) out[field[2]] = unquote(field[3]);
    }
  }
  return out;
}

/**
 * Die Release, auf die aktualisiert werden soll - oder null.
 * `releases` ist die Antwort von GET /repos/{owner}/{repo}/releases.
 */
function pickRelease(releases, current, { beta }) {
  let best = null;
  for (const r of releases ?? []) {
    if (r.draft) continue;
    const parsed = parseVersion(r.tag_name);
    if (!parsed) continue;
    const version = String(r.tag_name).trim().replace(/^v/, "");
    const pre = parsed.pre.length > 0;
    if (pre && !beta) continue;
    // Ein Beta-Tag, das GitHub nicht als Vorabversion markiert hat, zaehlt
    // trotzdem als Beta - entscheidend ist die Version.
    if (!r.assets?.some((a) => a.name === SETUP_YML)) continue;
    if (compareVersions(version, current) <= 0) continue;
    if (!best || compareVersions(version, best.version) > 0) best = { version, release: r };
  }
  return best;
}

/** Name und sha512 der Setup-AppImage aus latest-linux-setup.yml. */
function parseSetupYml(text) {
  const doc = ymlFields(text);
  const file = doc?.files?.find((f) => /\.AppImage$/.test(f.url ?? "")) ?? null;
  const name = file?.url ?? doc?.path;
  const sha512 = file?.sha512 ?? doc?.sha512;
  if (!doc?.version || !name || !sha512) throw new Error(`${SETUP_YML} unvollstaendig`);
  // Nur ein Dateiname, nie ein Pfad - er landet im Cache-Ordner.
  if (path.basename(name) !== name) throw new Error(`${SETUP_YML}: ungueltiger Dateiname`);
  const size = Number(file?.size);
  return { version: doc.version, name, sha512, size: Number.isFinite(size) && size > 0 ? size : null };
}

function assetUrl(release, name) {
  const asset = release.assets?.find((a) => a.name === name);
  if (!asset) throw new Error(`${name} fehlt in der Release ${release.tag_name}`);
  return asset.browser_download_url;
}

async function getJson(fetchImpl, url) {
  const res = await fetchImpl(url, {
    headers: { Accept: "application/vnd.github+json", "User-Agent": "ModStaller" },
  });
  if (!res.ok) throw new Error(`GitHub: HTTP ${res.status}`);
  return res.json();
}

/**
 * Sucht nach einem Update. Ergebnis: null oder
 * { version, notes, url, name, sha512, size }.
 */
async function check({ current, beta, fetchImpl = fetch }) {
  const releases = await getJson(fetchImpl,
    `https://api.github.com/repos/${OWNER}/${REPO}/releases?per_page=30`);
  const pick = pickRelease(releases, current, { beta });
  if (!pick) return null;
  const ymlRes = await fetchImpl(assetUrl(pick.release, SETUP_YML), {
    headers: { "User-Agent": "ModStaller" },
  });
  if (!ymlRes.ok) throw new Error(`${SETUP_YML}: HTTP ${ymlRes.status}`);
  const info = parseSetupYml(await ymlRes.text());
  return {
    version: pick.version,
    notes: pick.release.body ?? "",
    url: assetUrl(pick.release, info.name),
    name: info.name,
    sha512: info.sha512,
    size: info.size,
  };
}

/**
 * Laedt die Setup-AppImage nach `dir`, prueft sie und macht sie ausfuehrbar.
 * Erst nach bestandener Pruefung bekommt sie ihren endgueltigen Namen - ein
 * halber oder falscher Download kann also nie gestartet werden.
 */
async function download(update, { dir, fetchImpl = fetch, onProgress = () => {} }) {
  fs.mkdirSync(dir, { recursive: true });
  const target = path.join(dir, update.name);
  const part = `${target}.part`;
  const res = await fetchImpl(update.url, { headers: { "User-Agent": "ModStaller" } });
  if (!res.ok || !res.body) throw new Error(`Download: HTTP ${res.status}`);

  const total = Number(res.headers.get("content-length")) || update.size || 0;
  const hash = crypto.createHash("sha512");
  const out = fs.createWriteStream(part);
  let received = 0;
  try {
    for await (const chunk of res.body) {
      hash.update(chunk);
      received += chunk.length;
      if (!out.write(chunk)) await new Promise((r) => out.once("drain", r));
      if (total) onProgress(Math.min(100, Math.round((received / total) * 100)));
    }
  } finally {
    await new Promise((r) => out.end(r));
  }

  if (hash.digest("base64") !== update.sha512) {
    fs.rmSync(part, { force: true });
    throw new Error("Pruefsumme der Setup-AppImage stimmt nicht - Download verworfen.");
  }
  fs.chmodSync(part, 0o755);
  fs.renameSync(part, target);
  return target;
}

module.exports = {
  SETUP_YML, compareVersions, pickRelease, parseSetupYml, check, download,
};
