import * as fs from 'node:fs';
import * as path from 'node:path';
import { spawnSync } from 'node:child_process';
import { components, type Component, type RuntimeHomes } from './install.ts';
import { isRecord } from './mise.ts';

// Local, private machine state outside the checkout. The receipt records what
// ./cli actually applied; machine.json, written by hand, records intent that
// health checks against. Both are optional: a first install has neither.

export type Checkout = { revision?: string, dirty: boolean };
export type Outcome = 'complete' | 'kept-conflicts' | 'failed';
export type ComponentRecord = Checkout & { at: string, action: 'install' | 'uninstall', keptConflicts: boolean };
export type Run = Checkout & {
  at: string, action: 'install' | 'uninstall', components: Component[], outcome: Outcome,
  failed?: Component, error?: string, kept: string[],
};
export type Receipt = {
  version: 1,
  lastRun: Run,
  // The latest install or uninstall of each component, which may predate lastRun.
  components: Partial<Record<Component, ComponentRecord>>,
  // Homes that agents and skills were installed into, so health checks them all.
  runtimeHomes: { codex: string[], claude: string[] },
  // mise's resolved versions in the home directory when lastRun finished.
  tools?: Record<string, string>,
};
export type Role = 'command-center' | 'worker';
// Who runs node, npm, pnpm, yarn and bun in a terminal: mise, with Vite+'s shims
// in system-first mode, or Vite+'s own managed runtimes.
export type JsRuntimes = 'mise' | 'vite-plus';
export type Machine = { role?: Role, jsRuntimes: JsRuntimes, codexHomes: string[], claudeConfigDirs: string[], exceptions: Record<string, string> };

export function receiptPath(home: string) {
  return path.join(process.env.XDG_STATE_HOME || path.join(home, '.local/state'), 'donnes-configs/receipt.json');
}

export function machinePath(home: string) {
  return path.join(process.env.XDG_CONFIG_HOME || path.join(home, '.config'), 'donnes-configs/machine.json');
}

const text = (value: unknown) => typeof value === 'string' ? value : undefined;
const texts = (value: unknown) => Array.isArray(value) ? value.filter(item => typeof item === 'string') : [];
const component = (value: unknown) => components.find(name => name === value);
const action = (value: unknown) => value === 'uninstall' ? 'uninstall' : 'install';

function checkout(value: Record<string, unknown>): Checkout {
  return { revision: text(value.revision), dirty: value.dirty === true };
}

function readJson(file: string) {
  if (!fs.existsSync(file)) return undefined;
  try {
    const value: unknown = JSON.parse(fs.readFileSync(file, 'utf8'));
    return value;
  } catch (error) {
    throw new Error(`${file}: ${error instanceof Error ? error.message : String(error)}`);
  }
}

export function readReceipt(home: string): Receipt | undefined {
  const file = receiptPath(home), value = readJson(file);
  if (value === undefined) return undefined;
  if (!isRecord(value) || value.version !== 1 || !isRecord(value.lastRun) || !isRecord(value.components)) {
    throw new Error(`${file}: unrecognized receipt; move it aside and rerun ./cli`);
  }
  const run = value.lastRun;
  const outcome = run.outcome === 'complete' || run.outcome === 'kept-conflicts' ? run.outcome : 'failed';
  const records: Receipt['components'] = {};
  for (const [name, record] of Object.entries(value.components)) {
    const key = component(name);
    if (key && isRecord(record)) records[key] = { ...checkout(record), at: text(record.at) ?? '', action: action(record.action), keptConflicts: record.keptConflicts === true };
  }
  const homes = isRecord(value.runtimeHomes) ? value.runtimeHomes : {};
  const tools = isRecord(value.tools) ? Object.fromEntries(Object.entries(value.tools).flatMap(([name, version]) => typeof version === 'string' ? [[name, version]] : [])) : undefined;
  return {
    version: 1,
    lastRun: {
      ...checkout(run), at: text(run.at) ?? '', action: action(run.action), outcome, failed: component(run.failed), error: text(run.error),
      components: texts(run.components).flatMap(name => component(name) ?? []), kept: texts(run.kept),
    },
    components: records,
    runtimeHomes: { codex: texts(homes.codex), claude: texts(homes.claude) },
    tools,
  };
}

export function readMachine(home: string): Machine | undefined {
  const file = machinePath(home), value = readJson(file);
  if (value === undefined) return undefined;
  if (!isRecord(value)) throw new Error(`${file}: expected an object`);
  if (value.role !== undefined && value.role !== 'command-center' && value.role !== 'worker') throw new Error(`${file}: role must be command-center or worker`);
  if (value.jsRuntimes !== undefined && value.jsRuntimes !== 'mise' && value.jsRuntimes !== 'vite-plus') throw new Error(`${file}: jsRuntimes must be mise or vite-plus`);
  const expand = (file: string) => file.startsWith('~/') ? path.join(home, file.slice(2)) : path.resolve(file);
  const exceptions = isRecord(value.exceptions) ? value.exceptions : {};
  return {
    role: value.role, jsRuntimes: value.jsRuntimes ?? 'mise', codexHomes: texts(value.codexHomes).map(expand), claudeConfigDirs: texts(value.claudeConfigDirs).map(expand),
    exceptions: Object.fromEntries(Object.entries(exceptions).flatMap(([id, reason]) => typeof reason === 'string' ? [[id, reason]] : [])),
  };
}

export function checkoutState(repo: string): Checkout {
  const revision = spawnSync('git', ['-C', repo, 'rev-parse', 'HEAD'], { encoding: 'utf8' });
  if (revision.error || revision.status !== 0) return { dirty: false };
  const status = spawnSync('git', ['-C', repo, 'status', '--porcelain'], { encoding: 'utf8' });
  return { revision: revision.stdout.trim(), dirty: Boolean(status.stdout?.trim()) };
}

export function writeReceipt(home: string, receipt: Receipt) {
  const file = receiptPath(home);
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  const temporary = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, JSON.stringify(receipt, null, 2) + '\n', { mode: 0o600 });
  fs.renameSync(temporary, file);
}

// Folds one install or uninstall into the previous receipt. Components that
// did not finish keep their earlier record, so a partial run never looks complete.
export function nextReceipt(previous: Receipt | undefined, run: Run, finished: Component[], keptIn: Set<Component>, homes: RuntimeHomes, tools?: Record<string, string>): Receipt {
  const records = { ...previous?.components };
  for (const name of finished) records[name] = { revision: run.revision, dirty: run.dirty, at: run.at, action: run.action, keptConflicts: keptIn.has(name) };
  const codex = new Set(previous?.runtimeHomes.codex), claude = new Set(previous?.runtimeHomes.claude);
  if (finished.includes('agents')) {
    if (run.action === 'install') { codex.add(homes.codex); claude.add(homes.claude); }
    else { codex.delete(homes.codex); claude.delete(homes.claude); }
  }
  if (finished.includes('skills') && run.action === 'install') claude.add(homes.claude);
  return { version: 1, lastRun: run, components: records, runtimeHomes: { codex: [...codex], claude: [...claude] }, tools };
}
