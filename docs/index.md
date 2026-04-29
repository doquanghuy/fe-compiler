# Docs index

Navigation map for `fe-compiler` docs. Read this first; pick
the right doc for your task.

FE today is a **partial rollout**: a single shipped step
(`screen_outline`) and no impacts files yet. The docs here are
intentionally smaller than the BE compiler's because the
surface is smaller. Future frontend steps land as sibling
bundles.

## Repo-local docs

- [`architecture.md`](architecture.md) — what this package is,
  how it fits into the `axcore` framework, ownership boundary.
- [`section-tree.md`](section-tree.md) — `section_tree.yaml`
  contract for the `screen_outline` bundle (compiler-owned
  canonical section structure).
- [`section-impacts.md`](section-impacts.md) — section-impacts
  contract; documents the empty ledger today and the
  expansion path.

## Common tasks

| If you want to… | Read… |
| --------------- | ----- |
| Understand the package's role | `architecture.md` |
| Add or edit the section tree | `section-tree.md` |
| Add an impacts file when a second step lands | `section-impacts.md` |
| See repo-brain rules | `../CLAUDE.md` |

## Upstream references (axcore)

- [`../../axcore/docs/index.md`](../../axcore/docs/index.md)
  — framework-level docs index.
- [`../../axcore/docs/spec-kit-extension.md`](../../axcore/docs/spec-kit-extension.md)
  — integration design source of truth.
- [`../../axcore/docs/commands.md`](../../axcore/docs/commands.md)
  — full shell command reference.
- [`../../axcore/docs/conventions.md`](../../axcore/docs/conventions.md)
  — coding rules + forbidden abstractions for any compiler
  package.
