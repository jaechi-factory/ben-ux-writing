#!/usr/bin/env python3
"""Offline regressions for the critical audit. Temporary fake data only.

These are engineering assertions, not independent agent or writing-quality tests.
The report records each executed test; failed tests make the process nonzero.
"""
from __future__ import annotations
import argparse
import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import common
from common import ROOT
import install
import build
import package

SOURCE: Path | None = None


def run(root: Path, script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable,str(root/'scripts'/script),*map(str,args)],
                          cwd=root,capture_output=True,text=True,timeout=40,
                          env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})


def writej(path: Path, obj) -> None:
    path.write_text(common.json_text(obj),encoding='utf-8')


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='chihun-fix-test-')
        self.base=Path(self.temp.name)
        self.project=self.base/'project';self.project.mkdir()
        self.outside=self.base/'outside';self.outside.mkdir()
        self.root=None
        self.source=ROOT/'plugin/skills/chihun-ux-writing'

    def tearDown(self):self.temp.cleanup()

    def fork(self) -> Path:
        if self.root is None:
            self.root=self.base/'repository'
            shutil.copytree(ROOT,self.root,ignore=shutil.ignore_patterns('__pycache__','.git','dist','*.zip'),symlinks=True)
        return self.root

    def rejected(self, result):
        self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)

    def ok(self, result):
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def validate(self, root):
        args=['--source',str(SOURCE)] if SOURCE else []
        return run(root,'validate.py',*args)

    def test_R01_parent_link_no_outside_write(self):
        (self.project/'.agents').symlink_to(self.outside,target_is_directory=True)
        self.rejected(run(ROOT,'install.py','--target','codex','--project',self.project,'--apply'))
        self.assertEqual(list(self.outside.iterdir()),[])
        self.assertFalse((self.project/'.chihun-install.lock').exists())

    def test_R02_invalid_second_parent_no_first_install(self):
        (self.project/'.claude').mkdir();(self.project/'.claude/skills').write_text('FAKE_FILE')
        self.rejected(run(ROOT,'install.py','--target','both','--project',self.project,'--apply'))
        self.assertFalse((self.project/'.agents').exists())
        self.assertEqual((self.project/'.claude/skills').read_text(),'FAKE_FILE')

    def test_R03_external_link_rejected_by_both_packages(self):
        root=self.fork();secret=self.outside/'fake.txt';secret.write_text('FAKE_NO_REAL_SECRET')
        (root/'plugin/skills/chihun-ux-writing/references/fake.txt').symlink_to(secret)
        self.rejected(run(root,'package.py','--output',self.base/'out'))
        self.assertFalse(list(self.base.glob('out/*.zip')))

    def test_R04_unknown_export_omitted_from_both_packages(self):
        root=self.fork();(root/'customer-export.csv').write_text('FAKE_USER,example.invalid')
        (root/'core/unused-export.txt').write_text('FAKE_WORKING_DATA')
        # Build deliberately sees canonical-tree changes, packaging still uses allowlist.
        self.ok(run(root,'build.py'))
        result=run(root,'package.py','--output',self.base/'out');self.ok(result)
        for archive in (self.base/'out').glob('*.zip'):
            with zipfile.ZipFile(archive) as z:
                self.assertFalse(any('customer-export' in n or 'unused-export' in n for n in z.namelist()))
                if archive.name.startswith('chihun-ux-writing-os-'):
                    z.extractall(self.base/'roundtrip')
                    self.ok(self.validate(self.base/'roundtrip'/archive.stem))

    def test_R05_score_mutation_stops_build_and_validate(self):
        root=self.fork();p=root/'core/score.json';obj=json.loads(p.read_text())
        obj['items'][0]['max']=14;obj['items'][1]['max']=16;writej(p,obj)
        before=(root/'plugin/skills/chihun-ux-writing/references/07_EVALUATOR.md').read_bytes()
        self.rejected(run(root,'build.py'));self.rejected(self.validate(root))
        self.assertEqual(before,(root/'plugin/skills/chihun-ux-writing/references/07_EVALUATOR.md').read_bytes())

    def test_R06_hard_fail_mutation_stops_build_and_validate(self):
        root=self.fork();p=root/'core/hard-fails.json';obj=json.loads(p.read_text())
        obj[0]['statement_raw']='FAKE_CHANGED_TEXT';writej(p,obj)
        self.rejected(run(root,'build.py'));self.rejected(self.validate(root))

    def test_R07_version_upgrade_cleans_previous_outputs(self):
        root=self.fork();old=common.version(root)
        major,minor,patch=old.split('.');new=f'{major}.{minor}.{int(patch)+1}'
        (root/'VERSION').write_text(new+'\n')
        self.ok(run(root,'build.py'));self.ok(self.validate(root))
        self.assertEqual([p.name for p in (root/'chatgpt').glob('CHIHUN_KNOWLEDGE_*.md')],['CHIHUN_KNOWLEDGE_'+new+'.md'])
        self.assertNotIn('CHIHUN_KNOWLEDGE_'+old,(root/'chatgpt/00_START_HERE.md').read_text())
        self.assertEqual(common.load(root,'evals/result-template.json')['skill_version'],new)
        self.assertEqual(common.load(root,'evals/status.json')['version'],new)

    def test_R08_case_change_reprojects_actual_writer_input(self):
        root=self.fork();cases=common.rows(root,'evals/development-cases.jsonl')
        cases[0]['facts']='FAKE FIXTURE: 결제 완료 확인됨.'
        (root/'evals/development-cases.jsonl').write_bytes(common.jsonl_bytes(cases))
        self.rejected(self.validate(root))
        self.ok(run(root,'build.py'));self.ok(self.validate(root))
        written=common.rows(root,'evals/inputs.jsonl')[0]
        self.assertEqual(written,common.input_projection(cases[0]))
        self.assertEqual(written['input_sha256'],common.rubric_projection(cases[0])['input_sha256'])

    def test_R09_staging_link_rejected(self):
        (self.project/'.chihun-install-staging').symlink_to(self.outside,target_is_directory=True)
        self.rejected(run(ROOT,'install.py','--target','both','--project',self.project,'--apply'))
        self.assertFalse((self.project/'.agents').exists());self.assertEqual(list(self.outside.iterdir()),[])

    def test_R10_backup_link_rejected(self):
        (self.project/'.chihun-skill-backups').symlink_to(self.outside,target_is_directory=True)
        self.rejected(run(ROOT,'install.py','--target','both','--project',self.project,'--apply'))
        self.assertFalse((self.project/'.agents').exists());self.assertEqual(list(self.outside.iterdir()),[])

    def test_R11_dangling_parent_link_rejected(self):
        (self.project/'.agents').symlink_to(self.outside/'missing',target_is_directory=True)
        self.rejected(run(ROOT,'install.py','--target','codex','--project',self.project,'--apply'))
        self.assertFalse((self.outside/'missing').exists())

    def test_R12_second_commit_failure_rolls_back_fresh_install(self):
        original=os.replace
        def fail_second(src,dst):
            if Path(dst)==self.project/'.claude/skills/chihun-ux-writing' and '.chihun-install-staging' in Path(src).parts:
                raise OSError('INJECTED SECOND COMMIT FAILURE')
            return original(src,dst)
        with patch.object(install.os,'replace',side_effect=fail_second):
            with self.assertRaises(install.InstallationError):
                install.install_skill(self.source,self.project,['codex','claude'])
        self.assertEqual(list(self.project.iterdir()),[])

    def test_R13_second_commit_failure_restores_both_existing_installs(self):
        install.install_skill(self.source,self.project,['codex','claude'])
        for host in ('.agents','.claude'):
            (self.project/host/'skills/chihun-ux-writing/USER.txt').write_text(host)
        before={host:install.fingerprint(self.project/host/'skills/chihun-ux-writing') for host in ('.agents','.claude')}
        original=os.replace
        def fail_second(src,dst):
            if Path(dst)==self.project/'.claude/skills/chihun-ux-writing' and '.chihun-install-staging' in Path(src).parts:
                raise OSError('INJECTED SECOND COMMIT FAILURE')
            return original(src,dst)
        with patch.object(install.os,'replace',side_effect=fail_second):
            with self.assertRaises(install.InstallationError):
                install.install_skill(self.source,self.project,['codex','claude'],replace=True)
        for host,digests in before.items():
            self.assertEqual(install.fingerprint(self.project/host/'skills/chihun-ux-writing'),digests)
        self.assertFalse((self.project/'.chihun-install.lock').exists())

    def test_R14_source_root_link_rejected(self):
        root=self.fork();skill=root/'plugin/skills/chihun-ux-writing';saved=root/'real-skill'
        skill.rename(saved);skill.symlink_to(saved,target_is_directory=True)
        self.rejected(run(root,'install.py','--target','both','--project',self.project,'--apply'))
        self.assertEqual(list(self.project.iterdir()),[])

    def test_R15_required_release_file_link_rejected(self):
        root=self.fork();f=root/'NOTICE.md';f.unlink();fake=self.outside/'fake';fake.write_text('FAKE')
        f.symlink_to(fake)
        self.rejected(run(root,'package.py','--output',self.base/'out'))
        self.assertFalse(list(self.base.glob('out/*.zip')))

    def test_R16_archives_deterministic_and_manifests_exact(self):
        root=self.fork()
        for name in ('out1','out2'):self.ok(run(root,'package.py','--output',self.base/name))
        first=sorted((self.base/'out1').glob('*.zip'))
        self.assertEqual(len(first),2)
        for f in first:
            self.assertEqual(f.read_bytes(),(self.base/'out2'/f.name).read_bytes())
            with zipfile.ZipFile(f) as z:
                self.assertIsNone(z.testzip());prefix=z.namelist()[0].split('/')[0]+'/'
                index=json.loads(z.read(prefix+'RELEASE_MANIFEST.json'))['files']
                names={n[len(prefix):] for n in z.namelist()}-{'RELEASE_MANIFEST.json'}
                self.assertEqual(names,set(index))
                for rel,digest in index.items():self.assertEqual(common.sha256(z.read(prefix+rel)),digest)

    def test_R17_direct_generated_input_edit_detected(self):
        root=self.fork();values=common.rows(root,'evals/inputs.jsonl');values[0]['facts']='FAKE_STALE'
        (root/'evals/inputs.jsonl').write_bytes(common.jsonl_bytes(values))
        self.rejected(self.validate(root));self.rejected(run(root,'package.py','--output',self.base/'out'))

    def test_R18_direct_grader_edit_detected(self):
        root=self.fork();values=common.rows(root,'evals/rubrics.jsonl');values[0]['rubric']['must_include']=[]
        (root/'evals/rubrics.jsonl').write_bytes(common.jsonl_bytes(values))
        self.rejected(self.validate(root))

    def test_R19_score_label_mutation_rejected(self):
        root=self.fork();p=root/'core/score.json';obj=json.loads(p.read_text());obj['items'][0]['label']='FAKE_LABEL';writej(p,obj)
        self.rejected(run(root,'build.py'));self.rejected(self.validate(root))

    def test_R20_no_rubric_data_in_runtime(self):
        runtime='\n'.join(p.read_text() for p in common.list_tree(ROOT,self.source))
        self.assertNotRegex(runtime,r'DEV-\d{3}')
        self.assertNotIn('rubric_source',runtime)

    def test_R21_unmanaged_generated_file_preserved_and_build_rejected(self):
        root=self.fork();f=root/'chatgpt/MY_PRIVATE_NOTE.md';f.write_text('FAKE_USER_NOTE')
        self.rejected(run(root,'build.py'));self.assertEqual(f.read_text(),'FAKE_USER_NOTE')

    def test_R22_write_lock_blocks_concurrent_installer(self):
        (self.project/'.chihun-install.lock').write_text('FAKE_ACTIVE_LOCK')
        self.rejected(run(ROOT,'install.py','--target','both','--project',self.project,'--apply'))
        self.assertFalse((self.project/'.agents').exists())
        self.assertEqual((self.project/'.chihun-install.lock').read_text(),'FAKE_ACTIVE_LOCK')

    def test_R23_generated_parent_symlink_blocks_build(self):
        root=self.fork();cg=root/'chatgpt';shutil.rmtree(cg);cg.symlink_to(self.outside,target_is_directory=True)
        self.rejected(run(root,'build.py'));self.assertEqual(list(self.outside.iterdir()),[])

    def test_R24_zip_extract_rebuild_and_validate(self):
        root=self.fork();self.ok(run(root,'package.py','--output',self.base/'out'))
        archive=self.base/'out'/('chihun-ux-writing-os-v'+common.version(root)+'.zip')
        with zipfile.ZipFile(archive) as z:z.extractall(self.base/'unpacked')
        extracted=self.base/'unpacked'/archive.stem
        self.ok(self.validate(extracted));before=(extracted/'build-manifest.json').read_bytes()
        self.ok(run(extracted,'build.py'));self.assertEqual(before,(extracted/'build-manifest.json').read_bytes())


    def test_R25_build_failure_restores_generated_trees(self):
        root=self.fork();before={rel:common.read_bytes(root,rel) for rel in build.render_outputs(root)}
        proposed=build.render_outputs(root)
        original=os.replace
        def fail_chatgpt(src,dst):
            if Path(dst)==root/'chatgpt' and 'new' in Path(src).parts:
                raise OSError('INJECTED BUILD COMMIT FAILURE')
            return original(src,dst)
        with patch.object(build.os,'replace',side_effect=fail_chatgpt):
            with self.assertRaises(OSError):build.commit_outputs(root,proposed)
        for rel,data in before.items():self.assertEqual(common.read_bytes(root,rel),data)
        self.assertFalse((root/'.chihun-build.lock').exists())

    def test_R26_review_workspace_separates_writer_and_grader(self):
        destination=self.base/'review-spaces'
        self.ok(run(ROOT,'prepare_review.py','--output',destination))
        writer='\n'.join(p.read_text() for p in (destination/'writer').rglob('*') if p.is_file())
        self.assertNotIn('must_include',writer);self.assertNotIn('allowed_interventions',writer)
        self.assertTrue((destination/'grader/rubrics.jsonl').is_file())
        self.assertEqual(len(list((destination/'writer/tasks').glob('*.json'))),32)
        status=json.loads((destination/'REVIEW_STATUS.json').read_text())
        self.assertEqual(status['independent_agent_runs'],0)
        self.assertEqual(status['status'],'prepared_not_executed')
        self.rejected(run(ROOT,'prepare_review.py','--output',destination))

    def test_R27_missing_reference_blocks_install(self):
        root=self.fork();(root/'plugin/skills/chihun-ux-writing/references/07_EVALUATOR.md').unlink()
        self.rejected(run(root,'install.py','--target','both','--project',self.project,'--apply'))
        self.assertEqual(list(self.project.iterdir()),[])

    def test_R28_changed_runtime_blocks_install(self):
        root=self.fork();p=root/'plugin/skills/chihun-ux-writing/SKILL.md';p.write_text(p.read_text()+'\nFAKE_UNBUILT_EDIT\n')
        self.rejected(run(root,'install.py','--target','both','--project',self.project,'--apply'))
        self.assertEqual(list(self.project.iterdir()),[])


    def test_R29_build_failed_rollback_retains_recovery_files(self):
        root=self.fork();proposed=build.render_outputs(root);original=os.replace
        old_skill=(root/'plugin/skills/chihun-ux-writing/SKILL.md').read_bytes()
        def fail_forward_and_restore(src,dst):
            if Path(dst)==root/'chatgpt' and 'new' in Path(src).parts:
                raise OSError('INJECTED COMMIT FAILURE')
            if Path(dst)==root/'plugin' and 'old' in Path(src).parts:
                raise OSError('INJECTED ROLLBACK FAILURE')
            return original(src,dst)
        with patch.object(build.os,'replace',side_effect=fail_forward_and_restore):
            with self.assertRaisesRegex(RuntimeError,'Recovery files retained'):
                build.commit_outputs(root,proposed)
        backups=list(root.glob('.chihun-build-*/old/plugin/skills/chihun-ux-writing/SKILL.md'))
        self.assertEqual(len(backups),1);self.assertEqual(backups[0].read_bytes(),old_skill)

    def test_R30_installer_failed_rollback_retains_backup(self):
        install.install_skill(self.source,self.project,['codex','claude'])
        dest=self.project/'.agents/skills/chihun-ux-writing'
        (dest/'USER.txt').write_text('FAKE_USER_EDIT')
        original=os.replace
        def fail_forward_and_restore(src,dst):
            if Path(dst)==self.project/'.claude/skills/chihun-ux-writing' and '.chihun-install-staging' in Path(src).parts:
                raise OSError('INJECTED COMMIT FAILURE')
            if Path(dst)==dest and '.chihun-skill-backups' in Path(src).parts:
                raise OSError('INJECTED ROLLBACK FAILURE')
            return original(src,dst)
        with patch.object(install.os,'replace',side_effect=fail_forward_and_restore):
            with self.assertRaisesRegex(install.InstallationError,'Rollback incomplete'):
                install.install_skill(self.source,self.project,['codex','claude'],replace=True)
        backups=list((self.project/'.chihun-skill-backups/codex').rglob('USER.txt'))
        self.assertEqual(len(backups),1);self.assertEqual(backups[0].read_text(),'FAKE_USER_EDIT')


class RecordingResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.records=[]
    def addSuccess(self,test):
        super().addSuccess(test);self.records.append({'test':test._testMethodName,'result':'pass'})
    def addFailure(self,test,err):
        super().addFailure(test,err);self.records.append({'test':test._testMethodName,'result':'fail','detail':self._exc_info_to_string(err,test)})
    def addError(self,test,err):
        super().addError(test,err);self.records.append({'test':test._testMethodName,'result':'error','detail':self._exc_info_to_string(err,test)})


def main() -> int:
    global SOURCE
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path);ap.add_argument('--report',type=Path)
    a=ap.parse_args();SOURCE=a.source
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(RegressionTests)
    result=unittest.TextTestRunner(verbosity=2,resultclass=RecordingResult).run(suite)
    report={'version':common.version(ROOT),'kind':'offline_engineering_regression',
            'result':'pass' if result.wasSuccessful() else 'fail','tests_total':result.testsRun,
            'tests_passed':sum(x['result']=='pass' for x in result.records),'tests':result.records,
            'environment':sys.platform,'independent_agent_runs':0,'external_model_runs':0,
            'actual_user_installations':0,'limits':['Not a hostile concurrent-filesystem sandbox','Power-loss/process-kill atomicity not tested','macOS/Windows not executed','No semantic model quality score']}
    if a.report:a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(common.json_text(report),encoding='utf-8')
    print(common.json_text(report));return 0 if result.wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())
