# Market AI 프로젝트 인수인계

> 기준 시점: 2026-08-22 01:53 KST  
> 기준본: 이 문서와 함께 첨부되는 **최신 `market-ai` ZIP**  
> 현재 다음 작업: **KIS eFriend Expert 주간 `FC_R` 실제 실시간 수신 1회 확인**

---

## 0. 새 채팅 시작 규칙 — 가장 중요

새 채팅에서 사용자가 최신 `market-ai` ZIP을 첨부한 뒤 **`인수인계`**라고만 입력하면 다음 순서로 처리한다.

1. 첨부된 최신 ZIP 내부의 이 문서(`market_ai_project_handover.md`)와 `README.md`를 먼저 읽는다.
2. 과거 작업을 다시 설명해 달라고 사용자에게 요구하지 않는다.
3. **QA를 자동으로 시작하지 않는다.**
4. 현재 다음 작업이 아래임을 짧게 알려준다.

```text
KIS eFriend Expert 주간 FC_R 실제 실시간 수신 1회 확인
```

5. 답변 마지막에 반드시 아래처럼 안내하고 사용자 입력을 기다린다.

```text
다음 요청: 주간 FC_R 확인
```

권장 응답 예:

```text
인수인계 확인 완료.
현재 다음 작업은 KIS eFriend Expert 주간 FC_R 실제 실시간 수신 1회 확인입니다.

다음 요청: 주간 FC_R 확인
```

사용자가 이후 **`주간 FC_R 확인`**이라고 입력하면 주간장 실통신 확인을 진행한다.

---

# 1. 작업 운영 원칙

- 차수 작업과 QA를 분리한다.
  - `1차`, `2차`, `3차` ... = 해당 차수 구현/수정만 수행
  - `QA` = 현재 수정본 검증 수행
  - `수정` = QA에서 확인된 문제만 수정하고 다시 QA 대기
- 사용자가 명시하지 않으면 차수 구현 직후 전체 QA까지 자동 수행하지 않는다.
- 항상 **현재 채팅에 첨부된 최신 ZIP**을 코드 기준본으로 사용한다.
- 최소 변경 원칙을 유지한다.
- 실제 선물 데이터와 proxy를 절대 혼동하지 않는다.
- 데이터가 없으면 결측으로 두는 것이 잘못된 대체 데이터를 실제값처럼 저장하는 것보다 낫다.
- 이유: 저장된 시장 데이터가 이후 Signal / Backtest / Calibration의 기준이 되기 때문이다.
- GitHub는 현재 운영 필수 구성요소가 아니다. 현재 기준 ZIP에는 `.git/`이 없으며, 필요할 때 나중에 다시 연동한다.
- `main_dashboard_maintenance_handover.md`는 아직 수정하지 않는다. 투자 대시보드 쪽에서 나중에 일괄 반영한다.
- GitHub 커밋 문구가 필요한 경우:
  - `Summary`: 매우 짧게
  - `Description`: 한 줄 설명

---

# 2. 프로젝트 목표

로컬 PC에서 동작하는 **AI Market Signal** 시스템을 구축한다.

주요 구성:

- 국내/미국 시장 데이터
- 실제 KOSPI200 선물
- 반도체 관련 지표
- 환율 / 유가 / 미국채 금리
- 뉴스 수집
- OpenAI 뉴스 구조화 분석
- Rule-based Signal Engine
- 예측 이력 / 실제 결과 / Backtest
- 확률 Calibration
- 기존 투자 대시보드의 AI Market Signal 표시

자동 주문 시스템이 아니다.

**주문 API, 계좌번호, 계좌 비밀번호를 사용하지 않는다.**

---

# 3. 현재 프로젝트 구조

현재 최신 ZIP 기준 핵심 구조:

