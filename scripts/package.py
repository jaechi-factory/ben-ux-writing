#!/usr/bin/env python3
"""Package only explicitly allowlisted authored files and exact build outputs.

Refuses stale/tampered generated files. Unknown ordinary files are omitted;
links/reparse points anywhere in the public input trees are rejected. No upload.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

import common
from common import ROOT
from build import render_outputs


def add(z: zipfile.ZipFile, name: str, data: bytes) -> None:
    common.relative_path(name)
    info=zipfile.ZipInfo(name,date_time=(2026,9,18,0,0,0))
    info.external_attr=0o100644<<16
    info.compress_type=zipfile.ZIP_DEFLATED
    z.writestr(info,data)


def release_payloads(root: Path = ROOT) -> dict[str,dict[str,bytes]]:
    version=common.version(root)
    for dirname in ('plugin','chatgpt','core','templates','scripts','sources','docs'):
        common.list_tree(root,root/dirname)
    expected=render_outputs(root)
    for rel,data in expected.items():
        if common.read_bytes(root,rel)!=data:
            raise ValueError('Stale generated file; build and validate first: '+rel)
    for dirname in ('plugin','chatgpt'):
        extras=[p.relative_to(root).as_posix() for p in common.list_tree(root,root/dirname)
                if p.relative_to(root).as_posix() not in expected]
        if extras:
            raise ValueError('Unexpected runtime files: '+', '.join(extras))
    allow=common.load(root,'release-files.json')
    paths=allow['authored_files']
    if len(paths)!=len(set(paths)):
        raise ValueError('Duplicate release allowlist entry')
    # Raw run records may contain user input. Never silently publish them.
    if common.load(root,'evals/execution-status.json')['model_runs']:
        raise ValueError('Run records are private: create a reviewed, redacted release snapshot before packaging')
    repository=dict(expected)
    for rel in paths:
        common.relative_path(rel)
        if rel in expected:
            raise ValueError('Authored allowlist overlaps generated output: '+rel)
        if rel.startswith(('private/','evals/results/')) or Path(rel).name.startswith('.env'):
            raise ValueError('Private file cannot be allowlisted: '+rel)
        repository[rel]=common.read_bytes(root,rel)
    repository['release-files.json']=common.read_bytes(root,'release-files.json')
    chatgpt={rel.removeprefix('chatgpt/'):data for rel,data in expected.items() if rel.startswith('chatgpt/')}
    chatgpt.update({rel:data for rel,data in expected.items() if rel.startswith('plugin/')})
    chatgpt['.agents/plugins/marketplace.json']=expected['.agents/plugins/marketplace.json']
    for source,target in [('NOTICE.md','NOTICE.md'),('docs/00_DELIVERY_REPORT.md','DELIVERY_REPORT.md'),('docs/05_OFFICIAL_SOURCES.md','OFFICIAL_SOURCES.md'),('docs/06_FIX_REPORT.md','FIX_REPORT.md')]:
        text=common.read_text(root,source)
        if source.endswith('DELIVERY_REPORT.md'):
            text=text.replace('`docs/06_FIX_REPORT.md`','`FIX_REPORT.md`').replace('`chatgpt/00_START_HERE.md`','`00_START_HERE.md`').replace('`docs/03_INSTALL_AGENTS.md`','별도 저장소 패키지의 `docs/03_INSTALL_AGENTS.md`')
        chatgpt[target]=text.encode('utf-8')
    chatgpt['SETUP_DETAILS.md']=expected['docs/04_CHATGPT_SETUP.md'].decode().replace('chatgpt/','').replace('docs/05_OFFICIAL_SOURCES.md','OFFICIAL_SOURCES.md').encode()
    chatgpt['README.md']=expected['chatgpt/00_START_HERE.md']
    for payload in (repository,chatgpt):
        payload['RELEASE_MANIFEST.json']=common.json_text({
            'version':version,'hash_algorithm':'sha256',
            'files':{p:common.sha256(data) for p,data in sorted(payload.items())},
            'scope':'Local file integrity only; no host or semantic quality certification',
            'self_excluded':True}).encode()
    return {f'ben-ux-writing-os-v{version}':repository,
            f'chihun-chatgpt-v{version}':chatgpt}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'dist')
    parser.add_argument('--replace',action='store_true',help='Explicitly replace existing local archives')
    args=parser.parse_args()
    # Validate before creating the output directory or an archive.
    payloads=release_payloads(ROOT)
    out=args.output.expanduser().absolute()
    parent=out
    while not parent.exists():parent=parent.parent
    common.checked_path(parent.resolve(),out)
    out.mkdir(parents=True,exist_ok=True)
    out=out.resolve()
    for name in payloads:
        dest=out/(name+'.zip');common.checked_path(out,dest)
        if dest.exists() and not args.replace:
            raise ValueError('Archive already exists; use --replace after review: '+str(dest))
    artifacts=[]
    for name,files in payloads.items():
        dest=out/(name+'.zip')
        with tempfile.NamedTemporaryFile(prefix='.chihun-archive-',suffix='.zip',dir=out,delete=False) as temp:
            stage=Path(temp.name)
        try:
            with zipfile.ZipFile(stage,'w') as z:
                for rel,data in sorted(files.items()):add(z,name+'/'+rel,data)
            with zipfile.ZipFile(stage) as z:
                if z.testzip() is not None:raise ValueError('Archive CRC failure')
                if len(z.infolist())!=len(files):raise ValueError('Archive membership mismatch')
            common.checked_path(out,dest)
            os.replace(stage,dest)
        finally:
            stage.unlink(missing_ok=True)
        artifacts.append({'file':dest.name,'bytes':dest.stat().st_size,
                          'sha256':common.sha256(dest.read_bytes()),'entries':len(files)})
    print(common.json_text({'artifacts':artifacts,'published':False,'installed':False}))
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,KeyError) as exc:
        print(f'Packaging stopped: {exc}',file=sys.stderr);raise SystemExit(1)
