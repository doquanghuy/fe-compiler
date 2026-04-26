# `section_impacts.<workflow_id>.yaml` — workflow-specific downstream impacts

This document is the contract reference for the
`section_impacts.<workflow_id>.yaml` file that may live inside a
step bundle directory. Code home is
[`src/fe_compiler/section_impacts/__init__.py`](../src/fe_compiler/section_impacts/__init__.py).
Pairs with the per-step section structure described in
[`section-tree.md`](./section-tree.md).

## What it is

`section_impacts.<workflow_id>.yaml` is the **compiler-owned,
workflow-specific declaration** of which downstream steps (and
which sections within them) are invalidated when a given upstream
section changes.

The kernel in `axcore-v1` is intentionally domain-agnostic — it
neither infers nor authors impact relationships. The compiler owns
the file, declares the cross-step dependency edges
deterministically, and ships the file inside the step bundle. No
prose inference, no fuzzy matching, no LLM.

## Where it lives

Inside the step bundle directory, alongside `bundle.yaml`,
`section_tree.yaml`, the template, the rules, and the validation
spec:

```
src/fe_compiler/bundles/flows/<step_id>/
    bundle.yaml
    section_tree.yaml
    section_impacts.<workflow_id>.yaml   <-- here
    <step_id>.md
    <step_id>_rules.md
    <step_id>_validate.json
```

The directory name (`<step_id>`) is the canonical step id and is
cross-checked against the file's `step_id` field at load time. The
filename's embedded `<workflow_id>` is cross-checked against the
file's `workflow_id` field — disagreement is a hard error
(`SectionImpactsError`).

## Workflow-specific by design

A step may participate in multiple workflows. Each participating
workflow gets *its own* impacts file:

```
bundles/flows/screen_outline/
    section_impacts.fe-pipeline-v1.yaml
    section_impacts.fe-design-refresh-v1.yaml
```

A step that participates in workflow `X` but has no current
downstream impact in `X` may either omit the file or ship it with
`impacts: []` (an explicit "no impacts today" declaration is
preferable to silence). Both are valid.

The filename is the only way the contract knows which workflow a
file belongs to — there is no alternate naming, no folder layout,
no manifest. `section_impacts.<workflow_id>.yaml` is the locked
shape; the workflow id segment must match the Spec Kit
workflow-id grammar (lowercase alphanumeric + hyphens).

## Schema

Schema id: **`axcore.section-impacts/v1`** (constant
`fe_compiler.section_impacts.SECTION_IMPACTS_SCHEMA`).

Locked v1 shape:

```yaml
schema: axcore.section-impacts/v1
workflow_id: fe-pipeline-v1
step_id: screen_outline

impacts:
  - from_section: SCREEN_OUTLINE.LAYOUT
    to:
      - step_id: component_design
        target: section
        section_ids:
          - COMPONENT.LIST
      - step_id: state_design
        target: subtree
        section_ids:
          - STATE.MODELS
      - step_id: integration_summary
        target: artifact
```

Top-level keys are restricted to `schema`, `workflow_id`,
`step_id`, `impacts`. Each `impacts` entry has exactly two keys:
`from_section` and `to`. Each `to` entry has `step_id`, `target`,
and — for `section` / `subtree` modes — `section_ids`. Anything
else is rejected at parse time.

## The three target modes

The complete, closed set of target modes is locked at:

| Mode       | Semantics                                                    | `section_ids`            |
| ---------- | ------------------------------------------------------------ | ------------------------ |
| `section`  | Only the listed downstream section ids are impacted.         | Required, non-empty.     |
| `subtree`  | The listed downstream section ids **plus all descendants**.  | Required, non-empty.     |
| `artifact` | The entire downstream artifact / step is impacted.           | **Forbidden** — omit.    |

`SECTION_IMPACT_TARGET_MODES` exports this set as a `frozenset`
for callers that want to enumerate or assert membership.
Wildcards, regexes, and pattern modes are out of scope by design;
v1 is deterministic enumeration only.

## Cross-file alignment rules

Three deterministic checks. The first is intra-file (run by
`parse_section_impacts`); the other two are cross-file (run by
the explicit `validate_against_*` functions).

1. **Filename ⇄ content.** The workflow id embedded in the
   filename must equal the file's `workflow_id` field; the bundle
   directory name must equal the file's `step_id` field. Enforced
   by `load_section_impacts` and `load_all_section_impacts` via
   the parser's `expected_*` arguments.

2. **Workflow scope** (`validate_against_workflow`). Both the
   owning `step_id` and every `to.step_id` referenced must be
   members of the workflow's step set. An impacts file may not
   reach outside its own workflow.

3. **Section-tree alignment**
   (`validate_against_section_trees`). Every `from_section` must
   be in the owning step's section tree. Every downstream
   `section_ids` entry (for `target='section'` and
   `target='subtree'`) must be in that downstream step's section
   tree.

Both cross-file functions return an error list (empty ⇒ valid)
rather than raising, so a single validation pass surfaces all
problems at once.

## Downstream-no-tree rule

A downstream step is allowed to ship without a `section_tree.yaml`
(section trees are themselves optional). When that is the case,
only `target='artifact'` is meaningful — there are no sections to
target. `validate_against_section_trees` enforces this:

- `target='artifact'` against a tree-less downstream → allowed.
- `target='section'` or `target='subtree'` against a tree-less
  downstream → hard error.

Callers thread the downstream tree map as
`{step_id: SectionTree | None}`; `None` means "no
`section_tree.yaml` in that bundle".

## Optionality

Impacts files are **optional today**:

- A step with no `section_impacts.<workflow_id>.yaml` for a given
  workflow is valid (terminal step, or no current cross-step
  impact in that workflow). `load_section_impacts` returns `None`.
- A step may have impacts files for some workflows it participates
  in but not others.
- An impacts file with `impacts: []` is valid (formal opt-in with
  no current downstream impact).

Adding a `section_impacts.<workflow_id>.yaml` to an existing
bundle is a non-breaking change. Real FE bundles pick up impact
files as part of the section-level stale rollout — see the
in-flight prompts for the schedule.
