# Market AI 프로젝트 인수인계

> 기준 시점: 2026-08-27 11:00 KST  
> 기준본: 이 문서와 함께 첨부되는 **최신 `market-ai` ZIP**  
> 현재 상태: **최종 통합 QA 완료 · 필수 후속 작업 없음**

---

## 0. 새 채팅 시작 규칙 — 가장 중요

새 채팅에서 사용자가 최신 `market-ai` ZIP을 첨부한 뒤 **`인수인계`**라고만 입력하면 다음 순서로 처리한다.

1. 첨부된 최신 ZIP 내부의 이 문서(`market_ai_project_handover.md`)와 `README.md`를 먼저 읽는다.
2. 과거 작업을 다시 설명해 달라고 사용자에게 요구하지 않는다.
3. **QA를 자동으로 시작하지 않는다.**
4. 현재 기준이 최종 통합 QA 완료 상태임을 짧게 알려준다.
5. 필수 후속 작업을 임의로 만들지 말고 사용자의 새 요청을 기다린다.

권장 응답 예:

```text
인수인계 확인 완료.
Bridge/AUTO 세션 QA와 Signal v7 phase·checkpoint·대시보드 연동 통합 QA까지 완료된 기준본입니다.
현재 필수 후속 작업은 없습니다.
```

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
- 투자 대시보드의 `dashboard-market-ai.js`와 CSS 배치/유지보수 규칙은 대시보드 프로젝트의 `main_dashboard_maintenance_handover.md`가 담당한다. 이 문서에는 Market AI 백엔드·Bridge 운영 사실만 유지하고 대시보드 유지보수 규칙을 중복 누적하지 않는다.
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
├─ requirements-openai.txt
├─ build-kis-bridge-release.bat
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
│  ├─ kis_efriend.py
│  └─ kospi200_contract.py
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

# 5. Market AI 구현 차수 완료 상태

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
- affected_assets (`INDEX:SOX`만 허용, 구형 `FUTURES:SOX` 제외)
- KOSPI / 반도체 / NASDAQ100 / 유가 / 금리 / USDKRW 영향
- 한국어 rationale

자동 AI 분석 기본값:

```text
MARKET_AI_AI_ENABLED=false
```

실제 OpenAI API Key를 이용한 live QA는 아직 남아 있다.

## 6차 — Signal Engine ✅

현재 엔진 버전:

```text
stage6_rule_v7
```

주요 출력:

- `kospi_score`
- `semiconductor_score`
- `gap_up_probability`
- `up_close_probability`
- `confidence`
- `data_completeness`
- `calibrated`

`calibrated=false`일 때 `gap_up_probability`, `up_close_probability`는 실제 통계확률이 아니라 기존 이름을 유지한 **직접 가중 0~100 Rule Score**다.

현재 KOSPI 구성에서 KOSPI200 선물 기본 가중치:

```text
kospi200_futures = 0.65
```

freshness와 quality가 실제 effective weight에 반영된다.

## 7차 — 투자 대시보드 연동 ✅

Market AI는 기존 투자 대시보드에서 독립 모듈 방식으로 연동했다.

핵심 파일:

```text
js/dashboard-market-ai.js
```

대시보드 연동 원칙:

- `dashboard-market-ai.js`는 main feature graph와 분리된 standalone entry이며 공통 `dashboard-modal.js`의 dialog lifecycle만 공유한다.
- AI Market Signal은 Desktop/Tablet Hero 우측 compact panel로 표시하고, Mobile/실제 터치폰 가로에서는 Hero의 `AI Signal` 버튼으로 같은 panel DOM을 native dialog에 이동·재사용한다.
- GitHub Pages 등 비로컬 기본 모드에서는 Market AI 영역을 숨기고 localhost 요청도 보내지 않으며, `?market-ai-preview=1/2/3`은 내장 예시 데이터만 사용한다.
- 시장 Snapshot, Signal, KIS Bridge status는 endpoint별로 실패를 격리한다. Signal 404/오류/timeout/JSON 오류/stale 때문에 정상 Snapshot을 지우지 않는다.
- checkpoint `basis`는 기존 `weight`를 유지하면서 `configured_weight`, `effective_weight`, `quality`를 함께 제공하고 frontend tooltip은 `effective_weight`를 우선한다.
- 시장 SOX metric은 미국 현물 정규장 중에는 `INDEX:SOX`를 `SOX`로, 정규장 밖에는 `FUTURES:SOX`를 `SOX-F`로 표시한다. Rule Signal 입력은 계속 `INDEX:SOX`만 사용한다.
- 오래된 Signal은 `신호 지연`, stale 기준은 5분이다.

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