```text
market-ai/
├─ app.py
├─ config.py
├─ requirements.txt
├─ start-market-ai.bat
├─ .env.example
├─ README.md
├─ market_ai_project_handover.md
│
├─ ai/
│  ├─ openai_analyzer.py
│  ├─ pricing.py
│  ├─ schemas.py
│  └─ service.py
│
├─ backtest/
├─ bridges/
│  └─ kis_efriend.py
├─ calibration/
├─ collectors/
├─ db/
│  └─ market_signal.db
├─ market/
├─ news/
├─ signals/
│
├─ KisKospi200Bridge/
├─ KisKospi200Bridge.sln
│
└─ eFriendQA/
   ├─ expert_manual.pdf
   └─ expert_CS_Sample.zip
```

`eFriendQA/`는 **eFriend API 참고/QA 자료 보관 폴더**다.

- `expert_manual.pdf`
- `expert_CS_Sample.zip`

은 실행 필수 파일이 아니며, eFriend 관련 추가 검증이 필요할 때 참고한다.

현재 기준 ZIP에는 `.env`가 포함되지 않는다. 실제 API Key 등 비밀값은 로컬 `.env`에만 둔다.

`db/market_signal.db`는 누적 운영 데이터가 들어 있는 DB이므로 패치/병합 시 임의로 덮어쓰거나 삭제하지 않는다.

---

# 4. 전체 아키텍처

```text
투자 대시보드 (localhost:8000)
        │
        │ 최신 Signal 조회
        ▼
Market AI FastAPI (localhost:8001)
        │
        ├─ SQLite / SQLAlchemy
        ├─ 시장 데이터 수집
        ├─ 뉴스 수집
        ├─ OpenAI 뉴스 분석
        ├─ Signal Engine
        ├─ Backtest
        └─ Calibration

KIS eFriend Expert
        │
        ▼
C# KOSPI200 Futures Bridge
        │ HTTP POST
        ▼
Market AI :8001
        │
        ▼
FUTURES:KOSPI200
        │
        ▼
Signal Engine
```

---

# 5. Market AI 1~9차 완료 상태

## 1차 — FastAPI + SQLite ✅

- FastAPI
- SQLite / SQLAlchemy
- 기본 포트 `8001`
- Swagger `/docs`
- UTC timestamp `Z` 반환

## 2차 — 시장 데이터 DB ✅

핵심 테이블:

- `market_prices`
- `market_snapshot`

동작:

- 이력과 최신 snapshot 분리
- 오래된 관측값이 더 최신 snapshot을 덮지 않도록 보호

## 3차 — 실제 시장 데이터 수집 ✅

개발용 provider:

```text
yfinance
```

주요 symbol:

```text
KRX:005930
KRX:000660
KRX:009150
NASDAQ:SKHY
NASDAQ:NVDA
NASDAQ:MU
FUTURES:NQ
FX:USDKRW
COMMODITY:WTI
COMMODITY:BRENT
RATE:US10Y
RATE:US30Y
```

KOSPI200은 중요 무결성 규칙이 있다.

```text
FUTURES:KOSPI200
```

에 Yahoo `^KS200` 현물지수를 실제 선물처럼 넣지 않는다.

개발용 proxy를 허용하더라도:

```text
^KS200 = spot proxy
```

로 명확히 구분하며 실제 선물로 승격하지 않는다.

기본값:

```text
MARKET_AI_ALLOW_KOSPI200_INDEX_PROXY=false
```

## 4차 — 뉴스 수집 ✅

개발용 뉴스 소스:

```text
GDELT DOC 2.0
```

주요 Topic:

```text
geopolitics
us_policy
fed_rates
semiconductors
energy
korea_market
```

테이블:

- `news_articles`
- `news_article_topics`

## 5차 — OpenAI 뉴스 구조화 분석 + 비용 추적 ✅

AI 입력은 현재 기사 전체 본문이 아니라 **headline + metadata + topic 정보**다.

구조화 항목:

