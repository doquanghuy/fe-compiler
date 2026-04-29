"""Developer CLI for ``fe-compiler``.

Thin wrapper: exposes ``fe-compiler --version`` so plugin authors
can verify the installed distribution quickly. The user-facing
runtime is Spec Kit (``specify workflow run fe-pipeline-v1``) —
this CLI deliberately does not try to reimplement orchestration
or drive steps directly.
"""

from __future__ import annotations

import argparse
import sys

from fe_compiler import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fe-compiler",
        description=(
            "Developer CLI for fe-compiler. End users run pipelines "
            "through Spec Kit; this CLI only exposes package introspection."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"fe-compiler {__version__}",
    )
    parser.parse_args(argv)
    # No subcommands today; argparse --version exits with 0 before this line.
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
