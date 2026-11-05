---
name: test-audit
description: Trigger this if the user says 'test audit'.
---

# Test audit

Find and delete low-signal tests. These tests check what the types already
guarantee, re-assert what their own mocks were told to return, only check that
something mounts, or repeat a stronger test of the same contract. They cost CI
time and review attention and catch nothing.

The goal is the same confidence for less CI time and code, not a deletion
count. Every deletion names its reason. Every contract worth keeping still has
a test that can fail. When unsure, keep.

## Scope

Use the scope the user names: a file, a package, or the whole repo. With no
scope, audit the whole repo. Read the repo's agent and contributor guidance
and its CI config first. Their testing rules override this skill.

## Delete

A test is low-signal when it:

- checks what the type checker already enforces, such as a field's presence,
  an object's shape, or a function's declared return type;
- asserts that a mock returned what the test told it to return, or was called
  with the arguments the test just passed in;
- only checks that a component renders, mounts, or has basic DOM, such as a
  button existing or a click handler firing;
- covers trivial logic: getters, constants, pass-through wrappers, re-exports;
- smoke-tests a path that a stronger test already covers;
- repeats another row of the same table, or another test of the same contract
  at a weaker boundary;
- waits on real timers or asserts wall-clock speed;
- compares against a copy of the source: copied fixtures, export lists,
  source greps;
- computes its expected value with the code under test;
- cannot fail: no assertion, a negative check that passes for an unrelated
  reason, or a name that promises more than the body checks.

## Keep

Keep a test when it is the only proof of:

- state, orchestration, or event-sourcing correctness;
- protocol translation, wire formats, and parsing of external formats;
- auth, permission, and scope guards, including expiry and rotation tested on
  a deterministic clock;
- persistence, migrations, and storage formats;
- public API, config, and default values;
- a fixed bug or race that could plausibly come back;
- call order, when the order is observable behavior.

A test that matches a delete pattern but is the only proof of a keep contract
stays. If its assertion is weak, fix it or move it to the real boundary. A test
that already fails on the default branch may be a product bug. Report it
instead of deleting it to get green.

## Steps

1. **Baseline.** On the default branch, run the test suites in scope with the
   project's runner. Record test count and wall time per package, using a JSON
   reporter when the runner has one, and list the tests that already fail.
2. **Sweep.** Read each test file in full, with the production code it covers.
   Judge a test by its assertions, not its name. Mark each test `keep`,
   `delete`, `merge` into a named stronger test or table, or `fix` when the
   contract matters but the assertion cannot fail. Each `delete` names its
   pattern and the test that still covers the contract, or says no contract
   exists. For a large scope, split the work by package or production area and
   give each part to a read-only subagent with the Delete and Keep lists. When a
   file's calls are uncertain, run a second independent pass on it and delete
   only what both passes mark.
3. **Cut.** Delete tests by title. For a large cut, script the edit on the
   syntax tree (the TypeScript compiler API for TypeScript) instead of editing
   by hand. Remove imports, helpers, fixtures, and test scripts left unused.
   Un-export or delete production code that only the deleted tests used; the
   project's unused-export check (knip or equivalent) finds it. That cleanup
   must not change production behavior. Update CI test lists, shard weights,
   and docs that name deleted files.
4. **Verify.** Run typecheck, lint, format, the unused-export check, and the
   affected tests. Rerun the baseline commands and compare counts and wall
   time. A failure that also happens on the baseline is not from the cut; say
   so in the report.
5. **Review.** Run `sol-review-loop` on the diff. Tell Sol the intent is
   deleting low-signal tests, and ask it to flag keep contracts that lost
   their only test. Restore those tests.
6. **Report.** Give the before and after table of tests and wall time per
   package, what each delete pattern removed, the tests you kept on purpose
   and why, production code removed, baseline failures, and what review
   restored. Commit and file a PR with `file-pr` only when the user asked, and
   put the same table in the description.