- category
- event_type
- market_relevance
- sentiment
- severity
- confidence
- novelty
- time_horizon
- affected_assets
- KOSPI / 반도체 / NASDAQ100 / 유가 / 금리 / USDKRW 영향
- 한국어 rationale

자동 AI 분석 기본값:

```text
MARKET_AI_AI_ENABLED=false
```

실제 OpenAI API Key를 이용한 live QA는 아직 남아 있다.

## 6차 — Signal Engine ✅

엔진 버전:

```text
stage6_rule_v2
```

주요 출력:

- `kospi_score`
- `semiconductor_score`
- `gap_up_probability`
- `up_close_probability`
- `confidence`
- `data_completeness`
- `calibrated`

`calibrated=false`일 때 `gap_up_probability`, `up_close_probability`는 실제 통계확률이 아니라 기존 이름을 유지한 0~100 heuristic score다.

KOSPI 구성에서 KOSPI200 선물 기본 가중치:

```text
kospi200_futures = 0.20
```

freshness와 quality가 실제 effective weight에 반영된다.

## 7차 — 투자 대시보드 연동 ✅

Market AI는 기존 투자 대시보드에서 독립 모듈 방식으로 연동했다.

핵심 파일:

```text
js/dashboard-market-ai.js
```

대시보드 연동 원칙:

- 가능하면 `dashboard-app.js`, `dashboard-ui.js`를 건드리지 않는다.
- AI Market Signal은 웹/태블릿/모바일 모두 compact 한 줄 구조.
- GitHub Pages 등 비로컬 환경에서는 Market AI 영역을 완전히 숨기고 localhost 요청도 보내지 않는다.
- 로컬 서버 오류 시 간단히 `서버 연결 안 됨`
- 오래된 Signal은 `신호 지연`
- stale 기준: 5분

현재 Market AI Bridge 2차 QA에서는 투자 대시보드 수정이 필요하지 않다.

## 8차 — Prediction Outcome / Backtest ✅

기존 `signal_runs`를 prediction ledger로 사용.

테이블:

- `market_outcomes`
- `signal_evaluations`

평가용 공식 forecast 선택:

```text
09:00 KST 직전 가장 최근 Signal
```

기본 최대 forecast age:

```text
12시간
```

## 9차 — Probability Calibration ✅

방식:

```text
quantile_beta_pava_v1
```

기본 학습 조건:

- 평가 완료 거래일 30개 이상
- positive 5개 이상
- negative 5개 이상
- 서로 다른 raw score 3개 이상

독립 target:

- KOSPI 상승
- 반도체 상승
- 갭상
- 상승마감

테이블:

- `calibration_models`
- `signal_calibrations`

No-lookahead 원칙 유지.

수정 완료된 중요 사항:

- 동일 raw score는 같은 그룹 유지
- 같은 raw score는 같은 calibrated probability
- 단순 날짜 순서 변경으로 mapping이 달라지지 않음

---

# 6. 현재 API 범위

현재 `app.py` 기준 주요 API:

## 기본 / 시장

```text
GET  /api/health
GET  /api/market-signal
GET  /api/market-data/catalog
GET  /api/market-data/snapshot
GET  /api/market-data/history/{symbol}
```

## KIS eFriend Bridge

```text
GET  /api/bridge/kis-efriend/status
POST /api/bridge/kis-efriend/tick
POST /api/bridge/kis-efriend/heartbeat
```

## 일반 시장 collector

```text
GET  /api/collector/status
GET  /api/collector/mappings
POST /api/collector/run-once
```

## 뉴스

```text
GET  /api/news/status
GET  /api/news/topics
GET  /api/news/latest
POST /api/news/run-once
```

## AI 뉴스

```text
GET  /api/ai-news/status
GET  /api/ai-news/categories
GET  /api/ai-news/latest
POST /api/ai-news/run-once
```

## Signal

```text
GET  /api/signal/status
GET  /api/signal/weights
GET  /api/signal/latest
GET  /api/signal/history
POST /api/signal/run-once
```

