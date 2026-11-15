#!/usr/bin/env python3
"""Optionally import renderer-independent QA from an authorized local kotlinfest checkout."""
from pathlib import Path
import argparse
import shutil
import sys

FILES = ("harness/presentation_harness.py",)
DIRS = ("harness/schemas",)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True, help="Local checkout of authorized original repository")
    ap.add_argument("--destination", type=Path, default=Path("legacy-qa"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    source = args.source.resolve()
    dest = args.destination.resolve()
    if not (source / "HARNESS_ARCHITECTURE.md").is_file():
        print('Source is not an identifiable kotlinfest-2026 checkout', file=sys.stderr)
        return 1
    if dest.is_relative_to(source):
        print('Refusing to write inside original repository', file=sys.stderr)
        return 1
    for rel in FILES + DIRS:
        src = source / rel
        dst = dest / Path(rel).relative_to("harness")
        if not src.exists() or not src.resolve().is_relative_to(source):
            print('Missing or unsafe source: '+str(src),file=sys.stderr)
            return 1
        print(f"{src} -> {dst}")
        if not args.dry_run:
            if dst.exists():
                print('Refusing to overwrite: '+str(dst),file=sys.stderr)
                return 1
            dst.parent.mkdir(parents=True,exist_ok=True)
            if src.is_dir():shutil.copytree(src,dst)
            else:shutil.copy2(src,dst)
    if not args.dry_run:
        (dest / 'PROVENANCE.txt').write_text('Extracted from authorized local rioX432/kotlinfest-2026 checkout. Includes no deck-specific profiles, slides, code or assets.\n')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
