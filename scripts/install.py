#!/usr/bin/env python3
"""Install a local skill transactionally. Dry-run unless --apply is explicit.

No network or model calls. All targets are preflighted and staged before commit.
Ordinary copy/rename failures roll back every target; process kill/power failure
or hostile concurrent filesystem changes are not covered by that guarantee.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

from common import NAME, ROOT, checked_path, list_tree, read_bytes, sha256, load


class InstallationError(RuntimeError):
    pass


def fingerprint(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): sha256(read_bytes(root, p.relative_to(root).as_posix()))
            for p in list_tree(root, root)}


def plan_install(source: Path, base: Path, targets: list[str], replace: bool) -> list[dict[str, Any]]:
    source = Path(os.path.abspath(source))
    # Do not conceal a linked source root by resolving it first.
    checked_path(ROOT, source, must_exist=True)
    list_tree(ROOT, source)
    if not (source / 'SKILL.md').is_file():
        raise ValueError('Built SKILL.md missing; run scripts/build.py first')
    prefix = 'plugin/skills/' + NAME + '/'
    declared = load(ROOT, 'build-manifest.json')['outputs']
    expected = {rel[len(prefix):]: digest for rel, digest in declared.items() if rel.startswith(prefix)}
    if not expected or fingerprint(source) != expected:
        raise ValueError('Built skill is missing, changed or has extra files; rebuild and validate first')
    jobs = []
    for target in targets:
        if target not in ('codex', 'claude'):
            raise ValueError('Unsupported target')
        dest = base / ('.agents' if target == 'codex' else '.claude') / 'skills' / NAME
        checked_path(base, dest)
        if dest.exists() and not dest.is_dir():
            raise ValueError(f'Destination is not a directory: {dest}')
        if dest.exists() and not replace:
            raise ValueError(f'Existing skill preserved: {dest}; use --replace-with-backup after review')
        if dest.exists():
            list_tree(base, dest)
        if source == dest or source.is_relative_to(dest) or dest.is_relative_to(source):
            raise ValueError('Source and destination must not overlap')
        jobs.append({'host': target, 'destination': dest, 'existed': dest.exists(),
                     'before': fingerprint(dest) if dest.exists() else None})
    for name in ('.chihun-install-staging', '.chihun-skill-backups'):
        checked_path(base, base / name)
        if (base / name).exists() and not (base / name).is_dir():
            raise ValueError(f'Expected directory: {base / name}')
    checked_path(base, base / '.chihun-install.lock')
    return jobs


def install_skill(source: Path, base: Path, targets: list[str], replace: bool = False) -> dict[str, Any]:
    base = base.resolve(strict=True)
    jobs = plan_install(source, base, targets, replace)
    session = uuid.uuid4().hex
    stage_root = base / '.chihun-install-staging' / session
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + session[:8]
    for job in jobs:
        job['stage'] = stage_root / job['host'] / NAME
        job['backup'] = base / '.chihun-skill-backups' / job['host'] / stamp / NAME
        checked_path(base, job['stage'])
        checked_path(base, job['backup'])
        job.update(backed_up=False, committed=False)
    lock = base / '.chihun-install.lock'
    checked_path(base, lock)
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    os.close(fd)
    created: list[Path] = []

    def mkdirs(path: Path) -> None:
        checked_path(base, path)
        chain = []
        current = path
        while current != base and not current.exists():
            chain.append(current)
            current = current.parent
        for directory in reversed(chain):
            checked_path(base, directory)
            directory.mkdir()
            created.append(directory)

    def prune_empty() -> None:
        for path in reversed(created):
            try:
                checked_path(base, path)
                path.rmdir()
            except FileNotFoundError:
                pass
            except OSError:
                pass  # successful backups are deliberately retained

    try:
        # Recheck every target while holding our installer lock, before writes.
        plan_install(source, base, targets, replace)
        source_hashes = fingerprint(source)
        for job in jobs:
            mkdirs(job['stage'].parent)
            checked_path(base, job['stage'])
            shutil.copytree(source, job['stage'], symlinks=True)
            if fingerprint(job['stage']) != source_hashes:
                raise InstallationError('Staged skill differs from source')
        # Prepare destination/backup parents before moving any installed tree.
        for job in jobs:
            mkdirs(job['destination'].parent)
            if job['existed']:
                mkdirs(job['backup'].parent)
        for job in jobs:
            dest = job['destination']
            checked_path(base, dest)
            if dest.exists() != job['existed']:
                raise InstallationError(f'Destination changed during installation: {dest}')
            if job['existed'] and fingerprint(dest) != job['before']:
                raise InstallationError(f'Existing skill changed during installation: {dest}')
            if job['existed']:
                checked_path(base, job['backup'])
                os.replace(dest, job['backup'])
                job['backed_up'] = True
            checked_path(base, job['stage'], must_exist=True)
            checked_path(base, dest)
            os.replace(job['stage'], dest)
            job['committed'] = True
        if fingerprint(source) != source_hashes:
            raise InstallationError('Source changed during installation')
        return {'result': 'copied', 'targets': [
            {'host': j['host'], 'destination': str(j['destination']),
             'backup': str(j['backup']) if j['backed_up'] else None} for j in jobs],
            'host_invocation_verified': False, 'copy_quality_verified': False}
    except BaseException as exc:
        rollback_errors = []
        for job in reversed(jobs):
            try:
                dest = job['destination']
                if job['committed']:
                    checked_path(base, dest, must_exist=True)
                    shutil.rmtree(dest)
                if job['backed_up']:
                    checked_path(base, job['backup'], must_exist=True)
                    checked_path(base, dest)
                    if dest.exists():
                        raise InstallationError(f'Refusing to overwrite changed destination during rollback: {dest}')
                    os.replace(job['backup'], dest)
            except Exception as restore_error:
                rollback_errors.append(f"{job['host']}: {restore_error}")
        if rollback_errors:
            raise InstallationError('Rollback incomplete; inspect retained backups. ' +
                                    '; '.join(rollback_errors)) from exc
        raise InstallationError(f'Installation failed; all committed targets restored: {exc}') from exc
    finally:
        try:
            checked_path(base, stage_root)
            if stage_root.exists():
                shutil.rmtree(stage_root)
            prune_empty()
        finally:
            checked_path(base, lock)
            lock.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=['codex', 'claude', 'both'], required=True)
    parser.add_argument('--scope', choices=['user', 'project'], default='project')
    parser.add_argument('--project', type=Path)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--replace-with-backup', action='store_true')
    args = parser.parse_args()
    if args.scope == 'project':
        if args.project is None:
            parser.error('--project is required for project scope')
        base = args.project.expanduser().resolve(strict=True)
    else:
        if args.project is not None:
            parser.error('--project is not used with user scope')
        base = Path.home().resolve(strict=True)
    if not base.is_dir():
        parser.error('Selected root must be an existing directory')
    source = ROOT / 'plugin/skills' / NAME
    targets = ['codex', 'claude'] if args.target == 'both' else [args.target]
    jobs = plan_install(source, base, targets, args.replace_with_backup)
    print(json.dumps({'mode': 'apply' if args.apply else 'dry_run', 'source': str(source),
                      'resolved_root': str(base), 'targets': [
                          {'host': j['host'], 'destination': str(j['destination'])} for j in jobs],
                      'backup_existing': args.replace_with_backup, 'network_requests': False},
                     ensure_ascii=False, indent=2))
    if args.apply:
        result = install_skill(source, base, targets, args.replace_with_backup)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, InstallationError) as exc:
        print(f'Installation stopped: {exc}', file=sys.stderr)
        raise SystemExit(1)
