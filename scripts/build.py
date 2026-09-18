#!/usr/bin/env python3
"""Build reproducible packages from canonical inputs, in a clean staging tree.

No installation, publishing, network or model execution. Authored sources are
not overwritten; managed outputs are swapped with rollback on ordinary errors.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
import common
from common import ROOT

def reftext(refs:list)->str:return '; '.join(f"MASTER_V1 §{r['section']} L{r['line_start']}–L{r['line_end']}" for r in refs)
def render_rule(r:dict)->str:
 o=r['operationalization']
 return '\n'.join([f"## {r['id']} · {r['title']}",r['statement'],f"출처: {reftext(r['source_refs'])}",'아래 적용·예외·실패 조건은 원문을 실행하기 위한 v0.1 해석 초안이에요.',f"적용: {o['applies_when']}",f"예외·경계: {o['does_not_apply_when']}",f"실패: {o['fails_when']}"])
def render_evaluator(root: Path) -> str:
    common.assert_contracts(root)
    score = common.load(root, 'core/score.json')
    fails = common.load(root, 'core/hard-fails.json')
    contracts = common.load(root, 'core/source-contracts.json')
    parts = [common.read_text(root, 'core/evaluator.md'),
             '# 원문과 항목별 대조를 통과한 실행 기준',
             '# 102. HARD FAIL CONDITIONS', '다음 중 하나라도 발생하면 재작성한다.']
    for item in fails:
        parts += ['### ' + item['id'], item['statement_raw']]
    parts += ['# 103. QUALITY SCORE', str(score['maximum']) + '점 기준.']
    table = ['| 항목 | 배점 |', '| --- | --- |']
    table += ['| ' + x['label'] + ' | ' + str(x['max']) + ' |' for x in score['items']]
    parts.append('\n'.join(table))
    parts += [str(score['threshold']) + '점 미만이면 재작성한다.',
              'Hard Fail은 점수와 관계없이 재작성한다.', contracts['104']['raw_excerpt']]
    return '\n\n'.join(parts)


def render_outputs(root: Path = ROOT) -> dict[str, bytes]:
    common.assert_contracts(root)
    for dirname in ('core','templates','sources','scripts'):
        common.list_tree(root, root / dirname)
    outputs: dict[str, bytes] = {}
    ROOT = root
    authorized=set(common.load(root,'release-files.json')['authored_files']) | {'release-files.json','VERSION'}
    def read(p):
        if p not in authorized:raise ValueError('Unlisted build input: '+p)
        return common.read_text(root,p)
    load = lambda p: json.loads(read(p))
    rows = lambda p: [json.loads(line) for line in read(p).splitlines() if line.strip()]
    cases = rows('evals/development-cases.jsonl')
    if len({c['id'] for c in cases}) != len(cases):
        raise ValueError('Duplicate development case IDs')
    def write(path: Path, value: str) -> None:
        rel = path.relative_to(root).as_posix()
        common.relative_path(rel)
        outputs[rel] = (value.strip()+'\n').encode('utf-8')
    version=common.version(root);rules=load('core/rules.json')['rules'];contracts=load('core/source-contracts.json')
    skill=ROOT/'plugin/skills/ben.lee-ux-writing';refs=skill/'references'
    manifest={'$schema':'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json','name':'ben.lee-ux-writing','version':version,'description':'CHIHUN 기준의 한국어 제품 문구 작성·워싱·피드백. 개발 초안.'}
    write(ROOT/'plugin/plugin.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    write(ROOT/'.agents/plugins/marketplace.json',json.dumps({'name':'ben.lee-ux-writing-local','plugins':[{'name':'ben.lee-ux-writing','source':{'source':'local','path':'./plugin'},'policy':{'installation':'AVAILABLE','authentication':'ON_INSTALL'},'category':'Productivity'}]},ensure_ascii=False,indent=2))
    write(skill/'SKILL.md',read('templates/skill.md').replace('{{VERSION}}',version))
    write(skill/'agents/openai.yaml','''interface:
  display_name: "CHIHUN UX Writing"
  short_description: "제품 문구 작성·워싱·피드백, 유지·삭제·재설계 판단"
  default_prompt: "CHIHUN 기준으로 이 제품 문구를 검토해 주세요. 적절한 문구는 유지해 주세요."
''')
    common_rules=[r for r in rules if 'core' in r['modules']]
    constitution='# 01 · CONSTITUTION\n\n버전 '+version+' · 자동 생성본. 수정은 core 원본에서 해요.\n\n원문 기준의 요약과 실행 규칙을 연결해요. 원문의 모든 절을 대체하지 않아요.\n\n'+contracts['1']['raw_excerpt']+'\n\n'+contracts['129']['raw_excerpt']+'\n\n'+'\n\n'.join(render_rule(r) for r in common_rules)
    write(refs/'01_CONSTITUTION.md',constitution)
    write(refs/'02_DECISION_ENGINE.md',read('core/decision-engine.md'))
    surface=['# 03 · SURFACE SPEC','도메인·컨테이너·요소·상태를 별도로 조합해요. 고정 글자 수나 단어 금지로 평가하지 않아요. 화면 분류의 실행 축은 v0.1 설계이고 개별 기준은 원문에 연결돼요.']
    for s in load('core/surfaces.json'):
        surface.extend([f"## {s['id']} ({s['axis']})",f"목표: {s['goal']}",f"필요 정보: {s['required']}",f"피할 것: {s['avoid']}",f"출처: {reftext(s['source_refs'])}",f"규칙: {', '.join(s['rule_ids'])}"])
    for r in rules:
        if any(m in r['modules'] for m in ['surface','cta','form']):surface.append(render_rule(r))
    write(refs/'03_SURFACE_SPEC.md','\n\n'.join(surface))
    domain=['# 04 · DOMAIN SPEC','지원 범위는 특정 작업이며 도메인 전체 검증을 뜻하지 않아요. 아래 질문은 원문에서 재구성한 예상 질문이지 별도 사용자 조사 결과가 아니에요.']
    for d in load('core/domains.json'):
        domain.extend([f"## {d['id']}",f"작업 범위: {d['task_scope']}",f"질문: {' / '.join(d['questions'])}",f"확인할 사실: {', '.join(d['facts_needed'])}",f"출처: {reftext(d['source_refs'])}",f"규칙: {', '.join(d['rule_ids'])}"])
    for r in rules:
        if not 'core' in r['modules'] and any(m in r['modules'] for m in ['kyc','payment','subscription','challenge','authentication']):domain.append(render_rule(r))
    write(refs/'04_DOMAIN_SPEC.md','\n\n'.join(domain))
    prefs=['# 05 · PREFERENCE CORPUS','원문 #98의 GOLD-001~012를 원문 그대로 보존해요. 원문이 GOLD라고 명시했다는 사실을 보존하며, 원래 피드백 대화를 따로 검증한 것은 아니에요. user_reason과 독립 피드백 수는 제공되지 않아 null이에요. 아래 예시의 숫자·날짜·기관·조건은 현재 제품 사실이 아니에요.','원문 #109~111 출처 가중치와 승격 기준:']
    prefs.extend(contracts[str(n)]['raw_excerpt'] for n in [109,110,111])
    for p in rows('core/preference-corpus.jsonl'):
        prefs.extend([f"출처: {reftext([p['source_ref']])} · 도메인: {p['domain']} · 묶음: {p['lineage_group']}",p['raw_excerpt']])
    prefs.append('다른 GOLD 표시 8개는 05_ADDITIONAL_SOURCE_PAIRS.jsonl, 원문 Synthetic 20개는 05_SOURCE_SYNTHETIC.jsonl에 별도 보존해요. 독립적인 선호 건수로 합산하지 않고, 필요한 맥락에서만 읽어요. 새 개발용 시험은 여기 포함하지 않아요.')
    write(refs/'05_PREFERENCE_CORPUS.md','\n\n'.join(prefs))
    write(refs/'05_ADDITIONAL_SOURCE_PAIRS.jsonl',read('core/additional-source-pairs.jsonl'))
    write(refs/'05_SOURCE_SYNTHETIC.jsonl',read('core/source-synthetic.jsonl'))
    anti=['# 06 · ANTI-PATTERN LIBRARY','단어가 아니라 실패 유형이에요. 원문 예외·현재 상태·주변 UI를 먼저 확인해요.']
    for a in load('core/anti-patterns.json'):anti.extend([f"## {a['id']}",a['failure_type'],f"규칙: {', '.join(a['rule_ids'])}",f"출처: {reftext(a['source_refs'])}"])
    write(refs/'06_ANTI_PATTERN_LIBRARY.md','\n\n'.join(anti))
    evaluator=render_evaluator(root)
    write(refs/'07_EVALUATOR.md',evaluator)
    write(refs/'08_BENCHMARK.md','# 08 · BENCHMARK 경계\n\n이 실행 패키지에는 시험 입력과 정답을 넣지 않아요. 저장소의 evals/에 개발용 '+str(len(cases))+'개와 입력/평가 기준을 분리해 두었어요. 모두 미실행이며 블라인드·회귀 성능이 검증된 상태가 아니에요. 구조 검사 통과는 모델 품질 검증이 아니에요. 실제 모델·호스트 버전별로 별도 실행하고 사람의 수용 판단과 대조해야 해요.')
    write(refs/'09_REFERENCE_LIBRARY.md','# 09 · REFERENCE LIBRARY\n\n원문은 Master v1.0, 4,304줄, #0~129의 130개 절이에요. 원문 전체를 설치 패키지에 포함하지 않았어요. 전체 절의 분류는 SOURCE_MAP.jsonl에 있고, 추출된 규칙·사례에 원문 줄 번호를 유지해요. 지도에 있다는 이유로 해당 절의 세부 내용을 읽었다고 주장하지 않아요. 상세 원문이 필요하고 제공되지 않았다면 사용자에게 필요한 근거를 요청하거나 제안 범위를 제한해요.\n\nOVERRIDE ORDER 원문은 SOURCE_CONTRACTS.json에 보존돼요. 실행 해석과 원문을 구분하세요.')
    write(refs/'OUTPUT_CONTRACT.md',read('core/output-contract.md'))
    write(refs/'RULE_REGISTRY.json',common.json_text({'version':version,**load('core/rules.json')}))
    write(refs/'SOURCE_MAP.jsonl',read('sources/section-map.jsonl'))
    write(refs/'SOURCE_CONTRACTS.json',read('core/source-contracts.json'))
    write(refs/'VERSION',version)
    # Common skill payload is reused by ChatGPT plugin, Codex and Claude Code installations.
    cg=ROOT/'chatgpt'
    instructions=read('templates/project-instructions.md').replace('{{VERSION}}',version)
    write(cg/'PROJECT_INSTRUCTIONS.md',instructions)
    knowledge=['# CHIHUN UX Writing OS · '+version,'프로젝트 첨부용 기준 파일이에요. core 원본에서 자동 생성했어요. 전체 원문을 그대로 옮긴 것이 아니라 첫 실행 범위에 필요한 기준과 원문 사례를 연결했어요. 원문과 추가 해석의 구분을 유지해요. 시험 정답은 포함하지 않아요.']
    for f in ['01_CONSTITUTION.md','02_DECISION_ENGINE.md','03_SURFACE_SPEC.md','04_DOMAIN_SPEC.md','05_PREFERENCE_CORPUS.md','06_ANTI_PATTERN_LIBRARY.md','07_EVALUATOR.md','OUTPUT_CONTRACT.md']:
        knowledge.append(outputs[(refs/f).relative_to(ROOT).as_posix()].decode('utf-8'))
    # Include all source example materials in readable form, with exact origin labels.
    knowledge.append('# 원문 우선순위 보존 — 실행 해석과 구분')
    knowledge.append(contracts['112']['raw_excerpt'])
    knowledge.append('위 원문 순서는 변경하지 않았어요. 사실·필수 의미를 보존한 범위에서 현재 요청과 선호를 적용하는 것은 앞의 판단 엔진에서 설명한 v0.1 운영 해석이에요. 이 목록을 호스트 시스템의 권한·안전 규칙보다 우선시키지 않아요.')
    knowledge.append('# 추가 원문 표시 사례 — 독립 피드백 수로 합산하지 않음')
    for p in rows('core/additional-source-pairs.jsonl'):
        knowledge.extend([reftext([p['source_ref']]),p['raw_excerpt']])
    knowledge.append('# 원문 #99 Synthetic 보존 — 새 제품 사실이 아님')
    for p in rows('core/source-synthetic.jsonl'):
        knowledge.extend([reftext([p['source_ref']]),p['raw_excerpt']])
    # ChatGPT users should not be sent to absent local runtime reference paths.
    knowledge_text='\n\n'.join(knowledge)
    for old,new in [('07_EVALUATOR.md','이 파일의 07 · EVALUATOR 절'),('docs/02_DECISIONS_AND_BOUNDARIES.md','저장소의 docs/02_DECISIONS_AND_BOUNDARIES.md'),('05_ADDITIONAL_SOURCE_PAIRS.jsonl','이 파일의 추가 원문 표시 사례 절'),('05_SOURCE_SYNTHETIC.jsonl','이 파일의 원문 #99 Synthetic 보존 절')]:knowledge_text=knowledge_text.replace(old,new)
    write(cg/f'CHIHUN_KNOWLEDGE_{version}.md',knowledge_text)
    write(cg/'SINGLE_CHAT_STARTER.md',instructions+'\n\n---\n\n'+knowledge_text+'\n\n---\n\n이제 사용자가 제공하는 실제 문구와 제품 조건을 기다려요. 위 예시로 결과를 미리 생성하지 않아요.')
    write(cg/'REQUEST_EXAMPLES.md','''# 요청 예시

## 워싱
아래 문구를 CHIHUN 기준으로 워싱해 주세요. 적절한 문구는 유지하고 수정안과 중요한 이유만 보여주세요.
[문구/화면]
[확인된 상태와 제품 조건]

## 수정안만
아래 문구를 워싱해 주세요. 수정안만 주세요. 없는 원인·기한·기능은 만들지 마세요.
[문구]
[필요한 조건]

## 피드백
이 화면을 검토해 주세요. 문구 문제와 UI/상태 표시 문제를 구분하고, 수정·유지·삭제·재설계를 요소별로 판단해 주세요.
[화면과 조건]

## 작성
아래 조건에 맞는 제목·본문·버튼을 작성해 주세요. 필요한 요소만 만들고 중요한 미확인 사항은 표시해 주세요.
[조건]

## 에이전트에서 읽기 전용 검토
CHIHUN 기준으로 이 파일의 문구를 검토해 주세요. 파일은 아직 수정하지 말고 수정안과 근거를 먼저 보여주세요.
[파일 경로]
''')
    outputs['evals/inputs.jsonl'] = common.jsonl_bytes([common.input_projection(c) for c in cases])
    outputs['evals/rubrics.jsonl'] = common.jsonl_bytes([common.rubric_projection(c) for c in cases])
    write(root/'evals/result-template.json', read('templates/eval-result.json').replace('{{VERSION}}',version))
    status = load('evals/execution-status.json')
    write(root/'evals/status.json', common.json_text({'version':version,'case_count':len(cases),**status}))
    doc_templates=load('templates/generated-docs.json')
    if set(doc_templates) != {'README.md','chatgpt/00_START_HERE.md','docs/03_INSTALL_AGENTS.md','docs/04_CHATGPT_SETUP.md','evals/README.md'}:
        raise ValueError('Unexpected managed documentation target')
    for target, template in doc_templates.items():
        common.relative_path(target)
        text = read(template).replace('{{VERSION}}',version).replace('{{CASE_COUNT}}',str(len(cases)))
        write(root / target, text)
    source_paths = ['VERSION','evals/development-cases.jsonl','evals/execution-status.json','release-files.json']
    # An unrelated working file must not become an implicit build dependency.
    allowed_sources = load('release-files.json')['authored_files']
    source_paths += [p for p in allowed_sources if p.split('/')[0] in ('core','templates','sources','scripts')]
    source_paths = sorted(set(source_paths))
    hashes = {p:common.sha256(common.read_bytes(root,p)) for p in sorted(source_paths)}
    manifest = {'version':version,'generated_by':'scripts/build.py',
                'core_sources':hashes,
                'outputs':{p:common.sha256(data) for p,data in sorted(outputs.items())},
                'model_evaluation':'not_run' if not status['model_runs'] else 'see_evaluation_records',
                'installed_to_user_environment':False}
    write(root/'build-manifest.json',common.json_text(manifest))
    return outputs


def commit_outputs(root: Path, outputs: dict[str,bytes]) -> None:
    """Publish managed directories cleanly; roll back normal write/rename errors."""
    old_files: set[str] = set()
    if (root/'build-manifest.json').exists():
        old = common.load(root, 'build-manifest.json')
        old_files.update(old.get('outputs', {}))
    old_files.update(('chatgpt/00_START_HERE.md','plugin/plugin.json','.agents/plugins/marketplace.json'))
    trees = ('plugin','chatgpt')
    for tree in trees:
        path=root/tree
        common.checked_path(root,path)
        if path.exists():
            for f in common.list_tree(root,path):
                rel=f.relative_to(root).as_posix()
                if rel not in old_files and rel not in outputs:
                    raise ValueError('Unmanaged file in generated tree; move it before build: '+rel)
    for rel in outputs:
        common.checked_path(root,root/common.relative_path(rel))
    lock=root/'.chihun-build.lock'
    common.checked_path(root,lock)
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os,'O_NOFOLLOW',0),0o600)
    os.close(fd)
    changes=[]
    staging=Path(tempfile.mkdtemp(prefix='.chihun-build-',dir=root))
    retain_recovery=False
    try:
        stage=staging/'new';backup=staging/'old';stage.mkdir();backup.mkdir()
        for rel,data in outputs.items():
            p=stage/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        units=[root/t for t in trees]
        units += [root/rel for rel in outputs if rel.split('/')[0] not in trees]
        units.sort(key=lambda p:p.name=='build-manifest.json')
        try:
            for dest in units:
                rel=dest.relative_to(root);fresh=stage/rel;saved=backup/rel
                common.checked_path(root,dest)
                dest.parent.mkdir(parents=True,exist_ok=True)
                saved.parent.mkdir(parents=True,exist_ok=True)
                entry={'dest':dest,'saved':saved,'backed':False,'committed':False}
                changes.append(entry)
                if dest.exists():
                    os.replace(dest,saved);entry['backed']=True
                os.replace(fresh,dest);entry['committed']=True
        except BaseException as original_error:
            recovery_errors=[]
            for entry in reversed(changes):
                try:
                    dest=entry['dest']
                    common.checked_path(root,dest)
                    if entry['committed']:
                        if dest.is_dir():shutil.rmtree(dest)
                        elif dest.exists():dest.unlink()
                    if entry['backed']:os.replace(entry['saved'],dest)
                except Exception as restore_error:
                    recovery_errors.append(str(restore_error))
            if recovery_errors:
                retain_recovery=True
                raise RuntimeError('Build rollback incomplete. Recovery files retained at '+str(staging)+'; '+'; '.join(recovery_errors)) from original_error
            raise
    finally:
        if not retain_recovery:shutil.rmtree(staging)
        common.checked_path(root,lock);lock.unlink(missing_ok=True)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Compare without changing files')
    args=parser.parse_args()
    outputs=render_outputs(ROOT)
    if args.check:
        different=[p for p,data in outputs.items() if not (ROOT/p).is_file() or common.read_bytes(ROOT,p)!=data]
        for tree in ('plugin','chatgpt'):
            different.extend(p.relative_to(ROOT).as_posix() for p in common.list_tree(ROOT,ROOT/tree)
                             if p.relative_to(ROOT).as_posix() not in outputs)
        if different:raise ValueError('Generated outputs differ: '+', '.join(different))
        print('Generated outputs exactly match canonical inputs.')
    else:
        commit_outputs(ROOT,outputs)
        print(f'Built {common.version(ROOT)}: {len(outputs)} generated files. No model calls or installation.')
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,KeyError,RuntimeError) as exc:
        print(f'Build stopped: {exc}',file=sys.stderr);raise SystemExit(1)
