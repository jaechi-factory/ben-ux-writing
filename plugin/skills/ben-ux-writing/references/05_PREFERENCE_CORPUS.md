# 05 · PREFERENCE CORPUS

원문 #98의 GOLD-001~012를 원문 그대로 보존해요. 원문이 GOLD라고 명시했다는 사실을 보존하며, 원래 피드백 대화를 따로 검증한 것은 아니에요. user_reason과 독립 피드백 수는 제공되지 않아 null이에요. 아래 예시의 숫자·날짜·기관·조건은 현재 제품 사실이 아니에요.

원문 #109~111 출처 가중치와 승격 기준:

# 109. SOURCE WEIGHT

학습 우선순위:

```text
사용자가 직접 수정한 문장
        ↓
사용자가 명시적으로 채택한 문장
        ↓
사용자가 강하게 거절한 문장
        ↓
반복적으로 나타난 선호
        ↓
현재 데이터에서 직접 확장한 Synthetic Pair
        ↓
일반 UX Writing Best Practice

```

---


# 110. GOLD / SYNTHETIC 분리

### GOLD

실제 대화에서 명시적 선호 또는 거절이 확인됨.

Weight: 5

### STRONG\_SYNTHETIC

GOLD 규칙을 거의 동일한 UX 상황으로 확장.

Weight: 3

### SYNTHETIC

일반적인 제품 상황에 확장.

Weight: 1\~2

모델은 GOLD와 충돌하는 일반론을 사용하지 않는다.

---


# 111. RULE PROMOTION

한 번 나온 피드백은 UX 전역 규칙으로 바로 승격하지 않는다.

### Example

한 번:

> “진행”이라는 표현이 어색함.

Local preference.

반복:

> 진행 / 처리 / 수행 같은 명사형 표현을 여러 화면에서 반복 거절.

UX Global Rule:

> 행동을 구체적인 동사로 표현한다.

---


출처: MASTER_V1 §98 L2960–L2982 · 도메인: authentication · 묶음: AUTH_LOCK

### GOLD-001

**CONTEXT**

주민등록증 인증 실패

**REJECTED**

인증 시도 횟수를 초과했습니다.

**PREFERRED**

입력한 정보가 여러 번 맞지 않아 더 이상 인증할 수 없어요.

**RULE**

시스템 제한값보다 사용자 상태를 말한다.

**WEIGHT**

5

---

출처: MASTER_V1 §98 L2984–L3006 · 도메인: authentication · 묶음: AUTH_LOCK

### GOLD-002

**CONTEXT**

정부24 잠금 해제

**REJECTED**

정부24에서 잠김 해제를 진행해 주세요.

**PREFERRED**

정부24에서 주민등록증 잠금을 풀면 다시 인증할 수 있어요.

**RULE**

행정어를 행동어로 바꾸고 행동 이후 결과까지 설명한다.

**WEIGHT**

5

---

출처: MASTER_V1 §98 L3008–L3034 · 도메인: kyc · 묶음: KYC_REASON

### GOLD-003

**CONTEXT**

KYC

**REJECTED**

안전한 금융거래를 위해 고객님의 신원, 거래 목적 및 자금 출처를 확인합니다.

**PREFERRED**

안전한 금융거래를 위해 고객님이 어떤 분인지, 거래와 돈에 대한 정보를 확인해요.

또는 더 구체적으로:

안전한 금융거래를 위해 고객님이 어떤 분인지, 돈을 어디에 쓰고 어떻게 마련했는지 확인해요.

**RULE**

법적 용어를 사용자가 실제 답하게 될 질문으로 번역한다.

**WEIGHT**

5

---

출처: MASTER_V1 §98 L3036–L3062 · 도메인: kyc · 묶음: KYC_REASON

### GOLD-004

**CONTEXT**

법적 필수 절차

**REJECTED**

특정금융정보법에 따른 필수 절차예요.

**PREFERRED**

안전한 금융거래를 위해 꼭 확인해야 하는 정보예요.

보조:

특정금융정보법에 따라 필요한 절차예요.

**RULE**

