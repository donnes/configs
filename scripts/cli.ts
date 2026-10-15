import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';
import { parseArgs } from 'node:util';
import * as p from '@clack/prompts';
import { Files } from './lib/files.ts';
import { Health } from './lib/health.ts';
import { available, components, detectProfile, Installer, type Component } from './lib/install.ts';
import { answer, Cancelled, canPrompt } from './lib/prompts.ts';

const help = `Usage:
  ./cli --interactive
  ./cli [install | uninstall] [--dry-run] [--skip COMPONENT]... [--only COMPONENT]...
  ./cli [--dry-run] adopt <path>
  ./cli [--dry-run] update <path>
  ./cli [--dry-run] remove-skill [name...]
  ./cli health

Options:
  --dry-run          Preview changes without modifying managed files.
  -i, --interactive  Choose components with Clack prompts.
  --skip COMPONENT   Skip a component. May be repeated.
  --only COMPONENT   Select only a component. May be repeated.
  --skip-packages    Alias for --skip packages.
  --list-components  List selectable components and exit.
  -h, --help         Show this help.

health checks this machine against the repository for its detected OS:
managed files, packages, mise tools and their resolution in a new shell,
leftover version managers, and background jobs. It changes nothing and
exits 1 when a check fails.

Components:
  ${components.join(' ')}
  command-center is opt-in when installing; default uninstall includes it.
  rea is opt-in and leaves integrations intact on uninstall.
`;

async function main() {
  const { values, positionals } = parseArgs({
    allowPositionals: true,
    options: {
      'dry-run': { type: 'boolean' }, interactive: { type: 'boolean', short: 'i' },
      skip: { type: 'string', multiple: true }, only: { type: 'string', multiple: true },
      'skip-packages': { type: 'boolean' }, 'list-components': { type: 'boolean' },
      help: { type: 'boolean', short: 'h' },
    },
  });
  if (values.help) { console.log(help); return; }
  if (values['list-components']) { console.log(components.join('\n')); return; }
  const action = positionals[0] ?? 'install';
  if (!['install', 'uninstall', 'adopt', 'update', 'remove-skill', 'health'].includes(action)) throw new Error(`unknown command: ${action}`);
  const args = positionals.slice(1);
  if (['install', 'uninstall', 'health'].includes(action) && args.length) throw new Error(`unexpected argument: ${args[0]}`);
  if (['adopt', 'update'].includes(action) && args.length !== 1) throw new Error(`${action} requires exactly one path`);
  function selection(names: string[]): Component[] {
    return names.flatMap(name => name.split(',')).map(name => {
      const component = components.find(component => component === name);
      if (!component) throw new Error(`unknown component: ${name} (use --list-components)`);
      return component;
    });
  }
  const skip = selection([...(values.skip ?? []), ...(values['skip-packages'] ? ['packages'] : [])]);
  const only = selection(values.only ?? []);
  if (skip.length && only.length) throw new Error('--skip and --only cannot be used together');
  if (values.interactive && (skip.length || only.length)) throw new Error('--interactive cannot be combined with --skip, --only, or --skip-packages');
  if (!['install', 'uninstall'].includes(action) && (skip.length || only.length)) throw new Error('--skip and --only apply only to install and uninstall');
  if (values.interactive && ['adopt', 'update', 'health'].includes(action)) throw new Error('--interactive applies only to install, uninstall, and remove-skill');
  if (values['dry-run'] && action === 'health') throw new Error('health never changes anything; run it without --dry-run');
  const profile = detectProfile();
  const defaults = components.filter(component => component !== 'rea' && (action === 'uninstall' || component !== 'command-center'));
  let enabled = new Set<Component>((only.length ? only : defaults).filter(component => !skip.includes(component)));
  if (values.interactive && ['install', 'uninstall'].includes(action)) {
    if (!canPrompt()) throw new Error('interactive mode requires a terminal');
    p.intro(`donnes · ${action} · ${profile}`);
    enabled = new Set(answer(await p.multiselect({
      message: `Select components to ${action}`,
      options: available(profile).map(value => ({ value, label: value })),
      initialValues: defaults.filter(component => available(profile).includes(component)),
      required: false,
    })));
  }
  const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  if (action === 'health') {
    if (!await new Health(repo, homedir(), profile).run()) process.exitCode = 1;
    return;
  }
  const installer = new Installer(new Files(repo, homedir(), Boolean(values['dry-run'])), profile, enabled);
  if (action === 'install' || action === 'uninstall') {
    console.log(`Profile: ${profile}\nRepo:    ${repo}\n`);
    await installer.apply(action === 'uninstall');
  }
  else if (action === 'remove-skill') await installer.skills.remove(args);
  else {
    const input = args[0];
    if (input === undefined) throw new Error(`${action} requires a path`);
    await installer.importPath(input, action === 'update');
  }
  if (values.interactive && ['install', 'uninstall'].includes(action)) p.outro(values['dry-run'] ? 'Preview complete. No managed files changed.' : 'Done.');
}

try {
  await main();
} catch (error) {
  if (error instanceof Cancelled) process.exitCode = 130;
  else {
    console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 1;
  }
}
