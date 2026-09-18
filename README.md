# CHIHUN UX Writing OS

**버전 0.1.3 · 기술 결함 수정본 / 실제 호스트·라이팅 품질 검증 전**

하나의 판단 기준을 두 환경에 배포하는 패키지예요. 하나는 Codex·Claude Code용 로컬 스킬이고, 다른 하나는 ChatGPT 프로젝트 설정과 플러그인용 패키지예요. 모델 재학습이 아니라 지침·원칙·선호 데이터·검수 절차를 제공해요.

## 먼저 선택해요

| 사용 목적 | 시작 파일 |
|---|---|
| ChatGPT에서 문구 워싱·피드백 | `chatgpt/00_START_HERE.md` |
| Codex·Claude Code에 설치 | `docs/03_INSTALL_AGENTS.md` |
| 구조와 현재 진행 상태 확인 | `docs/00_DELIVERY_REPORT.md` |
| 원문이 어디로 연결됐는지 확인 | `docs/01_SOURCE_MAP.md` |
| 새 기준 추가·수정 | 아래 ‘관리 방법’ |

## 이 저장소에서 바로 쓰기

`.claude/skills/ben-ux-writing/`에 스킬이 프로젝트 범위로 함께 커밋되어 있어요. 이 저장소를 clone하거나 열고 Claude Code 세션을 시작하면 별도 설치 없이 `/ben-ux-writing`으로 호출할 수 있어요. 이 폴더는 `plugin/skills/ben-ux-writing/`의 복사본이므로 기준을 바꿨다면 빌드한 뒤 아래 명령으로 다시 맞춰요.

```sh
python3 scripts/install.py --target claude --scope project --project "$PWD" --replace-with-backup --apply
```

## 기본 사용

워싱은 필요한 부분만 수정하고 적절한 문구는 유지해요. 피드백은 문구 문제와 UI/상태 문제를 구분해요. 새 작성은 확인된 제품 사실을 바탕으로 만들어요. 결과는 요소별 WRITE / KEEP / DELETE / REDESIGN으로 판단해요.

첫 범위는 **주어진 인증/KYC 조건의 안내, 결제·구독 상태/중요 정보, 챌린지 현재 상태/진행**이에요. 모든 도메인의 완전 지원이나 성능 보장을 뜻하지 않아요.

## 구성

```text
core/              관리 원본: 규칙·스펙·선호·평가 기준
sources/           원문 해시와 130개 절의 출처 지도
plugin/            생성된 portable 플러그인과 설치 가능한 스킬
chatgpt/           생성된 프로젝트 지침·지식 파일·단일 대화 시작 자료
templates/         공통 실행 지침과 작업·제품 사실·피드백 양식
scripts/           빌드·검사·로컬 설치 스크립트
evals/             개발용 문제와 분리된 채점 기준 (미실행)
docs/              보고·설계 쟁점·설치·근거·검사 기록
.agents/plugins/   로컬 플러그인 마켓플레이스 예시
```

## 관리 방법

현재 버전은 `VERSION` 한 곳에서 관리해요. 규칙은 `core/rules.json`, 사례는 `core/*corpus.jsonl` 등 관리 원본에서 수정해요. `plugin/`과 `chatgpt/`, `evals/inputs.jsonl`, `evals/rubrics.jsonl`, 생성된 시작 안내는 직접 수정하지 않아요. 빌드하면 생성 폴더가 다시 만들어져요.

```sh
python3 scripts/build.py
python3 scripts/validate.py
python3 scripts/test_package.py
python3 scripts/test_regressions.py --report verification/regressions.json
```

스크립트는 Python 3.10+ 표준 라이브러리를 사용해요. 모델 호출, API 키, 네트워크, Git push가 필요하지 않아요. 설치는 기본 dry-run이며 `--apply`가 있어야 복사해요. 운영체제와 실제 호스트별 동작은 별도 검증 대상이에요.

원문을 가지고 있다면 `private/master-v1.0.md`에 보관한 뒤 검사할 수 있어요. 원문은 이 배포본에 포함하지 않았어요.

```sh
python3 scripts/validate.py --source private/master-v1.0.md
```

원문에 GOLD로 명시된 12개를 추출하고, 다른 GOLD 표시 8개와 원문 Synthetic 32개는 별도로 구분했어요. 이를 독립적인 실제 피드백 40건이라고 계산하지 않아요. 사용자가 말한 이유와 모델의 해석도 구분해요.

## 검증 상태

파일 구조·출처·원문 보존·참조 연결 검사와 임시 프로젝트 폴더에서의 설치 스크립트 검사는 수행했어요. 실제 Codex·Claude Code·ChatGPT에서 스킬 호출·문구 품질을 시험한 것은 아니에요. 32개 개발용 문제에는 아직 실행 결과가 없어요.

GitHub 공개/비공개 저장소 생성, push, ChatGPT 계정 설정, 플러그인 공개 등록·설치를 수행하지 않았어요. `NOTICE.md`를 확인한 뒤 배포 범위를 결정해요. 원문 전체가 빠져 있어도 추출된 규칙·사례에는 소유자의 기준이 담겨 있어요.

## 수정본 확인

`docs/06_FIX_REPORT.md`에 수정 항목·검사·남은 한계를 정리했어요. `verification/`의 통과 기록은 Linux 로컬 기술 검사예요. `review/README.md`는 별도 에이전트 검토 준비 방법이며 실제 실행 결과가 아니에요.

업데이트할 때는 VERSION을 변경한 뒤 빌드·검사하고 배포해요. `release-files.json`의 허용 파일 목록은 명시적으로 검토해 수정해요. 임시 파일·원문·고객 자료는 배포 목록에 자동으로 들어가지 않아요. 원문 고정 평가표 변경은 빌드에서 거부되며, 변경이 필요하다면 승인된 새 기준의 설계가 별도로 필요해요.
