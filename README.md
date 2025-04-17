# code2md

`code2md.py` is a single‑file CLI that snapshots any folder (or single source file) into a **self‑contained Markdown document**. The output contains a compact directory tree and the fully syntax‑highlighted text of every relevant code file, ready to paste into ChatGPT, Claude, or your favourite issue tracker.

It relies on two light dependencies—**pathspec** (for `.gitignore`‑style rules) and **pyperclip** (for cross‑platform clipboard access).

---

## ✨ Features

* **Zero‑config ignore rules** — understands common junk (`.git`, `__pycache__`, build artefacts) and honours additional `.gitignore`‑style patterns via **pathspec**.
* **ASCII tree preview** — readable Unicode tree at the top of the snapshot so you see project structure at a glance.
* **Syntax‑highlighted fences** — each file is wrapped in a ```language fenced block; GitHub & VS Code highlight automatically.
* **One‑line clipboard export** — the full Markdown is copied to your clipboard (macOS, Linux, Windows) through **pyperclip**.
* **Highly customisable** — flags for `--ignore-pattern`, `--include-ext`, `--exclude-ext`, and `--extra-file` let you fine‑tune what lands in the snapshot.
* **Python ≥ 3.9** — uses `argparse.BooleanOptionalAction` so you get pairs like `--show-tree / --no-tree`.
* **MIT‑licensed** — permissive, simple, business‑friendly.

---

## 🚀 Quick start

```bash
# 1 ▸ install (requires Python 3.9+)
python -m pip install pathspec pyperclip

# 2 ▸ snapshot your repo and copy to clipboard
python code2md.py .

# 3 ▸ write to README_CONTEXT.md instead, no clipboard
python code2md.py . -o README_CONTEXT.md --no-clip
```

### Common recipes

```bash
# Skip tests & migrations, but keep SQL
python code2md.py my_project \
  --ignore-pattern "tests/**" "*/migrations/*" \
  --include-ext .sql

# Snapshot a single helper file without the tree section
python code2md.py src/utils/helpers.py --no-tree
```

---

## 🛠  Command‑line reference

```
positional arguments:
  path                  directory or file to snapshot

optional arguments:
  -o, --output FILE     write markdown here instead of stdout/clipboard
  --no-clip             disable clipboard copy
  --show-tree / --no-tree
                        turn the ASCII tree on or off (default on)
  --include-ext EXT [EXT ...]
                        extra extensions to force‑include (e.g. .sql)
  --exclude-ext EXT [EXT ...]
                        extra extensions to ignore
  --ignore-pattern PATTERN [PATTERN ...]
                        additional .gitignore‑style excludes
  --extra-file PATH [PATH ...]
                        individual files to include even if normally ignored
```

*(Boolean flags rely on Python 3.9’s `argparse.BooleanOptionalAction`)*

---

## 🧩 Badges

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://python.org)

---

## 🤝 Contributing

1. **Fork** → create a **feature branch**.
2. Run `ruff`/`black` before committing (`black --line-length 88`).
3. Submit a PR with a clear description and before/after examples.

Writing the README first clarifies intent—feel free to improve this doc as you add features!

---

## 🗺️ Roadmap

- `--max-lines` / `--max-bytes` to cap output size.
- HTML output via Pygments for colourised embeds.
- GitHub Action to auto‑refresh `CONTEXT.md` on every push.

---

## 📄 License

Released under the MIT License. You are free to use, modify, and distribute this tool with minimal restrictions.

---

> **Need help?** Open an issue or drop the full snapshot into ChatGPT or Claude—the tool exists precisely for that!

