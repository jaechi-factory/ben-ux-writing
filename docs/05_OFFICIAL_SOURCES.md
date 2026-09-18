# 환경별 패키징 근거

확인일: 2026-09-18. 아래는 설치·배포 형식의 근거예요. CHIHUN의 라이팅 원칙을 이 문서들로 교체하지 않아요. 인터페이스·경로·권한은 변경될 수 있고 실제 사용 환경에서 재확인이 필요해요.

## D1 · OpenAI — Build skills

`https://learn.chatgpt.com/docs/build-skills`

기존 `https://developers.openai.com/codex/skills/`에서 이동했어요. `SKILL.md`와 name/description, references, Codex의 `.agents/skills`, 사용자 범위 `~/.agents/skills`, 명시 호출, 플러그인 배포 경로를 확인했어요.

## D2 · Anthropic — Extend Claude with skills

`https://code.claude.com/docs/en/skills`

프로젝트 `.claude/skills/<name>/SKILL.md`, 사용자 `~/.claude/skills/<name>/SKILL.md`, 참조 파일과 `/name` 호출 구조를 확인했어요. 로컬 설치와 계정/클라우드 동기화는 동일하지 않아요.

## D3 · OpenAI — Projects in ChatGPT

`https://help.openai.com/en/articles/10169521-using-projects-in-chatgpt`

프로젝트 내 파일·지침 사용과 설정 경로를 확인했어요. 계정에서 실제 프로젝트를 만들거나 파일을 업로드한 것은 아니에요.

## D4 · OpenAI — Package your plugin

`https://developers.openai.com/plugins/build/plugins`

root `plugin.json`, 공식 portable schema URL, `skills/` 구조, 선택적인 MCP/확장, 저장소 로컬 마켓플레이스 예시와 로컬 등록 절차를 확인했어요. 공개 디렉터리 게시와 로컬 테스트는 별개예요. 패키지의 JSON 검사는 로컬 필수 필드 검사이며 공식 등록 심사 통과를 뜻하지 않아요.

라이팅 원문의 출처는 `sources/source-manifest.json` 및 각 규칙·사례의 MASTER_V1 절/줄 번호예요. 대화에서 제안한 설계 변경은 `docs/02_DECISIONS_AND_BOUNDARIES.md`에 구분해요.
