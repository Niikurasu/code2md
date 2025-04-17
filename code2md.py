#!/usr/bin/env python3

import argparse
import os
import sys
import platform
from pathlib import Path
import fnmatch
import yaml # Requires PyYAML
from tqdm import tqdm # Requires tqdm
import logging

try:
    import pyperclip # Requires pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    # Let the script run, but disable clipboard functionality later if needed


# --- Configuration Loading ---
CONFIG_FILENAME = ".codetomdrc.yaml"

DEFAULT_CONFIG = {
    'comment': "Default configuration. Customize in project/.codetomdrc.yaml or ~/.codetomdrc.yaml",
    'code_extensions': [
        '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp',
        '.cs', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.kts', '.scala',
        '.html', '.htm', '.css', '.scss', '.less', '.vue', '.svelte',
        '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
        '.sh', '.bash', '.zsh', '.ps1', '.bat', '.cmd',
        '.sql', '.md', '.markdown', '.rst', '.gradle', '.xml', '.dockerfile', 'Dockerfile',
        '. R', '.r', '.m', '.ipynb', '.lua', # Added Lua
    ],
    'ignore_patterns': [
        # VCS
        '.git', '.svn', '.hg',
        # Python cache/build
        '__pycache__', '*.pyc', '*.pyo', '*.pyd',
        '.env', 'venv', '.venv', 'env', 'ENV', '*activate*', # Virtual envs
        '.pytest_cache', '.mypy_cache', '.ruff_cache',
        # Node cache/build
        'node_modules', '.npm', 'yarn.lock', 'package-lock.json', 'pnpm-lock.yaml',
        '.yarn',
        # Build/dist outputs
        'build', 'dist', 'target', 'out', 'bin', 'obj',
        # IDE/OS files
        '.vscode', '.idea', '.DS_Store', 'Thumbs.db',
        # Logs/Temp
        '*.log', '*.tmp', '*.temp', '*.swp', '*.swo', '*.swn',
        # Common data/asset formats (usually not needed for code context)
        '*.min.js', '*.min.css', # Minified assets
        '*.svg', '*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.ico', '*.webp', # Images
        '*.pdf', '*.doc', '*.docx', '*.xls', '*.xlsx', '*.ppt', '*.pptx', # Documents
        '*.zip', '*.tar', '*.gz', '*.bz2', '*.rar', '*.7z', # Archives
        '*.mp3', '*.wav', '*.ogg', '*.mp4', '*.avi', '*.mov', '*.webm', # Media
        '*.db', '*.sqlite', '*.sqlite3', # Databases
        # Specific lock files handled elsewhere if needed
        'poetry.lock', 'Pipfile.lock',
        '.mypy_cache', '.ruff_cache',
        '.next',
    ],
    'max_file_size': 1 * 1024 * 1024, # 1 MB
    'output_filename': 'project_context.md',
    'include_tree': True,
}

def load_config(start_path: Path) -> dict:
    """Loads configuration, merging defaults, home config, and project config."""
    config = DEFAULT_CONFIG.copy()
    paths_to_check = []

    # 1. Home directory config
    home_config_path = Path.home() / CONFIG_FILENAME
    if home_config_path.is_file():
        paths_to_check.append(home_config_path)

    # 2. Project directory config (if start_path is a dir)
    #    or parent directory config (if start_path is a file)
    project_dir = start_path if start_path.is_dir() else start_path.parent
    project_config_path = project_dir / CONFIG_FILENAME
    if project_config_path.is_file():
        paths_to_check.append(project_config_path)

    loaded_files = []
    for config_path in paths_to_check:
        try:
            print(f"Loading config: {config_path}")
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    # Simple merge: user keys override default keys
                    # For lists, user list *replaces* default list
                    config.update(user_config)
                    loaded_files.append(str(config_path))
        except yaml.YAMLError as e:
            print(f"Warning: Error parsing config file {config_path}: {e}", file=sys.stderr)
        except OSError as e:
             print(f"Warning: Could not read config file {config_path}: {e}", file=sys.stderr)

    if loaded_files:
        print(f"Successfully merged config from: {', '.join(loaded_files)}")
    else:
        print("Using default configuration (no .codetomdrc.yaml found or loaded).")

    # Ensure lists are sets for efficient lookup later, handle potential non-list values
    config['code_extensions'] = set(config.get('code_extensions', []) or [])
    config['ignore_patterns'] = set(config.get('ignore_patterns', []) or [])


    return config