사용자 이유가 법적 근거보다 위에 온다.

**WEIGHT**

5

---

출처: MASTER_V1 §98 L3064–L3086 · 도메인: document_upload · 묶음: DOC_DUPLICATE

### GOLD-005

**CONTEXT**

파일 중복 제출

**REJECTED**

{파일명} 파일은 중복 제출되었습니다.

**PREFERRED**

{파일명} 파일은 이미 제출했어요.

**RULE**

시스템 판정 대신 이미 일어난 사실을 자연스럽게 표현한다.

**WEIGHT**

5

---

출처: MASTER_V1 §98 L3088–L3110 · 도메인: document_upload · 묶음: DOC_ADDITIONAL

### GOLD-006

**CONTEXT**

추가 서류

**REJECTED**

다른 파일을 제출해 주세요.

**PREFERRED**

추가로 필요한 서류를 제출해 주세요.

**RULE**

‘다른’이라는 상대적 표현보다 실제 목적을 설명한다.

**WEIGHT**

5

---

출처: MASTER_V1 §98 L3112–L3136 · 도메인: reservation · 묶음: DRIVER_CONDITION

### GOLD-007

**CONTEXT**

차량 예약 조건

**REJECTED**

운전면허 취득 1년 이상, 예약가능
해당 조건이 아닐 경우 이용 제한이 있습니다.

**PREFERRED**

운전면허를 취득한 지 1년 이상이면 예약할 수 있어요.
1년 미만이면 차량 예약이 제한돼요.

**RULE**

가능 조건부터 설명하고 행정체를 제거한다.

**WEIGHT**

5

---

출처: MASTER_V1 §98 L3138–L3156 · 도메인: authentication · 묶음: JIT_AUTH

### GOLD-008

**CONTEXT**

예약코드 등록 후 인증

**PREFERRED**

운행을 시작하려면 인증이 필요해요. 지금 등록할까요?

**RULE**

실제로 인증이 필요한 시점에 요구하고 이유를 행동과 연결한다.

**WEIGHT**

5

---

출처: MASTER_V1 §98 L3158–L3177 · 도메인: location · 묶음: MAP_RANGE

### GOLD-009

**CONTEXT**

지도 범위 선택

**PREFERRED**

장소를 바꾸려면 지도에서 직접 선택해 주세요.
현재 위치에서 1km 안에서 선택할 수 있어요.

**RULE**

행동 방법과 제약 범위를 함께 알려준다.

**WEIGHT**

5

---

출처: MASTER_V1 §98 L3179–L3201 · 도메인: challenge · 묶음: CHALLENGE_PROGRESS

### GOLD-010

**CONTEXT**

Challenge progress

**REJECTED**

4 / 6

**PREFERRED**

4번 성공 · 2번 남았어요.

**RULE**

숫자를 진행 의미로 번역한다.

**WEIGHT**

5

---

출처: MASTER_V1 §98 L3203–L3225 · 도메인: challenge · 묶음: CHALLENGE_TODAY

### GOLD-011

**CONTEXT**

Challenge today state

**REJECTED**

9월 18일 참여 완료

**PREFERRED**

오늘 성공했어요.

**RULE**

현재 사용자가 궁금한 상태를 날짜 기록보다 위에 둔다.

**WEIGHT**

5

---

출처: MASTER_V1 §98 L3227–L3250 · 도메인: challenge · 묶음: WORKOUT_TIME

### GOLD-012

**CONTEXT**

운동 시간 진입 장벽

**REJECTED**

8세트 · 총 23분

**PREFERRED**

8세트 약 23분
설명까지 포함해도 30분 안에 끝나요.

**RULE**

숫자를 사용자의 실제 판단 기준으로 번역한다.

**WEIGHT**

5

---

다른 GOLD 표시 8개는 05_ADDITIONAL_SOURCE_PAIRS.jsonl, 원문 Synthetic 20개는 05_SOURCE_SYNTHETIC.jsonl에 별도 보존해요. 독립적인 선호 건수로 합산하지 않고, 필요한 맥락에서만 읽어요. 새 개발용 시험은 여기 포함하지 않아요.
