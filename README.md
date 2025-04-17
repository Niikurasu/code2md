## Overview  

`code2md.py` is a single‑file CLI that snapshots any folder (or lone source file) into a **self‑contained Markdown document**.  
The output contains a compact directory tree and the fully syntax‑highlighted text of every relevant code file, ready to paste into ChatGPT, Claude, or an issue tracker.  
It relies only on two light dependencies—**pathspec** (for `.gitignore`‑style rules) and **pyperclip** (for cross‑platform clipboard access). citeturn0search1turn0search0  

## Features  

* **Zero‑config ignore rules.** Reads common patterns (`.git`, `__pycache__`, build artefacts) and any `.gitignore` syntax via `pathspec`, so the dump stays lean. citeturn0search1  
* **ASCII tree preview.** A readable Unicode tree precedes the file dump, inspired by popular real‑world implementations. citeturn0search4  
* **Syntax‑highlighted fences.** Each file is wrapped in triple‑back‑tick blocks with the correct language tag; GitHub & VS Code render this automatically. citeturn0search7  
* **One‑line clipboard export.** On macOS, Linux, and Windows the whole Markdown goes straight to your clipboard thanks to `pyperclip`. citeturn0search0  
* **Python ≥ 3.9.** Uses `argparse.BooleanOptionalAction` to offer `--foo / --no-foo` flags. citeturn1search2turn1search0  
* **Highly customisable.** Add `--ignore-pattern`, `--include-ext`, `--exclude-ext`, or `--extra-file` flags to fine‑tune what lands in the snapshot.  
* **MIT‑licensed.** Permissive, simple, business‑friendly. citeturn0search6  

## Quick start  

```bash
# 1 ⋅ Install
python -m pip install pathspec pyperclip       # requires Python 3.9+

# 2 ⋅ Snapshot your repo and copy to clipboard
python code2md.py .                            # defaults: show tree + clipboard

# 3 ⋅ Write to README_CONTEXT.md instead
python code2md.py . -o README_CONTEXT.md --no-clip
```

### Common recipes  

* **Skip tests & migrations, but keep SQL:**

```bash
python code2md.py my_project \
  --ignore-pattern "tests/**" "*/migrations/*" \
  --include-ext .sql
```

* **Snapshot a single helper file:**

```bash
python code2md.py src/utils/helpers.py --no-tree
```

## Command‑line reference  

```
positional arguments:
  path                  directory or file to snapshot

optional arguments:
  -o, --output FILE     write markdown here instead of stdout/clipboard
  --no-clip             disable clipboard copy even if pyperclip is present
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

*(Flags are powered by `argparse`; Boolean pairs such as `--show-tree / --no-tree` rely on `BooleanOptionalAction` introduced in Python 3.9.)* citeturn1search0turn1search5  

## Badges  

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://shields.io/badges/py-pi-python-version) citeturn0search5  

## Contributing  

1. **Fork** → create a **feature branch**.  
2. Run `ruff`/`black` before committing (style is `black --line-length 88`).  
3. Submit a PR with a clear description and before/after examples.  

Writing the README first clarifies intent—feel free to improve this doc as you add features! citeturn0news144  

## Roadmap  

* `--max-lines` / `--max-bytes` to cap output size.  
* HTML output via Pygments for colourised embeds. citeturn0search7  
* CI action to auto‑refresh `CONTEXT.md` on every push.  

## License  

Released under the [MIT License](LICENSE). You are free to use, modify, and distribute this tool with minimal restrictions. citeturn0search6  

---

> **Need help?** Open an issue or drop the full `CONTEXT.md` into ChatGPT or Claude—the tool exists precisely for that!