# --- Helper Functions ---

def setup_logging(verbose_level):
    """Sets up logging based on verbosity."""
    if verbose_level > 0:
        log_level = logging.DEBUG
        log_format = '%(levelname)s: %(message)s'
    else:
        log_level = logging.INFO
        log_format = '%(message)s' # Only show messages for INFO level

    # Configure root logger - remove existing handlers first if any
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(level=log_level, format=log_format, stream=sys.stderr) # Log to stderr


def should_ignore(path: Path, root_path: Path, ignore_patterns: set, max_size: int | None) -> tuple[bool, str]:
    """
    Check if a path should be ignored.
    Returns (should_ignore: bool, reason: str)
    """
    try:
        relative_path = path.relative_to(root_path)
        relative_path_str = str(relative_path).replace(os.sep, '/') # Use forward slashes for matching
    except ValueError:
        # Handle cases where path is not under root_path (e.g., single file input)
        relative_path_str = path.name

    path_parts = set(relative_path.parts)
    name = path.name
    ext = path.suffix.lower()

    # 1. Check ignore patterns
    for pattern in ignore_patterns:
        # Match against the full relative path (e.g., 'src/vendor/lib')
        if fnmatch.fnmatch(relative_path_str, pattern):
            return True, f"Ignoring '{relative_path_str}' (matches pattern '{pattern}')"
        # Match against the basename (e.g., 'node_modules', '*.log')
        if fnmatch.fnmatch(name, pattern):
             return True, f"Ignoring '{relative_path_str}' (name matches pattern '{pattern}')"
        # Match directory name anywhere in the path parts (handles 'venv' matching '/path/to/project/venv/file')
        # Avoid matching patterns like '*.py' against directory parts
        if not pattern.startswith('*') and pattern in path_parts:
             return True, f"Ignoring '{relative_path_str}' (path part matches pattern '{pattern}')"


    # 2. Check file size limit
    if path.is_file() and max_size is not None:
        try:
            file_size = path.stat().st_size
            if file_size > max_size:
                return True, f"Ignoring '{relative_path_str}' (size {file_size} > max {max_size} bytes)"
        except OSError as e:
            return True, f"Ignoring '{relative_path_str}' (could not get size: {e})"

    return False, ""


def generate_tree(start_path: Path, root_path: Path, ignore_patterns: set, max_size: int | None, prefix: str = "", is_last: bool = True, header: bool = True) -> str:
    """Generates a string representation of the directory tree, respecting ignores."""
    tree_str = ""
    display_name = start_path.name if header else start_path.relative_to(start_path.parent).name # Use relative name inside tree

    if header:
        tree_str += f"Project Tree (`{start_path.relative_to(root_path.parent)}`):\n```\n"
        tree_str += f"{display_name}\n"

    try:
        # Sort items: directories first, then files, alphabetically
        items = sorted(list(start_path.iterdir()), key=lambda p: (p.is_file(), p.name.lower()))
    except OSError as e:
        logging.warning(f"Could not list items in {start_path}: {e}")
        items = []

    # Prepare items for display, filtering ignored ones
    display_items = []
    for item in items:
         ignore, reason = should_ignore(item, root_path, ignore_patterns, max_size)
         if not ignore:
             display_items.append(item)
         # else: # Optional: log ignored items during tree building at high verbosity
         #     if logging.getLogger().isEnabledFor(logging.DEBUG):
         #         logging.debug(f"Tree: {reason}")


    count = len(display_items)
    for i, item in enumerate(display_items):
        is_current_last = (i == count - 1)
        connector = "└── " if is_current_last else "├── "
        tree_str += prefix + connector + item.name + "\n"

        if item.is_dir():
            new_prefix = prefix + ("    " if is_current_last else "│   ")
            # Recursive call, passing False for header
            tree_str += generate_tree(item, root_path, ignore_patterns, max_size, new_prefix, is_current_last, header=False)

    if header:
        tree_str += "```\n"
    return tree_str

