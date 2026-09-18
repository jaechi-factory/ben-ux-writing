#!/usr/bin/env python3
"""Local integration smoke tests in temporary directories; never invokes a model."""
from __future__ import annotations
import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PYTHON=sys.executable

def run(args:list[str],expected:int=0):
 p=subprocess.run([PYTHON,str(ROOT/'scripts/install.py'),*args],capture_output=True,text=True)
 if (expected==0 and p.returncode!=0) or (expected!=0 and p.returncode==0):raise AssertionError(p.stdout+'\n'+p.stderr)
 return p

def main():
 checks=[]
 def passed(s):checks.append({'check':s,'result':'pass'})
 with tempfile.TemporaryDirectory(prefix='chihun-test-') as temp:
  base=Path(temp)/'project with spaces';base.mkdir()
  args=['--target','both','--scope','project','--project',str(base)]
  run(args)
  assert not (base/'.agents').exists() and not (base/'.claude').exists();passed('dry_run_has_no_writes')
  run([*args,'--apply']);passed('fresh_dual_host_copy')
  source=ROOT/'plugin/skills/ben.lee-ux-writing'
  for host in ['.agents','.claude']:
   target=base/host/'skills/ben.lee-ux-writing'
   for f in source.rglob('*'):
    if f.is_file():assert (target/f.relative_to(source)).read_bytes()==f.read_bytes()
  passed('all_skill_files_and_references_identical')
  run([*args,'--apply'],expected=1);passed('existing_install_preserved_by_default')
  marker=base/'.claude/skills/ben.lee-ux-writing/USER_EDIT.txt';marker.write_text('keep this edit')
  run([*args,'--apply','--replace-with-backup'])
  backups=list((base/'.chihun-skill-backups/claude').rglob('USER_EDIT.txt'))
  assert len(backups)==1 and backups[0].read_text()=='keep this edit'
  assert not marker.exists();passed('update_retains_user_edits_in_backup')
  assert not list((base/'.chihun-install-staging').rglob('SKILL.md'));passed('staging_outside_discovery_and_empty_after_success')
  # Existing destination for either target prevents writes to all targets.
  p2=Path(temp)/'preflight';(p2/'.claude/skills/ben.lee-ux-writing').mkdir(parents=True)
  run(['--target','both','--scope','project','--project',str(p2),'--apply'],expected=1)
  assert not (p2/'.agents').exists();passed('all_targets_preflight_before_write')
  run(['--target','codex','--scope','project','--project',str(Path(temp)/'missing'),'--apply'],expected=1);passed('missing_project_rejected')
  p3=Path(temp)/'symlink';(p3/'.agents/skills').mkdir(parents=True)
  real=Path(temp)/'existing-user-data';real.mkdir();(real/'marker').write_text('untouched')
  (p3/'.agents/skills/ben.lee-ux-writing').symlink_to(real,target_is_directory=True)
  run(['--target','codex','--scope','project','--project',str(p3),'--apply','--replace-with-backup'],expected=1)
  assert (real/'marker').read_text()=='untouched';passed('symlink_destination_rejected')
 # Generated output is deterministic for identical canonical inputs.
 manifest=(ROOT/'build-manifest.json').read_bytes()
 subprocess.run([PYTHON,str(ROOT/'scripts/build.py')],check=True,capture_output=True,text=True)
 assert (ROOT/'build-manifest.json').read_bytes()==manifest;passed('deterministic_rebuild')
 report={'version':(ROOT/'VERSION').read_text().strip(),'kind':'local_package_smoke_tests','result':'pass','tests_passed':len(checks),'tests_total':len(checks),'environment':'Python standard library on Linux; temporary directories only','tests':checks,'not_tested':['actual Codex/Claude execution','actual ChatGPT installation','Windows/macOS execution','semantic copy quality','GitHub publication']}
 (ROOT/'verification').mkdir(exist_ok=True)
 (ROOT/'verification/installer.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
