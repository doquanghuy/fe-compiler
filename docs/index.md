# Docs index

Navigation map for `fe-compiler-v1` docs. Read this first; pick
the right doc for your task.

FE today is a **partial rollout**: a single shipped step
(`screen_outline`) and no impacts files yet. The docs here are
intentionally smaller than the BE compiler's because the
surface is smaller. Future frontend steps land as sibling
bundles.

## Repo-local docs

- [`architecture.md`](architecture.md) — what this package is,
  how it fits into the `axcore-v1` framework, ownership boundary.
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

## Upstream references (axcore-v1)

- [`../../axcore-v1/docs/index.md`](../../axcore-v1/docs/index.md)
  — framework-level docs index.
- [`../../axcore-v1/docs/spec-kit-extension.md`](../../axcore-v1/docs/spec-kit-extension.md)
  — integration design source of truth.
- [`../../axcore-v1/docs/commands.md`](../../axcore-v1/docs/commands.md)
  — full shell command reference.
- [`../../axcore-v1/docs/conventions.md`](../../axcore-v1/docs/conventions.md)
  — coding rules + forbidden abstractions for any compiler
  package.