## 10차 — KOSPI200 AUTO 근월물 / KRX 세션 라우팅 ✅ 구현

고정 종목코드 중심이던 Bridge를 서버 기준 AUTO 라우팅으로 전환했다.

핵심 파일:

```text
bridges/kospi200_contract.py
bridges/kis_efriend.py
KisKospi200Bridge/MainForm.cs
```

핵심 구현:

- `XKRX` 거래 캘린더 우선 사용
- 캘린더 범위 밖은 한국 공휴일 + KRX 5월 1일/연말 휴장 fallback
- 일회성 정규장 휴장/개장일 및 야간장 휴장 override 지원
- 분기월(3/6/9/12) 실제 최종거래일 계산
- 명목상 두 번째 목요일이 휴장일이면 직전 거래일까지 만기일 이동
- 실제 만기일 15:20부터 다음 분기월로 rollover
- 18:00 야간장은 다음 거래일 소속으로 처리
- 서버 `/api/bridge/kis-efriend/route-code`가 `종목코드|서비스|세션`을 단일 기준으로 반환
- C# Bridge AUTO 모드는 이 route를 5초마다 조회해 `FC_R` / `CMEC_R` / `CLOSED`와 종목코드를 함께 전환
- `MARKET_AI_KIS_KOSPI200_CODE`는 비워두는 것이 기본이며 긴급 고정 override로만 사용

구현은 완료됐지만 **휴장일/만기일/야간장 경계값 QA와 주간 `FC_R` live 실증은 별도 남은 작업**이다.

## 11차 — SOX 현물 전환 / Nasdaq-100 선물 우선순위 재조정 ✅

2026-08-22 최신 기준.

- 대시보드와 Signal Engine의 SOX 기준은 `INDEX:SOX` (`^SOX`) 현물지수다.
- `FUTURES:SOX` (`SOX=F`)는 저유동성 문제 때문에 Signal 입력에서는 계속 제외하되, 대시보드의 정규장 외 시장 metric 표시용으로 yfinance 자동 수집한다. Signal Engine은 `INDEX:SOX`만 사용한다.
- Nasdaq-100 선물 canonical symbol은 `FUTURES:NQ`이며 Yahoo provider symbol은 `NQ=F`다.
- 엔진 버전은 `stage6_rule_v4`로 올려 기존 v3 calibration과 분리한다.
- 핵심 시장 입력 우선순위는 모든 주요 신호에서 `KOSPI200 선물 > SOX 현물지수 > Nasdaq-100 선물`을 유지한다.

가중치:

```text
KOSPI
  KOSPI200 선물  0.22
  SOX 현물지수   0.18
  Nasdaq100 선물 0.14

반도체
  KOSPI200 선물  0.20
  SOX 현물지수   0.18
  Nasdaq100 선물 0.14

갭상
  KOSPI200 선물  0.25
  SOX 현물지수   0.20
  Nasdaq100 선물 0.16
```

나머지 입력은 각 weight map에서 합계 1.00이 되도록 재조정하며 freshness / quality 기반 effective weight 로직은 기존대로 유지한다.


## 12차 — Signal 의미 재정의 / 직접 입력 분리 ✅

2026-08-22 최신 기준. 이 항목이 11차의 가중치 설계보다 우선한다.

대시보드에서 보이는 신호 이름과 실제 입력이 직관적으로 일치하도록 Rule Signal을 재정의했다.
엔진 버전은 `stage6_rule_v5`로 올려 v4 이하 calibration과 분리한다.