## Backtest

```text
GET  /api/backtest/status
GET  /api/backtest/forecasts
GET  /api/backtest/outcomes
POST /api/backtest/outcomes
POST /api/backtest/evaluate
GET  /api/backtest/evaluations
GET  /api/backtest/summary
GET  /api/backtest/dataset
```

## Calibration

```text
GET  /api/calibration/status
POST /api/calibration/train
GET  /api/calibration/models
GET  /api/calibration/performance
```

---

# 7. KIS eFriend Expert 연동 — 확인된 사실

## 7.1 eFriend 환경

완료:

- eFriend Expert Open API 신청
- eFriend Expert API 모듈 설치
- 인증서/로그인 설정
- eFriend Expert 로그인
- Visual Studio Community 2022
- `.NET 데스크톱 개발`
- C# Bridge 빌드

Bridge 프로젝트 설정:

```text
.NET Framework 4.8
x86
```

eFriend Expert와 Bridge는 관리자 권한 실행 기준으로 사용한다.

## 7.2 현재 KOSPI200 근월물

FML Viewer 실제 조회를 통해 현재 근월물 월 확인:

```text
609 → 202609
```

FOPH 실제 조회를 통해 확인한 종목코드:

```text
A01609
```

따라서 현재 기준 실제 사용 종목:

```text
2026-09 KOSPI200 선물
A01609
```

근월물 rollover는 아직 자동화하지 않았다.
실제 eFriend 규칙을 추가 검증하기 전에는 종목코드를 추측해서 자동 생성하지 않는다.

## 7.3 실시간 서비스

주간 체결:

```text
FC_R
```

야간 체결:

```text
CMEC_R
```

주요 공통 field index:

```text
0   종목코드
1   영업시간
4   전일대비율
5   현재가
10  누적거래량
34  매도1
35  매수1
```

야간 호가 참고 서비스:

```text
CMEH_R
```

---

# 8. KIS Bridge 1차 ✅

C# WinForms로 eFriend real-time subscription을 실제 수신하는 단계.

실제 야간 검증 완료:

```text
A01609
CMEC_R
```

Bridge 화면에서:

- 현재가 갱신
- 전일대비율 갱신
- 거래량 갱신
- 매도1 / 매수1 갱신
- Tick count 계속 증가

사용자가 보는 증권앱의 야간 KOSPI200 선물 가격과 동일하다고 직접 확인했다.

따라서 아래 구간은 실증 완료:

```text
eFriend Expert
→ ActiveX/COM
→ C# ReceiveRealData
```

---

# 9. KIS Bridge 2차 — 실통신 확인 / QA 수정 반영

현재 ZIP에는 2차 코드가 이미 병합되어 있다.
예전 패치 ZIP을 다시 덮어쓸 필요가 없다.

## 9.1 C# Bridge 동작

- eFriend raw tick은 UI에서 모두 수신
- Market AI 전송: 최대 **5초에 1회**
- heartbeat: **10초 간격**
- AUTO session check: **5초 간격**

AUTO 기준:

```text
08:45~15:45 → FC_R
15:45~18:00 → 장외 / 구독 해제
18:00~06:00 → CMEC_R
06:00~08:45 → 장외 / 구독 해제
```

## 9.2 Market AI 저장

canonical symbol:

```text
FUTURES:KOSPI200
```

source 형식:

야간:

```text
kis-efriend:night:CMEC_R:A01609
```

주간:

```text
kis-efriend:day:FC_R:A01609
```

snapshot은 전달된 실제 선물 tick으로 최신화.

이력 `market_prices`는 기본:

```text
60초
```

간격으로 샘플링한다.

설정:

```text
MARKET_AI_KIS_KOSPI200_CODE=A01609
MARKET_AI_KIS_HISTORY_INTERVAL_SECONDS=60
MARKET_AI_KIS_HEARTBEAT_STALE_SECONDS=30
```

