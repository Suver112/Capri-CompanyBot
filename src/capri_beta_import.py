"""Explicit, non-destructive media/profile copy from stable Capri into beta.

No delete, no overwrite, no secrets/cloud transfer. Models and environment are
not copied. Copy can be large; always initiated manually by the user.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import os
import shutil


MEDIA_EXT={'.gif','.png','.webp','.jpg','.jpeg','.mp4','.webm'}


def copy_missing_tree(source: Path, target: Path, *, extensions: set[str] | None=None) -> tuple[int,int]:
    copied=skipped=0
    if not source.is_dir():
        return 0,0
    for path in source.rglob('*'):
        if not path.is_file() or path.is_symlink():
            continue
        if extensions is not None and path.suffix.lower() not in extensions:
            continue
        relative=path.relative_to(source)
        dest=target/relative
        if dest.exists():
            skipped+=1
            continue
        try:
            dest.parent.mkdir(parents=True,exist_ok=True)
            with path.open('rb') as inf, dest.open('xb') as outf:
                shutil.copyfileobj(inf,outf)
            shutil.copystat(path,dest)
            copied+=1
        except (OSError,FileExistsError) as exc:
            print('Nie skopiowano:',relative,exc)
    return copied,skipped


def import_user_media(stable:Path, beta:Path, *, memory=False) -> list[str]:
    results=[]
    base=Path(os.getenv('APPDATA') or Path.home())
    prod=base/'CapriOverlay'
    test=base/'CapriOverlay_Beta'
    for folder in ('manual_voice','voices','piper_voice'):
        a,b=copy_missing_tree(prod/folder,test/folder)
        results.append(f'{folder}: skopiowano {a}, pominięto {b}')
    a,b=copy_missing_tree(stable/'assets'/'emocje',beta/'assets'/'emocje',extensions=MEDIA_EXT)
    results.append(f'awatary GIF/PNG/MP4: skopiowano {a}, pominięto {b}')
    for name in ('pronunciation_overrides.json','capri_talking_custom.gif'):
        src,dst=prod/name,test/name
        if src.is_file() and not dst.exists():
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(src,dst)
            results.append(f'{name}: skopiowano')
    if memory:
        src,dst=prod/'conversation_memory.sqlite3',test/'conversation_memory.sqlite3'
        if src.is_file() and not dst.exists():
            # SQLite backup API makes a consistent snapshot of a live database.
            import sqlite3
            dst.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(src) as original:
                with sqlite3.connect(dst) as destination:
                    original.backup(destination)
            results.append('Rozmowy: skopiowano bazę do beta')
    return results


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('stable_folder')
    parser.add_argument('--memory',action='store_true',help='Skopiuj również historię konwersacji')
    args=parser.parse_args()
    stable=Path(args.stable_folder).expanduser().resolve()
    if stable==Path(__file__).resolve().parent:
        parser.error('Wybierz istniejący folder STABILNEJ Capri, nie beta')
    if not (stable/'main.py').is_file():
        parser.error('Nie znaleziono main.py w stabilnej Capri')
    for line in import_user_media(stable,Path(__file__).resolve().parent,memory=args.memory):
        print(line)
    return 0

if __name__=='__main__':
    raise SystemExit(main())
