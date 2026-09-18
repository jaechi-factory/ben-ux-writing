# Codex·Claude Code 설치

버전 {{VERSION}} · 설치 방식은 2026-09-18 공식 문서 확인 기준이에요. [D1], [D2]는 `docs/05_OFFICIAL_SOURCES.md`에 있어요.

이 압축 파일은 GitHub에 아직 올라가 있지 않아요. 압축을 푼 저장소 루트에서 실행해요. 설치 스크립트에는 Python 3.10 이상이 필요해요. macOS/Linux 예시는 `python3`, 환경에 따라 `python`을 사용해요. Windows/macOS와 실제 에이전트 앱은 여기서 실행 검증하지 않았어요.

## 1. 복사 계획 확인

Codex와 Claude Code 모두 사용자 범위에 설치할 계획을 확인해요. 이 명령만으로 파일을 바꾸지는 않아요.

```sh
python3 scripts/install.py --target both --scope user
```

하나만 사용할 때는 `both`를 `codex` 또는 `claude`로 바꿔요.

## 2. 실제 파일 복사

```sh
python3 scripts/install.py --target both --scope user --apply
```

공식 로컬 스킬 경로 [D1, D2]:

```text
Codex:      ~/.agents/skills/ben.lee-ux-writing/
Claude Code: ~/.claude/skills/ben.lee-ux-writing/
```

프로젝트 한 곳에만 설치하려면 다음 명령을 사용해요. 경로는 실제 존재하는 작업 폴더로 바꿔요.

```sh
python3 scripts/install.py --target both --scope project --project "/absolute/path/to/project"
python3 scripts/install.py --target both --scope project --project "/absolute/path/to/project" --apply
```

프로젝트 경로는 각각 `.agents/skills/`와 `.claude/skills/`예요. 원본 스킬 전체를 복사하므로 참조 파일을 별도로 연결할 필요는 없어요. 스크립트는 모델을 실행하거나 계정 권한·Git 상태를 변경하지 않아요.

## 3. 발견·호출 확인

새 세션에서 목록에 나타나는지 확인해요. 반영되지 않으면 앱/CLI를 재시작해요. 공식 명시 호출 방법 [D1, D2]:

```text
Codex:
$ben.lee-ux-writing 아래 문구를 워싱해 주세요. 적절한 문구는 유지하고 중요한 이유만 알려주세요.

Claude Code:
/ben.lee-ux-writing 아래 문구를 워싱해 주세요. 적절한 문구는 유지하고 중요한 이유만 알려주세요.
```

명시 호출과 자동 선택은 달라요. 설치 파일이 존재하더라도 자동 선택·참조 파일 읽기·문구 품질은 별도 확인해야 해요. 이 패키지는 사용자 머신에 이미 설치된 것이 아니에요.

## 업데이트

`core/` 또는 `templates/`의 관리 원본을 수정한 뒤 생성본을 빌드하고 검사해요.

```sh
python3 scripts/build.py
python3 scripts/validate.py
python3 scripts/install.py --target both --scope user --replace-with-backup
python3 scripts/install.py --target both --scope user --replace-with-backup --apply
```

기존 설치가 있으면 기본 동작은 거절이에요. 업데이트 옵션을 주면 기존 폴더를 `~/.chihun-skill-backups/`로 옮겨 보존한 뒤 새 생성본을 복사해요. 프로젝트 설치의 백업은 해당 프로젝트의 `.chihun-skill-backups/`에 있어요. 설치본을 직접 편집했다면 백업과 차이를 검토해야 해요.

## 수동 설치

Python 설치를 사용하지 않는 경우, `plugin/skills/ben.lee-ux-writing/` 폴더 전체를 위의 대상 경로로 복사해요. `SKILL.md` 한 파일만 복사하면 참조 파일을 읽지 못해요. 기존 폴더를 덮어쓰기 전에 따로 백업해요.

## GitHub 배포

새 저장소에 올릴 수 있는 구조예요. 공개 여부와 라이선스를 결정하기 전에는 비공개 저장소에서 검토해요. 원문 전체는 포함하지 않았지만 추출된 규칙·사례는 포함돼요. `NOTICE.md`를 확인해요. 이 문서는 게시 방법을 설명할 뿐 실제 저장소 생성·push를 수행한 기록이 아니에요.

## 설치 보호 범위

선택한 루트 아래의 링크·junction·중간 폴더 오류를 거부해요. 양쪽 대상은 쓰기 전에 모두 검사하고 모두 임시 복사한 뒤 반영해요. 처리 가능한 복사·이름 변경 오류가 생기면 이미 변경한 대상도 복원해요. 원본 스킬 파일 목록과 해시가 빌드 기록에 맞지 않으면 설치하지 않아요.

동일 폴더를 악의적으로 동시에 바꾸는 다른 프로세스, 강제 종료·전원 손실, 다른 파일시스템 마운트 환경까지 원자성을 보장하는 보안 샌드박스는 아니에요. 설치 중 다른 프로세스로 같은 경로를 바꾸지 마세요. 강제 종료 후 잠금 파일이나 백업이 남으면 진행 중인 작업이 없는지 확인하고 보존된 백업부터 검토해요. 현재 자동 검사는 Linux의 임시 폴더에서 수행했고 macOS/Windows는 미실행이에요.
