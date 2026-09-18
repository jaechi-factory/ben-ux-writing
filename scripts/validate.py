#!/usr/bin/env python3
"""Static integrity validation, not an LLM quality evaluation. Standard library only."""
from __future__ import annotations
import argparse,hashlib,json,re,sys
import common
from build import render_outputs
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return common.read_text(ROOT,p)
def load(p):return json.loads(read(p))
def rows(p):return [json.loads(x) for x in read(p).splitlines() if x.strip()]
def walk(obj):
 if isinstance(obj,dict):
  yield obj
  for v in obj.values():yield from walk(v)
 elif isinstance(obj,list):
  for v in obj:yield from walk(v)
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--source',type=Path)
 ap.add_argument('--report',type=Path)
 args=ap.parse_args();checks=[];errors=[]
 def check(name,condition,detail=''):
  checks.append({'check':name,'result':'pass' if condition else 'fail','detail':detail})
  if not condition:errors.append(name+(': '+detail if detail else ''))
 version=read('VERSION').strip();manifest=load('sources/source-manifest.json')
 json_count=0;objects=[]
 for base in ['core','evals','sources','plugin','templates']:
  for f in common.list_tree(ROOT,ROOT/base):
   if not f.is_file() or f.suffix not in ['.json','.jsonl']:continue
   try:
    obj=[json.loads(l) for l in read(f.relative_to(ROOT).as_posix()).splitlines() if l.strip()] if f.suffix=='.jsonl' else json.loads(read(f.relative_to(ROOT).as_posix()))
    objects.extend(walk(obj));json_count+=1
   except (ValueError,UnicodeError) as exc:errors.append(f'{f.relative_to(ROOT)}: {exc}')
 check('json_and_jsonl_parse',not errors,f'{json_count} files parsed')
 rules=load('core/rules.json')['rules'];ids={r['id'] for r in rules}
 check('unique_rule_ids',len(ids)==len(rules),str(len(rules)))
 required={'id','title','statement','source_type','status','source_refs','operationalization'}
 check('rule_fields',all(required<=set(r) and {'applies_when','does_not_apply_when','fails_when'}<=set(r['operationalization']) for r in rules))
 missing=[x for obj in objects for x in obj.get('rule_ids',[]) if x not in ids]
 check('rule_reference_integrity',not missing,','.join(missing))
 section_map=rows('sources/section-map.jsonl');sections={s['section']:s for s in section_map}
 check('all_source_sections_indexed',set(sections)==set(range(130)) and len(section_map)==130)
 bad_refs=[]
 for obj in objects:
  if obj.get('source_id')=='MASTER_V1' and 'section' in obj:
   sec=sections.get(obj['section']);lo=obj.get('line_start');hi=obj.get('line_end')
   if not sec or not isinstance(lo,int) or not isinstance(hi,int) or not (sec['line_start']<=lo<=hi<=sec['line_end']):bad_refs.append(obj)
 check('source_reference_ranges',not bad_refs,str(bad_refs[:2]))
 for path,count,key in [('core/preference-corpus.jsonl',12,'main_gold'),('core/additional-source-pairs.jsonl',8,'additional_source_pairs'),('core/source-synthetic.jsonl',20,'source_synthetic')]:
  vals=rows(path);check(key+'_count_and_unique_ids',len(vals)==count and len({x['id'] for x in vals})==count)
 check('unknown_feedback_provenance_not_fabricated',all(x['user_reason'] is None and x['independent_feedback_events'] is None for x in rows('core/preference-corpus.jsonl')))
 score=load('core/score.json')
 check('original_score_total_and_threshold',sum(x['max'] for x in score['items'])==100 and score['threshold']==90 and score['hard_fail_overrides_score'])
 check('original_hard_fail_count',len(load('core/hard-fails.json'))==15)
 skill=ROOT/'plugin/skills/ben-ux-writing';skill_text=(skill/'SKILL.md').read_text(encoding='utf-8')
 fm=re.match(r'^---\n(.*?)\n---\n',skill_text,re.S)
 check('skill_metadata',bool(fm and re.search(r'^name: ben-ux-writing$',fm.group(1),re.M) and re.search(r'^description: .+',fm.group(1),re.M)))
 check('skill_body_under_500_lines',len(skill_text.splitlines())<500,str(len(skill_text.splitlines())))
 link_errors=[]
 for f in skill.rglob('*.md'):
  for target in re.findall(r'\]\(([^)]+)\)',read(f.relative_to(ROOT).as_posix())):
   if '://' in target or target.startswith(('mailto:','#')):continue
   path=target.split('#')[0]
   if path and not (f.parent/path).resolve().exists():link_errors.append(f'{f.relative_to(ROOT)} -> {target}')
 check('skill_local_markdown_links',not link_errors,'; '.join(link_errors))
 check('eight_module_reference_files',all((skill/'references'/name).is_file() for name in ['01_CONSTITUTION.md','02_DECISION_ENGINE.md','03_SURFACE_SPEC.md','04_DOMAIN_SPEC.md','05_PREFERENCE_CORPUS.md','06_ANTI_PATTERN_LIBRARY.md','07_EVALUATOR.md','08_BENCHMARK.md']))
 plugin=load('plugin/plugin.json')
 check('plugin_minimal_documented_fields',plugin.get('name')=='ben-ux-writing' and plugin.get('version')==version and isinstance(plugin.get('description'),str) and plugin.get('$schema')=='https://agent-plugins.org/schemas/1.0.0/plugin.schema.json','Local required-field check, not remote schema certification')
 market=load('.agents/plugins/marketplace.json');entry=market['plugins'][0]
 check('marketplace_path',entry['source']['path']=='./plugin' and (ROOT/entry['source']['path']/'plugin.json').is_file())
 build=load('build-manifest.json');drift=[]
 for group in ['core_sources','outputs']:
  for path,digest in build[group].items():
   f=ROOT/path
   if not f.is_file() or common.sha256(common.read_bytes(ROOT,path))!=digest:drift.append(path)
 check('generated_files_match_canonical_sources',not drift,'; '.join(drift))
 check('version_alignment',build['version']==version==load('plugin/skills/ben-ux-writing/references/RULE_REGISTRY.json')['version'] and (skill/'references/VERSION').read_text().strip()==version)
 cases=rows('evals/development-cases.jsonl');inputs=rows('evals/inputs.jsonl');rubrics=rows('evals/rubrics.jsonl')
 check('development_cases_separated',len(cases)>=20 and {c['id'] for c in cases}=={c['id'] for c in inputs}=={c['id'] for c in rubrics} and all('rubric' not in c for c in inputs))
 check('development_provenance_not_blind_or_gold',all(c['split']=='development' and not c['gold_status'] for c in cases) and load('evals/status.json')['blind_test_claim'] is False)
 runtimes='\n'.join(read(f.relative_to(ROOT).as_posix()) for f in skill.rglob('*') if f.is_file())
 knowledge=read(f'chatgpt/CHIHUN_KNOWLEDGE_{version}.md')
 check('no_development_answers_in_runtime',not re.search(r'DEV-\d{3}',runtimes+knowledge))
 check('project_instruction_budget',len(read('chatgpt/PROJECT_INSTRUCTIONS.md'))<8000,str(len(read('chatgpt/PROJECT_INSTRUCTIONS.md')))+' characters; local conservative budget, not asserted product limit')
 check('no_source_copy_in_distribution',not any(f.name=='master-v1.0.md' for base in [ROOT/'plugin',ROOT/'chatgpt'] for f in base.rglob('*')))
 check('no_runtime_shell_hooks_or_mcp',not any(f.name in ['mcp.json','.mcp.json','hooks.json'] for f in (ROOT/'plugin').rglob('*')) and not re.search(r'^!`',skill_text,re.M))
 # Additional v0.1.1 checks: semantic correspondence and exact projections.
 contract_issues=common.contract_errors(ROOT)
 check('evaluator_semantics_match_source_contracts',not contract_issues,'; '.join(contract_issues))
 try:
  expected=render_outputs(ROOT)
  changed=[p for p,data in expected.items() if not (ROOT/p).is_file() or common.read_bytes(ROOT,p)!=data]
  check('pure_rebuild_matches_every_generated_byte',not changed,', '.join(changed))
  extras=[p.relative_to(ROOT).as_posix() for tree in ('plugin','chatgpt') for p in common.list_tree(ROOT,ROOT/tree) if p.relative_to(ROOT).as_posix() not in expected]
  check('generated_trees_have_no_unlisted_or_old_files',not extras,', '.join(extras))
 except (ValueError,OSError,KeyError) as exc:
  check('pure_rebuild_matches_every_generated_byte',False,str(exc))
  check('generated_trees_have_no_unlisted_or_old_files',False,'Rebuild projection unavailable')
 check('writer_inputs_exactly_projected',inputs==[common.input_projection(c) for c in cases])
 check('grader_rubrics_exactly_projected',rubrics==[common.rubric_projection(c) for c in cases])
 check('single_current_knowledge_file',sorted(p.name for p in (ROOT/'chatgpt').glob('CHIHUN_KNOWLEDGE_*.md'))==[f'CHIHUN_KNOWLEDGE_{version}.md'])
 check('start_guide_and_result_template_current',f'CHIHUN_KNOWLEDGE_{version}.md' in read('chatgpt/00_START_HERE.md') and load('evals/result-template.json')['skill_version']==version)
 check('rubrics_require_meaning_scope_unknowns',all({'must_include','evaluation_scope','unknown_handling'}<=set(c['rubric']) and c['rubric']['must_include'] and c['rubric']['evaluation_scope'] and c['rubric']['unknown_handling'] for c in cases))
 run_errors=[];run_ids=set();by_case={c['id']:c for c in cases}
 for record in load('evals/status.json')['model_runs']:
  # These are evidence declarations, not proof that an external model was run.
  required_run={'run_id','case_id','host','model','host_version','timestamp','input_sha256','skill_sha256','raw_input','raw_response','result','review_kind'}
  if not required_run<=set(record):run_errors.append('Missing run fields');continue
  if record['run_id'] in run_ids:run_errors.append('Duplicate run ID')
  run_ids.add(record['run_id'])
  if record['case_id'] not in by_case:run_errors.append('Unknown case ID');continue
  if record['input_sha256']!=common.sha256(common.canonical_bytes(record['raw_input'])):run_errors.append('Raw input/hash mismatch')
  if record['raw_input']!={k:by_case[record['case_id']][k] for k in common.INPUT_FIELDS}:run_errors.append('Run input differs from current case')
  if record['result'] not in ('completed','failed') or not isinstance(record['raw_response'],str):run_errors.append('Missing actual response/status')
  if not record['host'] or not record['model'] or not re.fullmatch(r'[0-9a-f]{64}',str(record['skill_sha256'])):run_errors.append('Run host/model/skill identity missing')
 check('declared_model_run_records_have_required_evidence',not run_errors,'; '.join(run_errors) or 'No external model runs declared; no performance claim')
 if args.source:
  raw=args.source.read_bytes();source=raw.decode('utf-8');source_lines=source.splitlines()
  check('original_source_sha256',hashlib.sha256(raw).hexdigest()==manifest['sha256'])
  check('original_source_lines',len(source_lines)==manifest['line_count'])
  failures=[]
  for obj in objects:
   if 'raw_excerpt' in obj and 'source_ref' in obj:
    rr=obj['source_ref'];segment='\n'.join(source_lines[rr['line_start']-1:rr['line_end']])
    if obj['raw_excerpt'] not in segment:failures.append(str(obj.get('id',rr.get('section'))))
  check('preserved_source_excerpt_fidelity',not failures,','.join(failures[:10]))
  anchors=[]
  for r in rules:
   for a in r['source_anchors']:
    rr=a['source_ref'];segment='\n'.join(source_lines[rr['line_start']-1:rr['line_end']])
    if a['excerpt'] not in segment:anchors.append(r['id'])
  check('rule_anchor_fidelity',not anchors,','.join(anchors))
 report={'version':version,'kind':'static_integrity_only','result':'pass' if not errors else 'fail','checks_passed':sum(x['result']=='pass' for x in checks),'checks_total':len(checks),'checks':checks,'errors':errors,'not_tested':['Codex discovery/invocation and copy quality','Claude Code discovery/invocation and copy quality','ChatGPT project/plugin behavior','plugin marketplace publication','human preference acceptance','statistical or blind benchmark performance']}
 if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if not errors else 1
if __name__=='__main__':
 try:raise SystemExit(main())
 except (OSError,ValueError,KeyError,TypeError) as exc:
  print(json.dumps({'result':'fail','error':str(exc),'kind':'static_integrity_only'},ensure_ascii=False,indent=2));raise SystemExit(1)
