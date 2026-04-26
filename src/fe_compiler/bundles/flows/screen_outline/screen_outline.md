---
spec_id: SCREEN_OUTLINE-00
title: Frontend Screen Outline
status: active
version: 0.1.0
last_updated: YYYY-MM-DD-hh-mm-ss
---

<!-- section: SCREENS -->

[SECTION_START:SCREENS.OVERVIEW]
<!-- section: SCREENS.OVERVIEW -->
## 1. Overview

- <one-paragraph summary of the UI surface the system exposes>
- <intended user journey in one sentence>
[SECTION_END:SCREENS.OVERVIEW]

---

[SECTION_START:SCREENS.LIST]
<!-- section: SCREENS.LIST -->
## 2. Screens

Each screen carries a stable id (`SCR-NN`), a short name, and a
one-line purpose. The id order in this section is the logical
navigation order from entry point → primary flow → exit states.

- <SCR-01: short name — purpose>
- <SCR-02: short name — purpose>
[SECTION_END:SCREENS.LIST]

---

[SECTION_START:SCREENS.NAVIGATION]
<!-- section: SCREENS.NAVIGATION -->
## 3. Navigation

Edges between screens. Each edge uses the
`<SCR-NN → SCR-NN — trigger>` shape. Cycles are allowed (e.g. a
settings screen returning to its origin) and must be explicitly
called out.

- <SCR-NN → SCR-NN — trigger>
[SECTION_END:SCREENS.NAVIGATION]

---

[SECTION_START:SCREENS.COMPONENT_SURFACE]
<!-- section: SCREENS.COMPONENT_SURFACE -->
## 4. Component surface

The cross-screen components the frontend must render. Each
component lists the screens it appears on and the data it binds
to. Components that only live on one screen stay scoped to that
screen.

- <CMP-01: short name — screens: SCR-NN, SCR-NN — bound data>
[SECTION_END:SCREENS.COMPONENT_SURFACE]
