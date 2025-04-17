#!/usr/bin/env python3
"""
code2md.py – Generate a single Markdown file that captures the full context
of a code base (or single file) for AI assistants.

Author: 2025‑04‑17
"""

from __future__ import annotations

import argparse
import datetime as _dt
import mimetypes
import sys
from pathlib import Path
from textwrap import indent

try:
    import pyperclip
except ImportError:  # graceful degradation
    pyperclip = None  # type: ignore

try:
    import pathspec
except ImportError:
    print("ERROR: The 'pathspec' package is required.  pip install pathspec", file=sys.stderr)
    sys.exit(1)

# ---------- Defaults ---------------------------------------------------------

DEFAULT_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode",
    "node_modules", "__pycache__", "build", "dist", ".mypy_cache",
    ".venv"
}

DEFAULT_EXCLUDE_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico",
    ".mp4", ".mp3", ".zip", ".tar", ".gz", ".exe", ".dll",
    ".class", ".o", ".so", ".pdf",
}

DEFAULT_IGNORE_FILES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.test",
    ".env.test.local",
    ".env.test.local",
}

LANG_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".md": "markdown",
    ".sh": "bash",
    ".rb": "ruby",
    ".go": "go",
    ".rs": "rust",
    ".sql": "sql",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
}

# ---------- Helpers ----------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="code2md",
        description="Turn a directory/tree or a single file into a share‑ready Markdown document."
    )
    p.add_argument("path", type=Path, help="Root directory or file to snapshot")
    p.add_argument("-o", "--output", type=Path, help="Write markdown to this file")
    p.add_argument("--no-clip", action="store_true", help="Do NOT copy markdown to clipboard")
    p.add_argument("--show-tree/--no-tree", dest="show_tree", default=True, action=argparse.BooleanOptionalAction,
                   help="Include (or omit) the directory tree visual")
    p.add_argument("--include-ext", nargs="*", default=[],
                   help="Extra file extensions to FORCE include (e.g. .sql .graphql)")
    p.add_argument("--exclude-ext", nargs="*", default=[],
                   help="Extra file extensions to exclude")
    p.add_argument("--ignore-pattern", nargs="*", default=[],
                   help="Add .gitignore‑style patterns to exclude")
    p.add_argument("--extra-file", nargs="*", default=[],
                   help="Additional individual files to include even if normally ignored")
    return p


def compile_ignore_spec(patterns: list[str]) -> pathspec.PathSpec:
    """Compile patterns (gitwildmatch style) using pathspec."""
    return pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, patterns)


def is_binary(path: Path) -> bool:
    """Rudimentary binary detector based on MIME type."""
    mime, _ = mimetypes.guess_type(path.as_posix(), strict=False)
    return mime is not None and (
        mime.startswith("image/") or mime.startswith("video/") or mime.startswith("audio/")
    )


def generate_tree(root: Path, ignore: pathspec.PathSpec) -> str:
    """Return an ASCII tree of the directory, honouring ignore rules."""
    lines: list[str] = []

    def _walk(current: Path, prefix: str = "") -> None:
        entries = sorted([e for e in current.iterdir()
                          if not ignore.match_file(e.relative_to(root).as_posix())],
                         key=lambda p: (p.is_file(), p.name.lower()))
        for i, entry in enumerate(entries):
            connector = "└── " if i == len(entries) - 1 else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                extension = "    " if i == len(entries) - 1 else "│   "
                _walk(entry, prefix + extension)

    lines.append(root.name)
    _walk(root)
    return "\n".join(lines)


def language_tag(path: Path) -> str:
    return LANG_MAP.get(path.suffix.lower(), "")


def should_include(path: Path,
                   ignore: pathspec.PathSpec,
                   include_ext: set[str],
                   exclude_ext: set[str],
                   extra_files: set[Path]) -> bool:
    rel = path.relative_to(path.anchor)
    if path in extra_files:
        return True
    if ignore.match_file(rel.as_posix()):
        return False
    if path.is_dir():
        return True
    if is_binary(path):
        return False
    ext = path.suffix.lower()
    if ext in exclude_ext:
        return False
    if ext in include_ext:
        return True
    # keep if ext is source‑like
    return ext not in DEFAULT_EXCLUDE_EXTS


def snapshot(root: Path,
             show_tree: bool,
             ignore: pathspec.PathSpec,
             include_ext: set[str],
             exclude_ext: set[str],
             extra_files: set[Path]) -> str:
    """Build the full markdown text."""
    now = _dt.datetime.now().isoformat(timespec="seconds")
    md: list[str] = [
        f"# Project snapshot: **{root.resolve().name}**",
        f"*Generated {now} by `code2md.py`*",
        ""
    ]

    if show_tree:
        md += ["## Directory structure", "```", generate_tree(root, ignore), "```", ""]

    md.append("## Source files\n")

    for p in sorted(root.rglob("*")):
        if not should_include(p, ignore, include_ext, exclude_ext, extra_files):
            continue
        if p.is_file():
            tag = language_tag(p)
            rel = p.relative_to(root)
            md += [f"### `{rel}`", f"```{tag}"]
            try:
                md.append(p.read_text(errors="replace"))
            except Exception as ex:
                md.append(f":warning: *Could not read file – {ex}*")
            md.append("```\n")

    return "\n".join(md)


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    root = args.path.expanduser().resolve()
    if not root.exists():
        print(f"ERROR: Path {root} does not exist.", file=sys.stderr)
        sys.exit(2)

    ignore_patterns = (
        list(DEFAULT_EXCLUDE_DIRS)           # directories
        + list(DEFAULT_IGNORE_FILES)         # files
        + args.ignore_pattern                # user‑supplied
    )
    ignore_spec = compile_ignore_spec(ignore_patterns)

    include_ext = {e.lower() for e in args.include_ext}
    exclude_ext = {e.lower() for e in (DEFAULT_EXCLUDE_EXTS | set(args.exclude_ext))}
    extra_files = {Path(f).expanduser().resolve() for f in args.extra_file}

    markdown = snapshot(
        root,
        show_tree=args.show_tree,
        ignore=ignore_spec,
        include_ext=include_ext,
        exclude_ext=exclude_ext,
        extra_files=extra_files,
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")
        print(f"Wrote snapshot to {args.output}")

    if not args.no_clip and pyperclip:
        pyperclip.copy(markdown)
        print("Copied snapshot to clipboard.")
    elif args.no_clip:
        print("Clipboard copy disabled (--no-clip).")
    elif not pyperclip:
        print("pyperclip not installed; skipped clipboard copy.", file=sys.stderr)


if __name__ == "__main__":
    main()
