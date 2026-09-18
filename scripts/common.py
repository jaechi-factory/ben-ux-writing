#!/usr/bin/env python3
"""Shared, offline release integrity primitives. Python 3.10+.

These checks reject static links/reparse points and unexpected file types. They
are not a sandbox against hostile concurrent mutation of the same filesystem.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
NAME = 'ben-ux-writing'
INPUT_FIELDS = ('id', 'task', 'scope', 'prompt', 'facts')
SCORE_IDS = ('state', 'action', 'accuracy', 'consequence', 'plain_korean',
             'specificity', 'information_order', 'brevity', 'tone')


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':')).encode('utf-8')


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative_path(value: str) -> Path:
    p = Path(value)
    if not value or p.is_absolute() or '..' in p.parts or '\\' in value or ':' in value:
        raise ValueError(f'Unsafe relative path: {value!r}')
    if p.as_posix() != value or value == '.':
        raise ValueError(f'Non-normalized relative path: {value!r}')
    return p


def is_link(path: Path, info: os.stat_result) -> bool:
    return (stat.S_ISLNK(info.st_mode)
            or bool(getattr(info, 'st_file_attributes', 0) & 0x400))


def checked_path(base: Path, path: Path, *, must_exist: bool = False) -> Path:
    """Check all descendants of an explicitly selected, resolved root.

    The selected root may resolve an OS alias such as macOS /tmp. Below that
    root, links, junctions, mount points and non-directory ancestors are rejected.
    No resolve() is used on untrusted descendants before these lstat checks.
    """
    base = base.resolve(strict=True)
    candidate = Path(os.path.abspath(path))
    try:
        parts = candidate.relative_to(base).parts
    except ValueError as exc:
        raise ValueError(f'Path leaves allowed root: {candidate}') from exc
    current = base
    missing = False
    for index, part in enumerate(parts):
        current = current / part
        if missing:
            continue
        try:
            info = current.lstat()
        except FileNotFoundError:
            missing = True
            continue
        if is_link(current, info):
            raise ValueError(f'Links/reparse points are not supported: {current}')
        if os.path.ismount(current):
            raise ValueError(f'Nested mount points are not supported: {current}')
        if index < len(parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise ValueError(f'Ancestor is not a directory: {current}')
        if index == len(parts) - 1 and not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
            raise ValueError(f'Unsupported file type: {current}')
    if must_exist and (missing or not candidate.exists()):
        raise ValueError(f'Required path missing: {candidate}')
    return candidate


def read_bytes(root: Path, rel: str) -> bytes:
    p = checked_path(root, root / relative_path(rel), must_exist=True)
    info = p.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f'Expected regular file: {p}')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(p, flags)
    with os.fdopen(fd, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
            raise ValueError(f'File changed during read: {p}')
        return stream.read()


def read_text(root: Path, rel: str) -> str:
    return read_bytes(root, rel).decode('utf-8')


def load(root: Path, rel: str) -> Any:
    return json.loads(read_text(root, rel))


def rows(root: Path, rel: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in read_text(root, rel).splitlines() if line.strip()]


def list_tree(root: Path, base: Path) -> list[Path]:
    """Walk without following links; reject rather than silently omit them."""
    checked_path(root, base, must_exist=True)
    if not base.is_dir():
        raise ValueError(f'Expected directory: {base}')
    result: list[Path] = []
    for current, dirs, files in os.walk(base, followlinks=False):
        for name in sorted(dirs + files):
            p = checked_path(root, Path(current) / name, must_exist=True)
            if p.is_file():
                result.append(p)
    return sorted(result)


def version(root: Path) -> str:
    value = read_text(root, 'VERSION').strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?', value):
        raise ValueError('VERSION must be a safe semantic version')
    return value


def contract_errors(root: Path) -> list[str]:
    """Pin structured evaluator semantics to the preserved source contracts.

    IDs are schema aliases; Korean labels, weights, text, order, limits and source
    ranges must match. Source-file validation separately anchors the contracts
    themselves to the uploaded original. This is not cryptographic attestation.
    """
    contracts = load(root, 'core/source-contracts.json')
    score = load(root, 'core/score.json')
    failures = load(root, 'core/hard-fails.json')
    errors: list[str] = []
    raw = contracts['103']['raw_excerpt']
    pairs = [(label.strip(), int(weight)) for label, weight in
             re.findall(r'^\|\s*([^|\n]+?)\s*\|\s*(\d+)\s*\|\s*$', raw, re.M)]
    expected = [dict(id=k, label=label, max=weight)
                for k, (label, weight) in zip(SCORE_IDS, pairs)]
    threshold = re.search(r'(\d+)점 미만이면 재작성', raw)
    maximum = re.search(r'(\d+)점 기준', raw)
    if len(pairs) != len(SCORE_IDS) or score.get('items') != expected:
        errors.append('score items/labels/order/weights differ from source §103')
    if not threshold or score.get('threshold') != int(threshold.group(1)):
        errors.append('score threshold differs from source §103')
    if not maximum or score.get('maximum') != int(maximum.group(1)):
        errors.append('score maximum differs from source §103')
    if score.get('hard_fail_overrides_score') is not True:
        errors.append('Hard Fail override must be preserved')
    if score.get('source_ref') != contracts['103']['source_ref']:
        errors.append('score source range differs from source contract')
    hf_raw = contracts['102']['raw_excerpt']
    hf_pairs = re.findall(r'^### (HF-\d{2})\s*\n\s*\n([^\n]+)', hf_raw, re.M)
    if [(f.get('id'), f.get('statement_raw')) for f in failures] != hf_pairs or len(hf_pairs) != 15:
        errors.append('Hard Fail IDs/text/order differ from source §102')
    origin = contracts['102']['source_ref']
    raw_lines = hf_raw.splitlines()
    for f in failures:
        header = '### ' + str(f.get('id'))
        if header not in raw_lines:
            continue
        index = raw_lines.index(header)
        statement_index = index + 1
        while statement_index < len(raw_lines) and not raw_lines[statement_index].strip():
            statement_index += 1
        expected_ref = dict(source_id='MASTER_V1', section=102,
                            line_start=origin['line_start'] + index,
                            line_end=origin['line_start'] + statement_index)
        actual_ref = f.get('source_ref', {})
        if (actual_ref.get('source_id') != 'MASTER_V1' or actual_ref.get('section') != 102
                or actual_ref.get('line_start') != expected_ref['line_start']
                or not expected_ref['line_end'] <= actual_ref.get('line_end', -1) <= origin['line_end']
                or f.get('source_type') != 'verbatim'):
            errors.append(f'Hard Fail source range/type mismatch: {f.get("id")}')
    return errors


def assert_contracts(root: Path) -> None:
    errors = contract_errors(root)
    if errors:
        raise ValueError('Source contract mismatch: ' + '; '.join(errors))


def input_projection(case: dict[str, Any]) -> dict[str, Any]:
    payload = {key: case[key] for key in INPUT_FIELDS}
    return {**payload, 'input_sha256': sha256(canonical_bytes(payload))}


def rubric_projection(case: dict[str, Any]) -> dict[str, Any]:
    return {'id': case['id'], 'rubric': case['rubric'], 'tags': case['tags'],
            'lineage_group': case['lineage_group'],
            'input_sha256': input_projection(case)['input_sha256'],
            'rubric_sha256': sha256(canonical_bytes(case['rubric']))}


def jsonl_bytes(values: list[dict[str, Any]]) -> bytes:
    return ''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in values).encode('utf-8')