```text
코스피
  KOSPI 현물       0.35
  KOSPI200 선물    0.65

반도체
  삼성전자          0.20
  SK하이닉스        0.20
  SOX 현물지수      0.20
  NVIDIA            0.15
  SK하이닉스 ADR    0.15
  Micron            0.10

갭상
  KOSPI200 선물     0.50
  SOX 현물지수      0.25
  Nasdaq100 선물    0.20
  USD/KRW           0.05

상승마감
  KOSPI 현물        0.45
  KOSPI200 선물     0.35
  SOX 현물지수      0.12
  Nasdaq100 선물    0.08
```

운영 원칙:

- 코스피 신호에 반도체/미국주식/금리/유가/뉴스를 섞지 않는다.
- 반도체 신호에는 직접 반도체 자산만 사용한다.
- 갭상은 국내장 개장 전 선행성이 높은 K200 > SOX > NQ 순서를 중심으로 사용한다.
- 상승마감은 더 이상 `코스피 점수 × 55% + 반도체 점수 × 45%` 파생식으로 만들지 않고 직접 weight map을 사용한다.
- 뉴스는 별도 수집/AI 분석 기능으로 유지하되 4개 Rule Signal weight에는 사용하지 않는다.
- Signal Engine의 SOX 기준은 `INDEX:SOX (^SOX)` 현물지수만 유지한다. `FUTURES:SOX (SOX=F)`는 시장 표시 전용으로 catalog/자동수집에 포함하며 Signal 가중치에는 사용하지 않는다.
- freshness/quality 기반 유효가중치와 minimum data weight 정책은 유지한다.
- `/api/signal/weights`는 `up_close` weight까지 반환한다.
- `/api/signal/latest?include_details=true`의 `weights`, `market_components`, `qualities`가 대시보드 상세 tooltip의 단일 근거다.

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
GET  /api/bridge/kis-efriend/contract
GET  /api/bridge/kis-efriend/contract-code
GET  /api/bridge/kis-efriend/route
GET  /api/bridge/kis-efriend/route-code
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

Bridge 운영 UI 기준:

- 기본 실행은 시스템 트레이 상주이며 메인 창은 자동으로 열지 않는다.
- 트레이 우클릭 `View`로 상태 창을 열고 `종료`로 실제 프로세스를 종료한다.
- 트레이 아이콘 더블클릭도 `View`와 동일하다.
- 상태 창 최소화/닫기(X)는 종료가 아니라 트레이 숨김으로 처리한다.
- eFriend ActiveX 초기화 보존을 위해 폼은 생성하되 최초 표시 시 투명/Taskbar 비노출 상태에서 즉시 숨기는 구조를 유지한다.

통합 로컬 실행은 투자 대시보드의 `start-local-server.pyw`가 담당하며 런타임 의존 순서는 아래를 고정한다.

```text
eFriend Expert 프로세스 안정 확인
→ 기존 Bridge/API/Dashboard 잔존 프로세스 정리
→ KIS Bridge 실행 및 프로세스 안정 확인
→ Market AI API health 확인
→ Dashboard HTTP server 실행
```

eFriend 확인 실패 시 기존 `KisKospi200Bridge.exe`도 종료하고 이후 시작을 중단한다. Bridge는 API보다 먼저 뜨므로 AUTO route 첫 요청 실패는 정상적인 짧은 과도 상태이며, Bridge의 기존 주기 재시도로 API 준비 후 자동 복구한다.

## 7.2 KOSPI200 근월물 / AUTO 기준

FML Viewer와 FOPH로 실제 확인한 2026-09 월물 예시는 다음과 같다.

```text
월물          2026-09
종목코드      A01609
```

이 값은 **실증 예시**이며 운영 기본값을 고정하는 문서값이 아니다. 현재 기본 운영은:

```text
MARKET_AI_KIS_KOSPI200_CODE=
```

처럼 비워두고 서버가 AUTO로 근월물을 판정한다.

AUTO 기준:

