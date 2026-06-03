
#!/usr/bin/env python3
"""Copy a directory tree replacing names with their short (DOS) equivalents.

Usage: run without args to be prompted for source and target.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from ctypes import create_unicode_buffer, windll, wintypes
from typing import Dict

# extensions considered graphic files; these will keep their original filenames
GRAPHIC_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff', '.svg', '.webp', '.ico', '.heic'}

def is_windows() -> bool:
    return os.name == "nt"


def get_short_path(path: str) -> str:
    """Return the Windows short (8.3) path for `path`.

    Falls back to a sanitized 8.3-like name when the OS API isn't available.
    """
    path = os.path.abspath(path)
    if is_windows():
        try:
            GetShortPathNameW = windll.kernel32.GetShortPathNameW
            GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
            GetShortPathNameW.restype = wintypes.DWORD
            # first try small buffer
            buf_size = 260
            buf = create_unicode_buffer(buf_size)
            needed = GetShortPathNameW(path, buf, buf_size)
            if needed == 0:
                # try large buffer
                buf_size = 32767
                buf = create_unicode_buffer(buf_size)
                needed = GetShortPathNameW(path, buf, buf_size)
            if needed == 0:
                raise OSError(f"GetShortPathNameW failed for {path}")
            return buf.value
        except Exception:
            pass

    # Portable fallback: make a deterministic 8.3-like short name for the final component
    drive, tail = os.path.splitdrive(path)
    parts = tail.strip(os.sep).split(os.sep) if tail.strip(os.sep) else []
    out_parts = []
    for p in parts:
        name, ext = os.path.splitext(p)
        # keep only A-Z0-9 characters
        base = ''.join(ch for ch in name.upper() if ch.isalnum())
        if len(base) == 0:
            base = 'FILE'
        if len(base) > 8:
            base = base[:6] + '~1'
        if ext:
            ext_clean = ''.join(ch for ch in ext.upper().lstrip('.') if ch.isalnum())
            ext_clean = ext_clean[:3]
            out = f"{base}.{ext_clean}"
        else:
            out = base
        out_parts.append(out)
    return os.path.join(drive + os.sep, *out_parts) if out_parts else drive + os.sep


def ensure_dir(path: str, dry_run: bool = False) -> None:
    if dry_run:
        print(f"[DRY] mkdir: {path}")
    else:
        os.makedirs(path, exist_ok=True)


def copy_with_shortnames(src: str, dst: str, overwrite: bool = False, dry_run: bool = False) -> None:
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)
    if not os.path.exists(src):
        raise FileNotFoundError(src)

    short_src_root = get_short_path(src)

    cache: Dict[str, str] = {}

    for root, dirs, files in os.walk(src):
        # get short path for the current directory and cache it
        short_root = cache.get(root)
        if short_root is None:
            short_root = get_short_path(root)
            cache[root] = short_root

        # compute relative path components from the original source path
        rel_orig = os.path.relpath(root, src)
        if rel_orig == '.':
            target_dir = dst
        else:
            parts = rel_orig.split(os.sep)
            target_parts: list[str] = []
            for i, part in enumerate(parts):
                if i == 0:
                    # keep first-level directory name unchanged regardless of length
                    target_parts.append(part)
                else:
                    # for deeper levels, use the short (8.3) name of that component
                    comp_path = os.path.join(src, *parts[: i + 1])
                    short_comp = cache.get(comp_path)
                    if short_comp is None:
                        try:
                            short_comp = get_short_path(comp_path)
                        except Exception:
                            short_comp = part
                        cache[comp_path] = short_comp
                    short_basename = os.path.basename(short_comp)
                    target_parts.append(short_basename)

            target_dir = os.path.normpath(os.path.join(dst, *target_parts))

        ensure_dir(target_dir, dry_run=dry_run)

        for f in files:
            src_file = os.path.join(root, f)
            orig_ext = os.path.splitext(f)[1]
            ext_l = orig_ext.lower()
            # retain original filename for graphic files
            if ext_l in GRAPHIC_EXTS:
                new_name = f
            else:
                # get short name of file and replace extension with original extension to retain it
                try:
                    short_full = get_short_path(src_file)
                    short_base = os.path.splitext(os.path.basename(short_full))[0]
                except Exception:
                    # fallback: generate from filename
                    short_base = os.path.splitext(f)[0].upper()[:8]

                new_name = short_base + orig_ext
            dst_file = os.path.join(target_dir, new_name)

            if os.path.exists(dst_file) and not overwrite:
                print(f"Skipping existing: {dst_file}")
                continue

            if dry_run:
                print(f"[DRY] copy: {src_file} -> {dst_file}")
            else:
                shutil.copy2(src_file, dst_file)
                print(f"Copied: {src_file} -> {dst_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy tree using short (DOS) names for paths and files")
    parser.add_argument("source", nargs="?", help="Source directory (will be prompted if omitted)")
    parser.add_argument("target", nargs="?", help="Target directory (will be prompted if omitted)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files in target")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without copying")
    args = parser.parse_args()

    src = args.source or input("Source path: ").strip()
    dst = args.target or input("Target destination: ").strip()

    if not src or not dst:
        print("Source and target are required")
        sys.exit(1)

    try:
        copy_with_shortnames(src, dst, overwrite=args.overwrite, dry_run=args.dry_run)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(2)


if __name__ == '__main__':
    main()
