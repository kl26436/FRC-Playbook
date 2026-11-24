// Copies the simulated-run recordings from the robot code repo into public/replays/ before a build.
// The recordings are made by the code's own tests (see docs/playbook/replays/README.md in that repo).
// If a file cannot be fetched, the copy already in this repo is kept, so a build never fails on this step.
import { mkdir, readdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const SOURCE = 'https://raw.githubusercontent.com/kl26436/ClaudeBot/main/docs/playbook/replays';
const FILES = [
  'leave',
  'one_right',
  'one_centre',
  'one_left',
  'three_right_ecd',
  'three_left_jlk',
  'centre_h_algae',
  'climb',
];
const dir = fileURLToPath(new URL('../public/replays/', import.meta.url));
await mkdir(dir, { recursive: true });

for (const name of FILES) {
  try {
    const res = await fetch(`${SOURCE}/${name}.json`, { signal: AbortSignal.timeout(15000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const text = await res.text();
    const data = JSON.parse(text);
    if (!Array.isArray(data.columns) || !Array.isArray(data.samples)) throw new Error('not a replay file');
    await writeFile(`${dir}${name}.json`, text);
    console.log(`replays: fetched ${name}`);
  } catch (err) {
    console.log(`replays: ${name} not fetched (${err.message}); using the copy in this repo if there is one`);
  }
}

// The player reads this list, in the order above, so it only offers recordings that exist.
const present = new Set((await readdir(dir)).filter((f) => f.endsWith('.json') && f !== 'index.json'));
const index = [];
for (const name of FILES) {
  if (!present.has(`${name}.json`)) continue;
  const data = JSON.parse(await readFile(`${dir}${name}.json`, 'utf8'));
  index.push({ file: `${name}.json`, label: data.label ?? name, columns: data.columns });
}
await writeFile(`${dir}index.json`, JSON.stringify(index, null, 2) + '\n');
console.log(`replays: ${index.length} available`);