- KRX `XKRX` 거래 캘린더 우선
- 지원 범위 밖은 한국 공휴일 계산 fallback
- 분기월의 명목상 두 번째 목요일이 휴장일이면 직전 거래일까지 실제 최종거래일을 앞당김
- 실제 최종거래일 15:20부터 다음 분기월 사용
- 18:00 이후 야간장은 다음 거래일 소속
- 예측 불가능한 일회성 일정은 `MARKET_AI_KRX_CLOSED_DATES`, `MARKET_AI_KRX_OPEN_DATES`, `MARKET_AI_KRX_NIGHT_CLOSED_DATES`로 override
- 종목코드 고정은 긴급 상황에서만 `MARKET_AI_KIS_KOSPI200_CODE` 사용

따라서 과거처럼 월물 변경 때 문서/설정의 `A01609`를 수동 갱신하는 방식은 현재 canonical 운영 방식이 아니다.

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

AUTO 기준은 C# Bridge의 로컬 시계 추정이 아니라 Market AI 서버의 `/api/bridge/kis-efriend/route-code` 응답이다. Bridge는 5초마다 route를 확인한다.

기본 세션 정책:

```text
KRX 거래일 08:45~15:45                  → FC_R / day
장외 또는 정규장 휴장                    → CLOSED
야간 개시일이 KRX 거래일인 18:00~익일06:00 → CMEC_R / night
야간 개시일이 주말·공휴일·휴장일          → CLOSED
```

실제 최종거래일에는 만기 월물이 15:20에 끝나므로 15:20~15:45에도 서비스는 `FC_R`이지만 종목코드는 다음 분기월로 전환된다.

## 9.2 Market AI 저장

canonical symbol:

```text
FUTURES:KOSPI200
```

source 형식:

야간:

```text
kis-efriend:night:CMEC_R:<instrument_code>
```

주간:

```text
kis-efriend:day:FC_R:<instrument_code>
```

2026-09 실증에서는 `<instrument_code>`가 `A01609`였다. AUTO rollover 이후에는 서버가 판정한 현재 근월물 코드가 들어간다.

snapshot은 전달된 실제 선물 tick으로 최신화.

이력 `market_prices`는 기본:

```text
60초
```

간격으로 샘플링한다.

설정:

```text
MARKET_AI_KIS_KOSPI200_CODE=
MARKET_AI_KIS_HISTORY_INTERVAL_SECONDS=60
MARKET_AI_KIS_HEARTBEAT_STALE_SECONDS=30
MARKET_AI_KRX_CLOSED_DATES=
MARKET_AI_KRX_OPEN_DATES=
MARKET_AI_KRX_NIGHT_CLOSED_DATES=
```

고정 override가 비어 있으면 서버가 계산한 현재 AUTO 근월물만 `FUTURES:KOSPI200`으로 허용하고 다른 종목코드는 422로 거부한다. 고정 override를 명시한 경우에만 그 코드를 비상 수동 기준으로 사용한다.
heartbeat는 서버가 기대하는 현재 route와 일치하는 `FC_R/day`, `CMEC_R/night`, 장외 `service=null/closed` 조합만 허용한다.
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

- 당시 고정 override 기준 KOSPI200 허용 종목코드 검증 (`A01609`); 이후 10차에서 AUTO expected-contract 검증으로 확장
- 잘못된 종목코드 422 거부
- heartbeat `FC_R/day`, `CMEC_R/night`, `service=null/closed` 조합 검증
- tick 저장 오류 발생 후 heartbeat가 기존 `last_error`를 지우지 않음
- 이후 정상 tick 수신 시 오류 상태 정상 해제
- KIS 실제 futures snapshot 보호
- Yahoo `^KS200` proxy의 실제 futures 오인 방지
- Signal Engine freshness / effective weight / `stage6_rule_v4` 회귀 없음
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

이 58/58 결과는 **Bridge 2차 실통신/저장 검증 기준선**이다. 이후 10차에서 AUTO 근월물·KRX 거래세션 라우팅이 추가되었으므로, 현재 남은 검증 순서는 다음 11장을 따른다.

---

# 11. AUTO 근월물 / KRX 세션 라우팅 후속 검증 순서

AUTO 근월물/세션 라우팅 구현 후의 검증 순서는 **정적·경계값 QA → 실제 주간 live 확인**이다.

## 11.1 AUTO 휴장일 처리 QA — ✅ 53/53 PASS