def is_likely_binary(file_path: Path, chunk_size=1024) -> bool:
    """Heuristic check if a file is likely binary."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(chunk_size)
        # Common heuristic: check for null bytes or a high proportion of non-text characters
        # (This is not foolproof!)
        if b'\0' in chunk:
            return True
        # Check if chunk decodes cleanly as utf-8
        try:
            chunk.decode('utf-8', errors='strict')
        except UnicodeDecodeError:
            return True # If the first chunk isn't valid UTF-8, likely binary or wrong encoding

        # Add more checks if needed, e.g., control characters
        # text_chars = bytes({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})
        # non_text_ratio = sum(1 for b in chunk if b not in text_chars) / len(chunk)
        # if non_text_ratio > 0.3: # Arbitrary threshold
        #     return True

    except OSError as e:
         logging.warning(f"Could not read start of file {file_path} for binary check: {e}")
         return True # Treat as binary if unreadable
    except Exception as e:
        logging.error(f"Unexpected error during binary check for {file_path}: {e}")
        return True # Err on the side of caution

    return False

def get_code_files(start_path: Path, root_path: Path, ignore_patterns: set, include_exts: set | None, code_extensions: set, max_size: int | None) -> tuple[list[Path], dict]:
    """
    Finds all code files recursively, respecting ignores and configuration.
    Returns (list_of_code_files, dictionary_of_skipped_files_with_reasons)
    """
    code_files = []
    skipped_files = {} # Store path_str: reason

    # Handle single file input
    if start_path.is_file():
        ignore, reason = should_ignore(start_path, root_path, ignore_patterns, max_size)
        if ignore:
            skipped_files[str(start_path)] = reason
            return [], skipped_files

        ext = start_path.suffix.lower() or start_path.name # Handle files like 'Dockerfile'
        is_target_ext = (include_exts is not None and ext in include_exts) or \
                        (include_exts is None and ext in code_extensions)

        if not is_target_ext:
             skipped_files[str(start_path)] = f"Skipping '{start_path.name}' (extension '{ext}' not in include list)"
             return [], skipped_files

        if is_likely_binary(start_path):
            skipped_files[str(start_path)] = f"Skipping '{start_path.name}' (likely binary)"
            return [], skipped_files

        code_files.append(start_path)
        return code_files, skipped_files

    # Handle directory input using os.walk for efficiency
    all_paths = []
    for dirpath, dirnames, filenames in os.walk(start_path, topdown=True):
        current_dir_path = Path(dirpath)

        # --- Directory Pruning ---
        original_dirs = list(dirnames) # Copy before modifying
        dirnames[:] = [] # Clear the list, we'll add back allowed ones
        for d in original_dirs:
            dir_path = current_dir_path / d
            ignore, reason = should_ignore(dir_path, root_path, ignore_patterns, max_size=None) # Don't check size for dirs
            if not ignore:
                dirnames.append(d) # Keep this directory for traversal
            else:
                 skipped_files[str(dir_path.relative_to(root_path))] = reason


        # --- File Processing ---
        for filename in filenames:
             all_paths.append(current_dir_path / filename)


    # Iterate through files with tqdm progress bar
    # Sort first for consistent processing order (optional, but good practice)
    all_paths.sort()
    print(f"Scanning {len(all_paths)} potential files...")
    for file_path in tqdm(all_paths, desc="Processing files", unit="file", disable=logging.getLogger().getEffectiveLevel() > logging.INFO):
        # 1. Check ignores (already checked dirs, now check files)
        ignore, reason = should_ignore(file_path, root_path, ignore_patterns, max_size)
        if ignore:
            skipped_files[str(file_path.relative_to(root_path))] = reason
            continue

        # 2. Check extension
        ext = file_path.suffix.lower() or file_path.name # Handle files like 'Dockerfile'
        is_target_ext = (include_exts is not None and ext in include_exts) or \
                        (include_exts is None and ext in code_extensions)
        if not is_target_ext:
            reason = f"Skipping '{file_path.relative_to(root_path)}' (extension '{ext}' not included)"
            skipped_files[str(file_path.relative_to(root_path))] = reason
            continue

        # 3. Check if likely binary
        if is_likely_binary(file_path):
            reason = f"Skipping '{file_path.relative_to(root_path)}' (likely binary)"
            skipped_files[str(file_path.relative_to(root_path))] = reason
            continue

        # If all checks pass, add to list
        code_files.append(file_path)

    # Sort final list by path for consistent output
    code_files.sort()
    return code_files, skipped_files


def create_markdown(root_path: Path, start_path: Path, code_files: list[Path], output_file: Path, config: dict, skipped_files: dict):
    """Creates the final Markdown file."""
    output_abs_path = output_file.resolve()
    print(f"\nWriting output to: {output_abs_path}")
    total_content_size = 0

    try:
        with open(output_abs_path, "w", encoding="utf-8") as md_file:
            # 1. Add Header
            project_name = root_path.name
            md_file.write(f"# Project Context: {project_name}\n\n")
            md_file.write(f"Generated from: `{start_path.relative_to(root_path.parent)}`\n\n")


            # 2. Add Project Tree (if enabled and input is directory)
            if config['include_tree']:
                if start_path.is_dir():
                    print("Generating project tree...")
                    tree_str = generate_tree(start_path, root_path, config['ignore_patterns'], config['max_file_size'])
                    md_file.write(tree_str)
                    md_file.write("\n---\n\n") # Separator
                else:
                    md_file.write("Input is a single file (no tree generated).\n\n---\n\n")
            else:
                 md_file.write("Project tree generation skipped by user.\n\n---\n\n")


            # 3. Add File Contents
            md_file.write("## File Contents\n\n")

            if not code_files:
                md_file.write("No code files were included based on the specified criteria.\n")
                logging.warning("No files matched the criteria for inclusion in the output.")
                # Keep going to print summary
            else:
                 total_files = len(code_files)
                 print(f"Adding content from {total_files} files...")
                 for i, file_path in enumerate(tqdm(code_files, desc="Writing files", unit="file", disable=logging.getLogger().getEffectiveLevel() > logging.INFO)):
                    try:
                        # Use root_path for consistent relative paths in output
                        relative_path = file_path.relative_to(root_path)
                    except ValueError:
                        relative_path = file_path.name # Fallback for single file case

                    logging.debug(f"Processing ({i+1}/{total_files}): {relative_path}")

                    try:
                        content = file_path.read_text(encoding="utf-8")
                        content_size = len(content.encode('utf-8'))
                        total_content_size += content_size

                        ext = (file_path.suffix[1:] or file_path.name).lower() # Get extension without dot for hint

                        md_file.write(f"### File: `{str(relative_path).replace(os.sep, '/')}`\n\n")
                        md_file.write(f"```{ext}\n") # Add language hint
                        md_file.write(content.strip() + "\n")
                        md_file.write("```\n\n")
                        # Avoid excessive separators if file content is empty
                        if content.strip():
                           md_file.write("---\n\n")

                    except UnicodeDecodeError:
                        skipped_files[str(relative_path)] = f"Skipping '{relative_path}' (UTF-8 decoding error)"
                        logging.warning(f"Skipping file due to encoding error (not UTF-8): {relative_path}")
                    except OSError as e:
                         skipped_files[str(relative_path)] = f"Skipping '{relative_path}' (OS error reading: {e})"
                         logging.error(f"Error reading file {relative_path}: {e}")
                    except Exception as e:
                         skipped_files[str(relative_path)] = f"Skipping '{relative_path}' (Unexpected error: {e})"
                         logging.error(f"An unexpected error occurred processing file {relative_path}: {e}")

        # Return total size and final path
        return output_abs_path, total_content_size

    except OSError as e:
        logging.error(f"Fatal: Could not write to output file {output_abs_path}: {e}")
        sys.exit(1)
    except Exception as e:
         logging.error(f"Fatal: An unexpected error occurred writing the output file: {e}")
         sys.exit(1)


# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(
        description="Combine code files from a project into a single Markdown file for LLM context.",
        epilog="""\
