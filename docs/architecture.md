# Architecture

`fe-compiler` is the **frontend-domain compiler package** for the
[`axcore`](https://github.com/doquanghuy/axcore) framework. It
contributes frontend-domain content — plugin manifest, workflow,
and one step bundle — not a runtime.

**It is not a runtime.** The user-facing runtime is **Spec Kit**;
per-step enrichment is handled by the `axcore` Spec Kit extension
calling `axcore.api.Kernel`. See
[`axcore/docs/spec-kit-extension.md`](../../axcore/docs/spec-kit-extension.md)
for the locked integration design.

## Identity

- **Distribution:** `fe-compiler`.
- **Importable package:** `fe_compiler`.
- **Plugin id:** `fe`.
- **Framework dependency:** `axcore`.
- **Workflow id:** `fe-pipeline` (Spec Kit `schema_version:
  "1.0"`).
- **Step bundle shipped:** `screen_outline` — describes UI screens
  / navigation surface.

## Layer model

```
┌──────────────────────────────────────────────────┐
│                   End user                        │
│     $ specify workflow run fe-pipeline        │
└─────────────────────▲────────────────────────────┘
                      │
┌─────────────────────┴────────────────────────────┐
│                  Spec Kit                        │  ← primary orchestration / entry point
└─────────────────────▲────────────────────────────┘
                      │ SKILL dispatch for axcore.* commands
┌─────────────────────┴────────────────────────────┐
│        `axcore` Spec Kit extension               │  ← shipped by axcore
└─────────────────────▲────────────────────────────┘
                      │ axcore.api.Kernel
┌─────────────────────┴────────────────────────────┐
│                   axcore                         │
│   (kernel, plugin contract, public API)          │
└─────────────────────▲────────────────────────────┘
                      │ discovers this package via axcore.plugins entry point
┌─────────────────────┴────────────────────────────┐
│              fe-compiler                         │  ← THIS REPO
│                                                  │
│  - plugin manifest (plugin.yaml)                 │
│  - frontend workflow YAML (Spec Kit v1.0)        │
│  - one step bundle: screen_outline               │
└──────────────────────────────────────────────────┘
```

## What this repo owns

- **Plugin identity.** `plugin_id: fe` declared in
  `src/fe_compiler/plugin/plugin.yaml` and exposed via the
  `axcore.plugins` entry-point group (entry-point name `fe`).
- **Frontend workflow.** `src/fe_compiler/workflows/fe_pipeline.yaml`,
  Spec Kit `schema_version: "1.0"`. Action steps dispatch the
  `speckit.axcore.step-run` SKILL shipped by the `axcore`
  extension.
- **Step bundle.** `src/fe_compiler/bundles/flows/screen_outline/`
  — `bundle.yaml` + template + rules + validation_spec. No
  upstream consumption (entry step of the pipeline); one primary
  artifact (Markdown).

Future frontend steps (component surface, routing surface, state
model) land as sibling bundles under
`src/fe_compiler/bundles/flows/`.

## What this repo does *not* own

- **The primary runtime shell.** Spec Kit is the user-facing
  entry point.
- **Generic orchestration.** Workflow execution, gates,
  pause/resume, and run state are owned by Spec Kit.
- **The `axcore.*` command handlers.** Those are SKILLs shipped
  by the `axcore` Spec Kit extension.
- **The per-step enrichment kernel.** `axcore.kernel` owns that.
  This repo supplies *inputs* (bundle + validator hooks) to the
  kernel; it does not run it.
- **The plugin and bundle contracts.** Schemas live in
  `axcore/schemas/`.
- **Anything in common with `be-compiler`.** There is no
  cross-compiler dependency. The two packages share `axcore`
  and nothing else.

## Dependency wiring

- `pyproject.toml` declares `axcore` as a runtime dependency.
- `pyproject.toml` registers one entry point under
  `axcore.plugins` with name `fe` pointing at
  `fe_compiler.plugin.entry:FeCompilerPlugin`.
- At runtime, `axcore`'s `PluginRegistry.discover()` enumerates
  the entry-point group, instantiates each `Plugin` subclass,
  loads each plugin's `plugin.yaml`, cross-checks that `plugin_id`
  matches `metadata.name`, and registers it.

## Internal step design — phases, not workflows

When a step runs, the framework's kernel walks a small linear
**phase plan** internally:

1. `load_inputs`
2. `build_generation_context`
3. `validate_artifact`
4. `build_repair_context`
5. `improve_artifact`
6. `persist_artifact`

These are Python callables with a fixed order owned by the
framework. This repo does not define phases.

## Import rule

Plugin code MUST import only from `axcore.api`:

```python
from axcore.api import (
    Kernel, StepResult, WorkflowDefinition,
    Plugin, PluginMetadata, PluginRegistry,
    PLUGIN_ENTRY_POINT_GROUP, ManifestError, PluginLoadError,
    ValidationFinding, ValidationResult,
)
```

Anything else under `axcore.*` is internal and may change
without notice.

## Dev loop

Requires **Python 3.11+** and an installable `axcore`.

```bash
git clone <repo-url> fe-compiler
cd fe-compiler

python -m venv .venv
source .venv/bin/activate

pip install -e ../axcore          # if sibling checkout
make dev-install                  # install + pre-commit
make check                        # lint + typecheck + tests (CI gate)
```

End users run the pipeline through Spec Kit:

```bash
specify workflow run fe-pipeline
```

Spec Kit dispatches `/speckit-axcore-step-run`; the SKILL calls
`axcore.api.Kernel` against the step bundles this package ships.
See [`axcore/docs/commands.md`](../../axcore/docs/commands.md)
for full shell usage.
