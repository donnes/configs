import * as p from '@clack/prompts';

export class Cancelled extends Error {}

export function canPrompt() {
  return Boolean(process.stdin.isTTY && process.stdout.isTTY);
}

export function answer<T>(value: T | typeof p.CANCEL_SYMBOL): T {
  if (p.isCancel(value)) {
    p.cancel('Operation cancelled.');
    throw new Cancelled();
  }
  return value;
}