다음 항목을 코드/테스트 기준으로 확인한다. 실제 eFriend 주간장이 열려 있을 필요는 없다.

- 일반 평일 `08:45 / 15:20 / 15:45 / 18:00 / 06:00` 경계
- 토·일요일 CLOSED
- `XKRX`가 알고 있는 정규 휴장일 CLOSED
- XKRX 범위 밖 fallback 공휴일과 5월 1일/연말 휴장
- `MARKET_AI_KRX_CLOSED_DATES` / `OPEN_DATES` 우선순위
- `MARKET_AI_KRX_NIGHT_CLOSED_DATES`가 18:00 시작일 기준으로만 야간장을 닫는지
- 명목상 두 번째 목요일 휴장 시 실제 최종거래일이 직전 거래일로 이동하는지
- 실제 최종거래일 15:20 전/후 종목코드 rollover
- `/contract`, `/route`, `/route-code`의 종목코드·service·session 일치
- 잘못된 tick/heartbeat route가 422로 거부되는지

2026-08-24 재QA 결과: **53/53 PASS**.

- 일반/주말/공휴일/override/야간장 경계 PASS
- 실제 최종거래일 15:20 rollover PASS
- 현재 서버 route와 다른 tick/heartbeat는 422로 거부 PASS
- CLOSED 중 tick 거부, CLOSED heartbeat만 허용 PASS
- contract/session 계산은 동일 server-side instant를 사용하도록 고정

## 11.2 주간 FC_R 실제 실시간 확인 — ✅ 실증 완료

실제 주간장 개장 시 1회 확인한다.

- 서버 route가 `FC_R/day` 반환
- C# Bridge가 AUTO로 현재 근월물 + `FC_R` 구독
- 실제 체결 tick 수신
- C# Bridge → Market AI 전송
- source가 `kis-efriend:day:FC_R:<현재_AUTO_종목코드>`인지 확인
- `FUTURES:KOSPI200` snapshot 갱신
- Signal Engine 반영
- 장 종료 시 AUTO unsubscribe / CLOSED 전환

2026-08-24 실제 주간장 확인 완료. eFriend Expert 실행 후 AUTO가 `FC_R/day`로 연결되고 K200 선물값이 Market AI/대시보드에 정상 표시됨.

---

# 12. 선택 운영 / 후속 확인

## KIS

완료:

```text
야간 CMEC_R 실제 실통신 ✅
C# Bridge → Market AI ✅
Signal Engine 반영 ✅
KOSPI200 AUTO 근월물 rollover ✅ 구현
서버 기준 FC_R / CMEC_R / CLOSED route ✅ 구현
KRX 캘린더 + fallback + 수동 override ✅ 구현
AUTO 휴장일/만기일/야간장 경계값 QA ✅ 53/53 PASS
주간 FC_R 실제 실시간 1회 확인 ✅
```

선택 항목:

```text
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


## 13차 — Rule Score 출력 정합성 통일 ✅

2026-08-24 운영 QA에서 `gap_up_probability`, `up_close_probability`만 direct weighted score에 `50 + (score - 50) × 0.85` 압축을 한 번 더 적용해, tooltip의 구성 가중치로 재계산한 점수와 화면/API 값이 달라지는 문제를 확인했다.

`stage6_rule_v6`에서 이 legacy 압축을 제거하고 비보정 Rule Signal 4개를 모두 동일한 직접 가중 0~100 점수로 통일한다.

```text
kospi_score             = direct weighted score
semiconductor_score     = direct weighted score
gap_up_probability      = direct weighted score  # legacy field name 유지
up_close_probability    = direct weighted score  # legacy field name 유지
```

운영 원칙:

- `gap_up_probability`, `up_close_probability`라는 기존 API/DB 필드명은 호환성을 위해 유지한다.
- `calibrated=false`이면 네 값 모두 통계 확률이 아니라 0~100 Rule Score다.
- Stage 9 calibration이 실제 적용된 target만 대시보드에서 통계 보정 상승확률로 표시한다.
- 점수 계산식 변경으로 v5 이하 기록/Calibration과 섞이지 않도록 엔진 버전을 `stage6_rule_v6`로 분리한다.
- 기존 DB의 v5 이하 SignalRun은 이력으로 보존하며 소급 재작성하지 않는다.

---

## 14차 — 갭상/상승마감 시간대 의미 분리 ✅

`stage6_rule_v7`부터 갭상과 상승마감은 KRX 현금장 시간대에 따라 의미를 분리한다. v6의 직접 가중 0~100 점수 원칙은 유지한다.

```text
갭상
- 장전(<09:00) / 비거래일: K200 50% + SOX 25% + NQ100 20% + USD/KRW 5% 실시간 예측
- 장중(09:00~15:30): 09:00 직전 마지막 장전 신호를 고정
- 장마감 후(>=15:30): 다음 KRX 거래일 갭 예측으로 전환

