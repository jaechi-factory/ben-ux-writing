# 원문과 출처

원문: `붙여넣은 마크다운(1)(1).md`, CHIHUN UX WRITING OS Master v1.0.
`source-manifest.json`에 원본 SHA-256, 4,304줄, #0~129의 130개 절을 기록했어요. 130개 절을 130개 독립 규칙이라고 주장하지 않아요.

원문 전체는 이 저장소에 포함하지 않아요. 사용자가 가진 원문을 `private/master-v1.0.md`에 복사한 뒤 다음 검사를 실행할 수 있어요.

```sh
python3 scripts/validate.py --source private/master-v1.0.md
```

원문 줄 번호는 업로드한 Markdown의 실제 줄 번호예요. 본문을 편집하거나 줄바꿈을 바꾸면 번호와 해시가 달라질 수 있어요. ChatGPT 대화의 filecite 식별자는 다른 환경에서 작동하지 않으므로, 배포본에서는 source ID·절·줄 번호로 참조해요.

`section-map.jsonl`: 전체 절의 목적지 지도예요. `compiled_rule_draft`는 해당 절이 규칙 초안에 연결되었다는 뜻이지 그 절의 모든 내용이 완전히 이식·검증되었다는 뜻이 아니에요.

`core/preference-corpus.jsonl`: 원문 #98 GOLD-001~012를 그대로 보존해요.
`core/additional-source-pairs.jsonl`: 원문 #17의 KYC 6개와 #33의 GOLD 표시 문서 2개를 별도로 보존해요. 독립적인 GOLD 피드백 수로 합산하지 않아요.
`core/source-synthetic.jsonl`: 원문 #99의 20개를 보존해요. 원문이 부모 GOLD ID를 명시하지 않았으므로 임의 연결하지 않아요.
