#!/usr/bin/env python3
"""Prepare separated reviewer/writer workspaces. Does NOT invoke any agent.

Folder separation alone is not access control: open each workspace as the only
allowed root of a separate host sandbox. Review results are initially absent.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

import common
from common import ROOT
from build import render_outputs


def make_payloads(root: Path = ROOT) -> dict[str, bytes]:
    generated=render_outputs(root)
    for rel,data in generated.items():
        if common.read_bytes(root,rel)!=data:
            raise ValueError('Build before preparing review: '+rel)
    outputs={}
    skill_prefix='plugin/skills/ben-ux-writing/'
    skill={rel.removeprefix(skill_prefix):data for rel,data in generated.items() if rel.startswith(skill_prefix)}
    for role in ('writer','grader','source-reviewer'):
        for rel,data in skill.items():outputs[f'{role}/skill/{rel}']=data
    for item in common.rows(root,'evals/inputs.jsonl'):
        # Only task input: grading notes and expected interventions are absent.
        payload={k:item[k] for k in common.INPUT_FIELDS}
        outputs[f"writer/tasks/{item['id']}.json"]=common.json_text(payload).encode()
    outputs['writer/INPUT_HASHES.json']=common.json_text({i['id']:i['input_sha256'] for i in common.rows(root,'evals/inputs.jsonl')}).encode()
    outputs['grader/inputs.jsonl']=generated['evals/inputs.jsonl']
    outputs['grader/rubrics.jsonl']=generated['evals/rubrics.jsonl']
    outputs['grader/result-template.json']=generated['evals/result-template.json']
    for role,source in [('writer','WRITER.md'),('grader','GRADER.md'),('source-reviewer','SOURCE_REVIEWER.md'),('engineering-reviewer','ENGINEERING_REVIEWER.md')]:
        outputs[f'{role}/AGENTS.md']=common.read_bytes(root,'review/'+source)
        outputs[f'{role}/CLAUDE.md']=outputs[f'{role}/AGENTS.md']
    # Provide implementation and canonical materials, not existing audit verdicts.
    for rel in common.load(root,'release-files.json')['authored_files']:
        if rel.split('/')[0] in ('scripts','core','sources','templates') or rel in ('VERSION','release-files.json','evals/development-cases.jsonl','evals/execution-status.json'):
            outputs['engineering-reviewer/repository/'+rel]=common.read_bytes(root,rel)
    outputs['engineering-reviewer/repository/VERSION']=common.read_bytes(root,'VERSION')
    outputs['engineering-reviewer/repository/release-files.json']=common.read_bytes(root,'release-files.json')
    # Full source is intentionally not copied: reviewers attach it explicitly locally.
    for rel in ('sources/source-manifest.json','sources/section-map.jsonl'):
        outputs['source-reviewer/'+Path(rel).name]=common.read_bytes(root,rel)
    outputs['README.md']=common.read_bytes(root,'review/README.md')
    outputs['REVIEW_STATUS.json']=common.json_text({
        'version':common.version(root),'status':'prepared_not_executed',
        'independent_agent_runs':0,'model_quality_runs':0,
        'access_control':'Use separate host sandboxes; folders alone are not a boundary',
        'original_source_included':False,'prior_audit_verdicts_included':False,
        'files':{p:common.sha256(data) for p,data in sorted(outputs.items())}}).encode()
    return outputs


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',required=True,type=Path)
    a=ap.parse_args();dest=a.output.expanduser().absolute()
    if dest.exists() or dest.is_symlink():raise ValueError('Choose a new output directory; no overwrite')
    anchor=dest.parent
    while not anchor.exists():anchor=anchor.parent
    common.checked_path(anchor.resolve(),dest)
    payload=make_payloads(ROOT)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.chihun-review-',dir=dest.parent) as td:
        stage=Path(td)/'payload';stage.mkdir()
        for rel,data in payload.items():
            common.relative_path(rel);p=stage/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        common.checked_path(dest.parent.resolve(),dest)
        os.rename(stage,dest)
    print(common.json_text({'output':str(dest),'files':len(payload),'independent_agent_runs':0,'status':'prepared_not_executed'}))
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,KeyError) as exc:
        print(f'Review preparation stopped: {exc}',file=sys.stderr);raise SystemExit(1)
