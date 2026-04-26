# fe-compiler-v1

Frontend-domain compiler package for
[`axcore-v1`](https://example.invalid/axcore-v1). Sibling of
`be-compiler-v1`.

| Concern | Value |
| ------- | ----- |
| Distribution        | `fe-compiler-v1` |
| Importable package  | `fe_compiler` |
| Plugin id           | `fe` |
| Workflow            | `fe-pipeline-v1` |
| Step bundle         | `screen_outline` (single step today) |

`axcore-v1` discovers this package through the `axcore.plugins`
entry-point group. This package contributes one Spec Kit
workflow and one step bundle against the same
`speckit.axcore.step-run` SKILL that powers `be-compiler-v1`.

## Scope today (honestly partial)

One step: **`screen_outline`** — describes the UI screens /
navigation surface of the target system.

- No upstream consumption (entry step of `fe-pipeline-v1`).
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
depends on `fe-compiler-v1` and has the `axcore` Spec Kit
extension installed:

```bash
# from the app repo:
specify workflow run fe-pipeline-v1
```

Spec Kit dispatches the `/speckit-axcore-step-run` SKILL
(shipped by the `axcore` extension); the SKILL calls
`axcore.api.Kernel` against the bundles this package ships.

## Install (dev)

This package depends on `axcore-v1` via a `file://` direct
reference (see `pyproject.toml`). Sibling checkouts are expected
at `~/Desktop/axcore-v1`. Adjust the path if your layout differs.

```bash
pip install -e /path/to/fe-compiler-v1
```

`axcore-v1` picks the plugin up at runtime once it is
pip-installed in the active environment.

## Where to read next

- Docs index: [`docs/index.md`](docs/index.md).
- Agent context: [`CLAUDE.md`](CLAUDE.md).
- Full shell usage:
  [`../axcore-v1/docs/commands.md`](../axcore-v1/docs/commands.md).

## License

MIT — see [LICENSE](LICENSE).
