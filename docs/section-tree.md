# `section_tree.yaml` — section structure for a step bundle

This document is the contract reference for the
`section_tree.yaml` file that may live inside a step bundle
directory. Code home is
[`src/fe_compiler/section_tree/__init__.py`](../src/fe_compiler/section_tree/__init__.py).

## What it is

`section_tree.yaml` is the **compiler-owned source of truth for a
step's primary-artifact section structure**. Each section has a
canonical id (e.g. `SCREEN_OUTLINE.LAYOUT`) and a display title;
ids nest hierarchically with a parent-prefix rule.

The kernel in `axcore` is intentionally domain-agnostic and
never parses compiler template prose. Section semantics belong to
the compiler. `section_tree.yaml` is how the compiler encodes
them so downstream layers (the validation spec, future
section-level stale support) can refer to sections by id rather
than by heading text.

## Where it lives

Inside the step bundle directory, alongside the existing files:

```
src/fe_compiler/bundles/flows/<step_id>/
    bundle.yaml
    section_tree.yaml         <-- here
    <step_id>.md              <-- template
    <step_id>_rules.md
    <step_id>_validate.json
```

The directory name (`<step_id>`) is the canonical step id and is
cross-checked against the file's `step_id` field at load time.

## Schema

Schema id: **`axcore.section-tree/v1`** (constant
`fe_compiler.section_tree.SECTION_TREE_SCHEMA`).

Locked v1 shape:

```yaml
schema: axcore.section-tree/v1
step_id: screen_outline

sections:
  - id: SCREEN_OUTLINE
    title: Screen outline
    children:
      - id: SCREEN_OUTLINE.LAYOUT
        title: Layout
      - id: SCREEN_OUTLINE.STATES
        title: States
```

Top-level keys are restricted to `schema`, `step_id`, `sections`.
Per-section keys are restricted to `id`, `title`, `children`.
Anything else is rejected at parse time.

## Section id rules

Locked grammar (constant `SECTION_ID_PATTERN`):

```
^[A-Z][A-Z0-9_]*(\.[A-Z][A-Z0-9_]*)*$
```

- Uppercase only; no spaces; dot-separated.
- Each segment starts with `A-Z` and may contain `A-Z`, `0-9`,
  `_`.
- A child id MUST be prefixed by its parent id plus a literal
  `.`. So `SCREEN_OUTLINE.LAYOUT` is a valid child of
  `SCREEN_OUTLINE`; `LAYOUT` is not.
- Ids are unique across the entire tree.
- `title` is display-only; `id` is the canonical identity.
- **Renaming an id is a breaking change.** Treat ids as stable
  contracts the same way you treat `step_id` or `plugin_id`.

## Template alignment via markers

Templates align to the tree using a deterministic, structured
marker (no fuzzy heading matching, no LLM):

```html
<!-- section: SCREEN_OUTLINE.LAYOUT -->
```

Markers can sit on their own line or appear inline; whitespace
around `section:` and the id is tolerated. The matcher is
`SECTION_MARKER_PATTERN`.

`validate_template_alignment(tree, template_text)` returns a list
of error strings (empty list ⇒ aligned) and reports three
deterministic failure classes:

1. A tree id that has no marker in the template.
2. A marker in the template that has no matching tree id.
3. Marker order in the template that does not match the tree's
   pre-order traversal (`tree.flat_ids`).

## Rollout status

Section trees are **optional today**. A step bundle without
`section_tree.yaml` works exactly as before; `load_section_tree`
returns `None`. Real FE templates pick up markers as part of the
section-level stale rollout — see the in-flight prompts for the
schedule. Adding a `section_tree.yaml` to an existing bundle is a
non-breaking change.

## Related: workflow-specific downstream impacts

The section tree describes the structure of *one* step's primary
artifact. Cross-step ("which sections of step X invalidate step
Y?") is the workflow-specific
[`section_impacts.<workflow_id>.yaml`](./section-impacts.md)
contract, which sits in the same bundle directory and references
section ids defined here.
