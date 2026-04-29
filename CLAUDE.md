# CLAUDE.md — fe-compiler agent context

## Repo identity

`fe-compiler` is a **frontend-domain compiler package**
consumed by `axcore` via the `axcore.plugins` entry-point
group. It is not a framework; it ships plugin + workflow + one
step bundle.

Plugin id: **`fe`**. Importable: `fe_compiler`. Distribution:
`fe-compiler`. Sibling: `be-compiler` (plugin id `be`).
Both depend on `axcore` and import only from `axcore.api`.

This repo is a **compiler/plugin source package**. NOT the
workflow runtime home — workflow runs happen in an **app repo**
(e.g. `idea-engine`) where Spec Kit + the `axcore` extension +
this package are installed.

FE today is a **partial rollout**: a single shipped step
(`screen_outline`), no impacts files, ledger-locked. Future
frontend steps land as sibling bundles.

## Fast resume

1. **Read `docs/index.md` first.** It maps the docs tree.
2. Framework conventions live upstream in
   [`../axcore/docs/conventions.md`](../axcore/docs/conventions.md).
3. Never assume — verify against source.

## Audit + debt tracking

This repo currently has no `docs/audit.md` or `docs/tech-debt.md`.
Audit work for the four-repo system is tracked in
[`../axcore/docs/audit.md`](../axcore/docs/audit.md). Add
files here only if/when this repo accumulates its own audit log
or unresolved gaps; follow the same rules:

- `docs/audit.md`: audit reports ONLY. Append entries at the
  **top** with full timestamp `YYYY-MM-DD HH:MM:SS`. Do not
  write here from feature/fix prompts.
- `docs/tech-debt.md`: current-state debt only. No chronology,
  no timestamps. Update to reflect right now. Remove fixed items.

## Architectural truth (load-bearing)

1. **This repo is a plugin/domain package.** It *consumes* the
   `axcore` framework; it does not re-implement it. Primary
   shell is **Spec Kit**.
2. **Plugins import only from `axcore.api`.** Reaching into
   `axcore.kernel.*` is a layering violation.
3. **Workflow YAML owns orchestration only.** Topology, gates,
   switches, fan-out/fan-in. No per-step execution semantics in
   workflow files.
4. **Bundle config owns step semantics.** Resources, validation,
   required_inputs, outputs, retry policy.
5. **No mini-runtime drift.** This package does not ship a
   runtime; it ships declarations.
6. **No phase / prompt / sprint / step / task identifiers anywhere** —
   in code, comments, docstrings, YAML comments, file names, or test names.
   Examples of what is forbidden: `Phase 9`, `Step 39`, `Prompt 13.2`,
   `Task 7`. Name responsibilities and architecture, not implementation moments.

## What this package must never do

- Reimplement orchestration.
- Add workflow-level gate/switch/fan-out primitives.
- Own Spec Kit extension files for the `axcore.*` namespace.
- Depend on `be-compiler`.
- Install `axcore` as a git dependency.

## Mandatory post-change validation

```bash
make fix        # ruff check . --fix && ruff format .
make typecheck  # pyright (basic mode, py3.11 target)
make test       # only if you touched tested code
```

Skip only for docs-only / YAML-only / repo-metadata-only changes.

## Completion rule

1. Implement the change.
2. `make fix` until clean.
3. `make typecheck` until clean.
4. `make test` if you touched tested code.
5. Summarize files changed and stop.

**Never commit, branch, tag, or push without an explicit user
request.**
