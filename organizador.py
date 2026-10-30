"""Reconstrução independente: organiza arquivos sem sobrescrever destinos."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

CATEGORIES = {
    'Documentos': {'.pdf', '.txt', '.doc', '.docx', '.odt', '.rtf', '.ppt', '.pptx', '.epub'},
    'Imagens': {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg', '.heic'},
    'Videos': {'.mp4', '.mkv', '.avi', '.mov', '.webm', '.wmv'},
    'Musicas': {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac'},
    'Planilhas': {'.xls', '.xlsx', '.csv', '.ods'},
    'Compactados': {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'},
}
INCOMPLETE = {'.part', '.crdownload', '.tmp', '.download'}
LOG_NAME = 'organizador-operacoes.jsonl'


def category(path: Path) -> str:
    suffix = path.suffix.lower()
    return next((name for name, extensions in CATEGORIES.items() if suffix in extensions), 'Outros')


def plan(folder: Path) -> list[tuple[Path, Path]]:
    folder = folder.expanduser().resolve(strict=True)
    if not folder.is_dir():
        raise ValueError('Informe uma pasta existente.')
    result = []
    reserved = set()
    running_files = {Path(__file__).resolve(), Path(sys.executable).resolve()}
    for source in sorted(folder.iterdir(), key=lambda p: p.name.casefold()):
        if (source.is_symlink() or not source.is_file() or source.resolve() in running_files or source.name.startswith('.')
                or source.name == LOG_NAME or source.suffix.lower() in INCOMPLETE):
            continue
        parent = folder / category(source)
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            raise ValueError(f'Destino inválido: {parent.name}. Nenhum arquivo foi movido.')
        index = 0
        while True:
            name = source.name if index == 0 else f'{source.stem} ({index}){source.suffix}'
            target = parent / name
            key = str(target).casefold()
            if not target.exists() and not target.is_symlink() and key not in reserved:
                reserved.add(key)
                result.append((source, target))
                break
            index += 1
    return result


def _copy_exclusive(source: Path, target: Path) -> None:
    """Fallback para volumes sem hardlinks; o modo xb impede sobrescrita."""
    before = source.stat()
    created = False
    try:
        with source.open('rb') as src, target.open('xb') as dst:
            created = True
            shutil.copyfileobj(src, dst)
            dst.flush()
            os.fsync(dst.fileno())
        after = source.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise OSError('Arquivo foi alterado durante a cópia; origem preservada.')
        shutil.copystat(source, target)
        source.unlink()
    except Exception:
        # Só remove o destino criado nesta tentativa; nunca um destino existente.
        if created:
            target.unlink(missing_ok=True)
        raise


def organize(folder: Path, *, apply: bool = False) -> list[dict]:
    folder = folder.expanduser().resolve(strict=True)
    operations = plan(folder)
    if not apply:
        return [{'origem': str(a), 'destino': str(b), 'status': 'simulado'} for a, b in operations]
    records = []
    log_path = folder / LOG_NAME
    if log_path.is_symlink():
        raise ValueError('O arquivo de log não pode ser um link simbólico.')
    # Abrir o log antes de mover garante que uma falha inicial de permissão não mova arquivos.
    with log_path.open('a', encoding='utf-8') as log:
        for source, target in operations:
            record = {'data_utc': datetime.now(timezone.utc).isoformat(), 'origem': str(source), 'destino': str(target)}
            try:
                if source.is_symlink() or target.parent.is_symlink():
                    raise ValueError('Link simbólico detectado; arquivo preservado.')
                target.parent.mkdir(exist_ok=True)
                try:
                    os.link(source, target, follow_symlinks=False)
                except FileExistsError:
                    raise FileExistsError('Destino criado após a simulação; origem preservada.') from None
                except OSError:
                    _copy_exclusive(source, target)
                else:
                    try:
                        source.unlink()
                    except OSError:
                        target.unlink()
                        raise
                record['status'] = 'movido'
            except (OSError, ValueError) as error:
                record.update(status='erro', erro=str(error))
            log.write(json.dumps(record, ensure_ascii=False) + '\n')
            log.flush()
            records.append(record)
    return records


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Organizador de Downloads — reconstrução independente. Simula por padrão.')
    parser.add_argument('pasta', type=Path, help='Pasta a organizar, sem processar subpastas.')
    parser.add_argument('--aplicar', action='store_true', help='Move os arquivos e grava o log. Sem esta opção, somente simula.')
    args = parser.parse_args(argv)
    try:
        records = organize(args.pasta, apply=args.aplicar)
    except (OSError, ValueError) as error:
        parser.exit(2, f'Erro: {error}\n')
    print(json.dumps(records, ensure_ascii=False, indent=2))
    if not args.aplicar:
        print('SIMULAÇÃO: nenhum arquivo ou diretório foi alterado.')
    return int(any(r['status'] == 'erro' for r in records))


if __name__ == '__main__':
    raise SystemExit(main())
