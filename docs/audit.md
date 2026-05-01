# Audit reports

Append entries at the **top** with full timestamp `YYYY-MM-DD HH:MM:SS`.
One entry per audit run.

---

## 2026-05-01 23:30:00 — fe-compiler v0.1.1 release audit

### Verdict

**RELEASED — fe-compiler v0.1.1 GitHub Release is live and verified**

---

### Release identity

| Field | Value |
|---|---|
| Package | `fe-compiler` |
| Version | `0.1.1` |
| Tag | `v0.1.1` |
| Tag commit | `3795f61515a62ec9d86bffd631e1cc2d2d04a8a5` |
| Release URL | https://github.com/doquanghuy/fe-compiler/releases/tag/v0.1.1 |
| Is draft | No |
| Is prerelease | No |
| Distribution | GitHub Releases only |
| PyPI | Not published |
| Private registry | Not published |

---

### Assets

| Asset | Size | SHA-256 |
|---|---|---|
| `fe_compiler-0.1.1-py3-none-any.whl` | 29,011 bytes | `741ab1752cc6b41185e123d1ea5a02e306678124eb5a85717e23f9bbb79c179b` |
| `fe_compiler-0.1.1.tar.gz` | 28,361 bytes | `284e13845e8edea3a1a57910770286923fbe823209d82481e62b0e8809a34363` |

---

### Gate results

| Gate | Result |
|---|---|
| `make fix` | PASS — 23 files unchanged |
| `make typecheck` | PASS — 0 errors |
| `make test` | PASS — 135 passed, 4 skipped |
| Install from release wheel | PASS — `fe_compiler.__version__ == "0.1.1"` |

---

### Version bump scope

`pyproject.toml`, `src/fe_compiler/__init__.py`, `src/fe_compiler/plugin/plugin.yaml`,
`src/fe_compiler/workflows/fe_pipeline.yaml`, 2 test files.

axcore compatibility range `>=0.1.0,<0.2.0` unchanged — already accepts `0.1.1`.

---

### Commits since v0.1.0 (4)

- `e9e9544` Update GitHub Actions versions
- `d085358` Install axcore release wheel in CI
- `06aa175` Fix screen outline validation assertions
- `b17e532` Clean up package license metadata

---

### No live AI / no PyPI / no Spec Kit patching

No AI provider called. No `specify workflow run` executed. No PyPI publish. No Spec Kit
patches applied.

### v0.1.0 immutability

The `v0.1.0` tag and GitHub Release were not touched.