상승마감
- 장전: K200 50% + SOX 30% + NQ100 20%
- 장중: KOSPI 45% + K200 35% + SOX 12% + NQ100 8%
- 15:30 이후: 당일 KOSPI 종가 snapshot 확인 시 실제 상승/하락/보합으로 종료
```

보존 규칙:
- 장중 갭상은 개장 후 데이터를 섞어 다시 계산하지 않는다. 장전 체크포인트가 없으면 `--`로 표시한다.
- 장마감 직후 KOSPI 종가 snapshot이 아직 확정되지 않았으면 마지막 장중 상승마감 예측을 잠시 유지하고 `종가 확정 대기`로 표시한다.
- 주말/휴장일에는 다음 KRX 거래일을 대상으로 장전 예측 모드로 동작한다.
- `signal.details.signal_state`에 phase/mode/대상 거래일/체크포인트 시각을 저장한다.
- Stage 9 Calibration은 `calibration_eligible_targets`를 따라 적용하며, 장중/마감확정 `up_close`에는 장전 학습 모델을 적용하지 않는다.
- 계산 의미가 달라졌으므로 엔진 버전은 `stage6_rule_v7`로 분리하며 v6 이하 기록은 이력으로 보존한다.

Signal v7 phase/checkpoint 및 대시보드 연동 통합 QA까지 완료했다. 필수 후속 작업은 없다.

---

# 15. 파일/보존 관련 주의

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

# 16. 현재 상태 한눈에 보기

```text
Market AI 1~14차                    ✅
시장 데이터 / 뉴스                  ✅
Signal Engine                       ✅ stage6_rule_v7
Backtest / Calibration              ✅
투자 대시보드 Market AI 연동         ✅
OpenAI 실제 API live QA             ⏸ 선택 기능 · 보류
eFriend Expert 실시간 환경          ✅
2026-09 A01609 실물월물 확인         ✅ 실증 예시
야간 CMEC_R                         ✅ 실증
C# Bridge 1차                       ✅
C# → Market AI Bridge 2차           ✅ 실통신
Signal Engine 실제 KIS futures 반영  ✅
Bridge 2차 수정본 재QA               ✅ 58/58 PASS
근월물 자동 rollover                ✅ 구현
KRX 세션/휴장 route                 ✅ 구현
AUTO 휴장일 경계값 QA               ✅ 53/53 PASS
주간 FC_R live 확인                 ✅ 실증
Signal v7 phase/checkpoint QA        ✅
Dashboard Front↔Backend 통합 QA     ✅
SOX ↔ SOX-F 시장 표시 전환           ✅
GitHub 연동                         ⏸ 현재 불필요
```

---

# 17. 새 채팅 최종 행동 지침

사용자가 최신 ZIP을 첨부하고:

```text
인수인계
```

라고 입력하면 **절대 바로 QA를 시작하지 않는다.**

이 문서와 실제 최신 소스를 확인한 뒤 다음처럼 안내하고 대기한다.

```text
인수인계 확인 완료.
Bridge/AUTO 세션 QA와 Signal v7 phase·checkpoint·대시보드 Front↔Backend 통합 QA까지 완료된 기준본입니다.
현재 필수 후속 작업은 없습니다.
```

새 채팅에서는 오래된 차수의 미완료 작업을 다시 제안하지 말고 최신 ZIP의 실제 코드와 이 문서를 기준으로 사용자의 새 요청부터 진행한다.