현재는 FML/FOPH로 검증한 `A01609`만 `FUTURES:KOSPI200`으로 허용한다.
다른 종목코드는 422로 거부하며, 월물 변경은 실제 조회 후 설정값을 갱신한다.
heartbeat는 `FC_R/day`, `CMEC_R/night`, 장외 `service=null/closed` 조합만 허용한다.
heartbeat 성공만으로 이전 tick 저장 오류(`last_error`)를 지우지 않는다.

## 9.3 2차 실제 실통신 확인 ✅

실제 Bridge 화면에서 확인:

```text
종목코드        A01609
서비스          AUTO
실제 구독       CMEC_R
상태            수신 중
Market AI       연결됨 · N건
```

실제 예:

```text
현재가          1,082.40
전일대비율      -1.57%
누적거래량      16,732
매도1           1,082.55
매수1           1,082.25
수신 Tick       168
Market AI       연결됨 · 46건
```

이후에도 Tick / Market AI 전송 count 증가 확인.

## 9.4 Bridge 상태 API 실제 확인 ✅

```text
GET /api/bridge/kis-efriend/status
```

실제 확인 내용:

```text
provider              kis-efriend
symbol                FUTURES:KOSPI200
connected             true
service               CMEC_R
session               night
instrument_code       A01609
price                  1082.4
change_pct             -1.57
cumulative_volume      16732
ask1                   1082.55
bid1                   1082.25
heartbeat_age_seconds  약 0.6
last_error             null
```

## 9.5 Signal Engine 실제 반영 확인 ✅

```text
GET /api/signal/latest
```

에서 실제 확인:

```text
kospi200_futures:
  available: true
  price: 1085.2
  change_pct: -1.32
  source: kis-efriend:night:CMEC_R:A01609
  freshness_weight: 1.0
  quality: 1.0
```

또한:

```text
weights.kospi.kospi200_futures = 0.20
qualities.kospi200_futures = 1.0
```

확인.

따라서 야간 기준 end-to-end 경로는 실동작 확인 완료:

```text
eFriend Expert
→ CMEC_R
→ C# Bridge
→ Market AI API
→ market_snapshot
→ FUTURES:KOSPI200
→ Signal Engine
```

---

# 10. Bridge 2차 수정본 QA 완료 ✅

2026-08-22 수정본 QA까지 완료했다.

확인 완료:

- KOSPI200 허용 종목코드 검증 (`MARKET_AI_KIS_KOSPI200_CODE=A01609`)
- 잘못된 종목코드 422 거부
- heartbeat `FC_R/day`, `CMEC_R/night`, `service=null/closed` 조합 검증
- tick 저장 오류 발생 후 heartbeat가 기존 `last_error`를 지우지 않음
- 이후 정상 tick 수신 시 오류 상태 정상 해제
- KIS 실제 futures snapshot 보호
- Yahoo `^KS200` proxy의 실제 futures 오인 방지
- Signal Engine freshness / effective weight / `stage6_rule_v2` 회귀 없음
- history 약 60초 sampling 확인
- 주요 API 회귀 확인
- canonical symbol 및 KOSPI 가중치 문서 정합화
- 배포 ZIP의 `__pycache__` / `.pyc` 제거

수정본 기능 재현 QA 결과는 **58/58 PASS**다.

야간 기준 end-to-end는 실증 완료 상태다.

```text
eFriend Expert
→ CMEC_R
→ C# Bridge
→ Market AI API
→ market_snapshot
→ FUTURES:KOSPI200
→ Signal Engine
```

**현재 다음 작업은 주간장 개장 시 `FC_R` 실제 실시간 수신을 1회 확인하는 것이다.**

새 채팅에서 `인수인계`라고 입력했을 때는 자동으로 실통신 확인을 시작하지 말고:

```text
다음 요청: 주간 FC_R 확인
```