Configuration is loaded from default settings, then updated by ~/.codetomdrc.yaml (if exists),
then by <project>/.codetomdrc.yaml (if exists), and finally overridden by command-line arguments.
Use --show-config to see the final configuration being used.
Example .codetomdrc.yaml:
---
# Optional: Add a comment
comment: My custom project settings

# List of extensions to consider code (replaces default list)
# code_extensions:
#   - .py
#   - .js

# List of patterns to ignore (replaces default list)
ignore_patterns:
  - .git
  - node_modules
  - venv
  - '*.log'
  - 'docs/' # Ignore the whole docs directory

# Max file size in bytes (0 for no limit)
max_file_size: 2097152 # 2MB

# Default output filename
output_filename: context_for_ai.md

# Whether to include the directory tree (true/false)
include_tree: true
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # --- Input/Output Arguments ---
    io_group = parser.add_argument_group('Input/Output')
    io_group.add_argument(
        "input_path",
        type=str,
        help="Path to the project folder or a single code file."
    )
    io_group.add_argument(
        "-o", "--output",
        type=str,
        help="Name/Path of the output Markdown file. Overrides config file setting."
    )
    io_group.add_argument(
        "--clipboard",
        action="store_true",
        help=f"Copy the final Markdown content to the clipboard. {'(Requires pyperclip)' if not PYPERCLIP_AVAILABLE else ''}"
    )

    # --- Filtering Arguments ---
    filter_group = parser.add_argument_group('Filtering and Inclusion')
    filter_group.add_argument(
        "--ignore",
        nargs='*',
        metavar='PATTERN',
        help="Space-separated list of patterns (fnmatch style) to ignore. Overrides patterns from config files and defaults."
    )
    filter_group.add_argument(
        "--include-ext",
        nargs='*',
        metavar='EXTENSION',
        help="Space-separated list of extensions (e.g., .py .js) to *exclusively* include. If used, only these extensions are considered, overriding 'code_extensions' from config/defaults."
    )
    filter_group.add_argument(
        "--max-size",
        type=int,
        metavar='BYTES',
        help="Maximum file size in bytes to include. 0 means no limit. Overrides config file setting."
    )

    # --- Formatting Arguments ---
    format_group = parser.add_argument_group('Output Formatting')
    format_group.add_argument(
        "--no-tree",
        action="store_true",
        default=None, # Use None to distinguish between default false and explicitly set true
        help="Do not include the directory tree structure at the beginning of the output. Overrides config file setting."
    )

    # --- Utility Arguments ---
    util_group = parser.add_argument_group('Utilities')
    util_group.add_argument(
        "--show-config",
        action="store_true",
        help="Display the final effective configuration (after merging defaults, files, and args) and exit."
    )
    util_group.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity. -v shows files being skipped, -vv for more debug info."
    )

    args = parser.parse_args()

    # --- Initial Setup ---
    setup_logging(args.verbose) # Setup logging early

    start_path_input = Path(args.input_path)
    if not start_path_input.exists():
        logging.error(f"Error: Input path '{args.input_path}' does not exist.")
        sys.exit(1)

    start_path = start_path_input.resolve() # Get absolute path
    root_path = start_path if start_path.is_dir() else start_path.parent

    # --- Load and Merge Configuration ---
    config = load_config(start_path)

    # Override config with command-line arguments if they were provided
    if args.output:
        config['output_filename'] = args.output
    if args.ignore is not None: # If --ignore is present (even if empty list), override config
        config['ignore_patterns'] = set(args.ignore)
        logging.info("Overriding ignore patterns with command line arguments.")
    if args.max_size is not None:
        config['max_file_size'] = args.max_size if args.max_size > 0 else None
        logging.info("Overriding max file size with command line argument.")
    if args.no_tree is not None: # User explicitly used --no-tree
        config['include_tree'] = False
        logging.info("Overriding include_tree (set to False) with command line argument.")

    # Handle exclusive extension inclusion
    include_extensions_override = None
    if args.include_ext is not None: # If --include-ext is present (even if empty list), override config
        include_extensions_override = set(ext if ext.startswith('.') else '.' + ext for ext in args.include_ext)
        logging.info(f"Overriding included extensions with command line arguments: {', '.join(include_extensions_override) or 'None'}")


    # Ensure required config keys exist after potential user overrides
    config.setdefault('code_extensions', set(DEFAULT_CONFIG['code_extensions']))
    config.setdefault('ignore_patterns', set(DEFAULT_CONFIG['ignore_patterns']))
    config.setdefault('max_file_size', DEFAULT_CONFIG['max_file_size'])
    config.setdefault('output_filename', DEFAULT_CONFIG['output_filename'])
    config.setdefault('include_tree', DEFAULT_CONFIG['include_tree'])


    # --- Show Config and Exit (if requested) ---
    if args.show_config:
        print("\n--- Effective Configuration ---")
        # Display the relevant final settings
        print(f"Input Path: {start_path}")
        print(f"Project Root: {root_path}")
        print(f"Output File: {Path(config['output_filename']).resolve()}")
        print(f"Include Tree: {config['include_tree']}")
        print(f"Max File Size: {config['max_file_size']} bytes" if config['max_file_size'] is not None else "No limit")
        if include_extensions_override is not None:
             print(f"Included Extensions (Cmd-line Override): {', '.join(sorted(list(include_extensions_override))) or 'None'}")
        else:
             print(f"Considered Code Extensions (Config/Default): {', '.join(sorted(list(config['code_extensions'])))}")
        print(f"Ignore Patterns (Config/Cmd-line):")
        for pattern in sorted(list(config['ignore_patterns'])):
            print(f"  - {pattern}")
        print("-----------------------------")
        sys.exit(0)

    # --- Core Logic ---
    logging.info(f"Processing project: {root_path}")
    logging.info(f"Ignoring patterns: {', '.join(sorted(list(config['ignore_patterns'])))}")
    if include_extensions_override is not None:
         logging.info(f"Including ONLY extensions: {', '.join(sorted(list(include_extensions_override))) or 'None'}")
    else:
         logging.info(f"Considering code extensions: {', '.join(sorted(list(config['code_extensions'])))}")


    code_files, skipped_files = get_code_files(
        start_path,
        root_path,
        config['ignore_patterns'],
        include_extensions_override, # Use override if specified
        config['code_extensions'],   # Otherwise uses config/default
        config['max_file_size']
    )

    output_path_arg = Path(config['output_filename'])
    # Make output path relative to CWD if not absolute, like typical CLIs
    output_path_final = output_path_arg if output_path_arg.is_absolute() else Path.cwd() / output_path_arg

    if not code_files and not skipped_files:
        logging.warning("No files found at all in the input path.")
        # Decide if you want to create an empty file or just exit
        # Let's create it for consistency, create_markdown handles empty list
        # sys.exit(0)


    output_abs_path, total_content_size = create_markdown(
        root_path,
        start_path, # Pass original start path for header
        code_files,
        output_path_final,
        config,
        skipped_files # Pass skipped files for summary and potential logging inside
    )

    # --- Final Summary & Actions ---
    print("\n--- Summary ---")
    print(f"Markdown output generated at: {output_abs_path}")
    print(f"Included {len(code_files)} files.")
    print(f"Total content size: {total_content_size / 1024:.2f} KB")

    if skipped_files:
        print(f"Skipped {len(skipped_files)} files/directories.")
        # Log skipped files details if verbose
        if args.verbose > 0:
             print("Skipped items:")
             # Sort skipped items for consistent reporting
             for item, reason in sorted(skipped_files.items()):
                 logging.info(f"- {reason}") # Use logging to print based on verbosity level set earlier
        else:
            print("(Use -v to see details of skipped items)")

    # Copy to clipboard if requested
    if args.clipboard:
        if PYPERCLIP_AVAILABLE:
            try:
                with open(output_abs_path, 'r', encoding='utf-8') as f:
                    final_content = f.read()
                pyperclip.copy(final_content)
                print("Markdown content copied to clipboard!")
            except OSError as e:
                logging.error(f"Error reading output file for clipboard: {e}")
            except pyperclip.PyperclipException as e:
                 logging.error(f"Error copying to clipboard: {e}")
                 print("Clipboard functionality may not be available on this system or environment (e.g., SSH without X forwarding).")
            except Exception as e:
                 logging.error(f"An unexpected error occurred during clipboard copy: {e}")

        else:
            logging.warning("Cannot copy to clipboard: 'pyperclip' package not found.")
            print("Install it using: pip install pyperclip")

    print("\nDone.")


if __name__ == "__main__":
    main()