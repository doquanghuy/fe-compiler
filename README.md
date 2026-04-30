# fe-compiler

Frontend-domain compiler package for
[`axcore`](https://example.invalid/axcore). Sibling of
`be-compiler`.

| Concern | Value |
| ------- | ----- |
| Distribution        | `fe-compiler` |
| Importable package  | `fe_compiler` |
| Plugin id           | `fe` |
| Workflow            | `fe-pipeline` |
| Step bundle         | `screen_outline` (single step today) |

`axcore` discovers this package through the `axcore.plugins`
entry-point group. This package contributes one Spec Kit
workflow and one step bundle. Spec Kit dispatches the mode-specific
axcore SKILLs (`speckit.axcore.step-run-fast`, `-review`, `-strict`)
for each action step, the same commands that power `be-compiler`.

## Scope today (honestly partial)

One step: **`screen_outline`** — describes the UI screens /
navigation surface of the target system.

- No upstream consumption (entry step of `fe-pipeline`).
- Single primary artifact (Markdown, `text/markdown`).
- Deterministic validation — required sections, unresolved
  placeholders, section-marker integrity.

Future frontend steps (component surface, routing surface,
state model) land as sibling bundles under
`src/fe_compiler/bundles/flows/`.

## What this is not

- Not a front-end framework.
- Not a UI renderer.
- Not an alternative orchestration engine.
- Not a Spec Kit extension — it is a *consumer* of the `axcore`
  Spec Kit extension.

## Where end users actually run this

End users do NOT run workflow commands from this repo. This
repo is a compiler/plugin package — workflows defined here are
consumed from an **app repo** (e.g.
[`idea-engine`](https://example.invalid/idea-engine)) that
depends on `fe-compiler` and has the `axcore` Spec Kit
extension installed:

```bash
# from the app repo:
specify workflow run fe-pipeline
```

Spec Kit dispatches the mode-specific SKILL for each action step
(`speckit.axcore.step-run-fast`, `speckit.axcore.step-run-review`,
or `speckit.axcore.step-run-strict`, depending on `quality_mode`),
shipped by the `axcore` extension; each SKILL calls
`axcore.api.Kernel` against the bundles this package ships.

## Install (dev)

This package depends on `axcore` via a `file://` direct
reference (see `pyproject.toml`). Sibling checkouts are expected
at `~/Desktop/axcore`. Adjust the path if your layout differs.

```bash
pip install -e /path/to/fe-compiler
```

`axcore` picks the plugin up at runtime once it is
pip-installed in the active environment.

## Where to read next

- Docs index: [`docs/index.md`](docs/index.md).
- Agent context: [`CLAUDE.md`](CLAUDE.md).
- Full shell usage:
  [`../axcore/docs/commands.md`](../axcore/docs/commands.md).

## License

MIT — see [LICENSE](LICENSE).