이라고 안내한다.

주간 실제 확인 범위:

- 08:45~15:45 `FC_R` 구독
- 실제 체결 tick 수신
- C# Bridge → Market AI 전송
- source가 `kis-efriend:day:FC_R:A01609`인지 확인
- `FUTURES:KOSPI200` snapshot 갱신
- Signal Engine 반영
- 장 종료 시 AUTO unsubscribe / closed 전환

주간 실증 전까지는 코드 경계값 QA는 PASS지만 **실제 `FC_R` live 확인만 미완료**로 취급한다.

---

# 11. QA 이후 남은 운영 작업

## KIS

완료:

```text
야간 CMEC_R 실제 실통신 ✅
C# Bridge → Market AI ✅
Signal Engine 반영 ✅
```

남음:

```text
주간 FC_R 실시간 1회 확인
근월물 자동 rollover 검토
FML 기반 월물 갱신 검토
필요 시 CMEH_R 호가 교차검증
```

## OpenAI

코드는 구현되어 있으나 실제 live API QA 남음.

예정 순서:

1. OpenAI API 프로젝트/결제
2. API Key 생성
3. 로컬 `.env`에만 설정
4. `MARKET_AI_AI_ENABLED=false` 상태에서 수동 3건 분석
5. 결과 / usage / cost 확인
6. 성공 후 자동 분석 활성화

---

# 12. 파일/보존 관련 주의

## 반드시 보존

```text
db/market_signal.db
```

누적 운영 데이터이므로 임의 삭제/초기화 금지.

로컬 PC의:

```text
.env
```

도 유지하되 ZIP/GitHub에는 넣지 않는다.

## eFriend 참고자료

현재는 아래에 보관:

```text
eFriendQA/
├─ expert_manual.pdf
└─ expert_CS_Sample.zip
```

실행 필수는 아니지만 향후 eFriend QA에 재사용 가능하므로 현재는 별도 보관한다.

## GitHub

현재 기준 ZIP에는 `.git/`이 없다.

- 프로젝트 실행과 무관
- 지금은 로컬 개발 기준
- 안정화 후 필요하면 다시 GitHub 연결 가능
- Git 연결 여부 때문에 소스 구조를 변경하지 않는다

---

# 13. 현재 상태 한눈에 보기

```text
Market AI 1~9차                     ✅
시장 데이터 / 뉴스                  ✅
Signal Engine                       ✅
Backtest / Calibration              ✅
투자 대시보드 Market AI 연동         ✅
OpenAI 실제 API live QA             ⏳
eFriend Expert 실시간 환경          ✅
KOSPI200 A01609 확인                ✅
야간 CMEC_R                         ✅ 실증
C# Bridge 1차                       ✅
C# → Market AI Bridge 2차           ✅ 실통신
Signal Engine 실제 KIS futures 반영  ✅
Bridge 2차 QA 수정 반영              ✅
Bridge 2차 수정본 재QA               ✅ 58/58 PASS
주간 FC_R live 확인                 ⏳ 다음 작업
근월물 자동 rollover                ⏳ 이후 검토
GitHub 연동                         ⏸ 현재 불필요
main_dashboard_maintenance_handover  ⏸ 아직 수정 금지
```

---

# 14. 새 채팅 최종 행동 지침

사용자가 최신 ZIP을 첨부하고:

```text
인수인계
```

라고 입력하면 **절대 바로 QA를 시작하지 않는다.**

이 문서 기준 상태를 확인한 뒤 다음만 알려주고 대기한다.

```text
인수인계 확인 완료.
Bridge 2차 수정본 QA는 완료됐습니다.
현재 다음 작업은 KIS eFriend Expert 주간 FC_R 실제 실시간 수신 1회 확인입니다.

다음 요청: 주간 FC_R 확인
```

사용자가 `주간 FC_R 확인`이라고 입력하면 주간장 실통신 확인을 진행한다.
