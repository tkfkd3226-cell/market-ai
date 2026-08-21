# Market AI

로컬 PC에서 시장 데이터, 뉴스, 실제 KOSPI200 선물, Signal Engine, Backtest, Calibration을 통합해 **AI Market Signal**을 생성하는 프로젝트입니다.

현재 기준은 **Market AI 1~10차 + KIS eFriend Expert KOSPI200 Futures Bridge 2차**까지 구현된 상태입니다.

> 자동 주문 시스템이 아닙니다.  
> 주문 API, 계좌번호, 계좌 비밀번호를 사용하지 않습니다.

---

## 현재 상태

```text
Market AI 1~9차                     ✅
시장 데이터 수집                     ✅
뉴스 수집                           ✅
OpenAI 뉴스 분석 코드                ✅
Signal Engine                       ✅
Backtest                            ✅
Calibration                         ✅
eFriend Expert C# Bridge            ✅
KOSPI200 야간 CMEC_R 실제 수신       ✅
C# Bridge → Market AI 실통신         ✅
Signal Engine 실제 KIS 선물 반영      ✅
Bridge 2차 QA 수정 반영              ✅
Bridge 2차 수정본 재QA               ✅ 58/58 PASS
KOSPI200 근월물 자동 rollover        ✅ 구현
주간 FC_R 실시간 확인                ⏳ 실증 필요
OpenAI 실제 API live QA             ⏸ 선택 기능 · 보류
```

다음 개발 작업은 **AUTO 휴장일 처리 QA + 주간 `FC_R` 실제 실시간 수신 1회 확인**입니다.

---

# 프로젝트 구조

```text
market-ai/
├─ app.py                     # FastAPI entry
├─ config.py                  # 환경변수 설정
├─ requirements.txt           # 필수 Python 패키지
├─ requirements-openai.txt    # 선택: OpenAI 기능 패키지
├─ .env.example
│
├─ ai/                        # OpenAI 뉴스 구조화
├─ backtest/                  # 예측/실제 결과 평가
├─ bridges/
│  └─ kis_efriend.py          # KIS eFriend Bridge 수신 API/저장
├─ calibration/               # 확률 Calibration
├─ collectors/                # yfinance 시장 collector
├─ db/                        # SQLAlchemy repository / SQLite
├─ market/                    # symbol catalog / provider mapping
├─ news/                      # GDELT news collector
├─ signals/                   # Rule-based Signal Engine
│
├─ KisKospi200Bridge/         # C# WinForms eFriend Expert Bridge
├─ KisKospi200Bridge.sln
│
├─ eFriendQA/                 # eFriend 참고/QA 자료
│  ├─ expert_manual.pdf
│  └─ expert_CS_Sample.zip
│
└─ market_ai_project_handover.md
```

`eFriendQA/`는 실행 필수 폴더가 아니라 향후 eFriend API 검증을 위한 참고자료 보관 위치입니다.

---

# 빠른 실행

## 1. Python 패키지

투자성과 대시보드의 `start-local-server.bat`을 사용하는 일반 실행에서는 필수 패키지가 없으면 최초 실행 때 `requirements.txt`를 자동 설치합니다. 수동 설치가 필요할 때만 아래 명령을 사용합니다.

```bat
python -m pip install -r requirements.txt
```

OpenAI 기능은 선택 사항입니다. 나중에 사용할 때만 아래를 실행합니다.

```bat
python -m pip install -r requirements-openai.txt
```

## 2. 환경설정

기본 Market AI 실행에는 `.env`가 필요하지 않습니다.

OpenAI 뉴스 분석은 선택 기능이며 기본값은 비활성화입니다. 나중에 이 기능을 사용할 때만 `.env.example`을 참고해 로컬 `.env`를 만들고 API Key를 넣습니다.

```text
MARKET_AI_AI_ENABLED=false
OPENAI_API_KEY=
```

OpenAI가 비활성화되어 있거나 API Key가 없으면 오류로 취급하지 않으며, 뉴스 가중치는 Signal의 `data_completeness`와 `confidence` 계산 분모에서도 제외됩니다.

`.env`는 공유 ZIP이나 GitHub에 넣지 않습니다.

## 3. Market AI 실행

투자성과 대시보드와 함께 사용하는 일반 실행은 투자성과 대시보드 프로젝트의 `start-local-server.bat` 하나를 권장합니다. 이 배치 파일이 대시보드 HTTP 서버(8000), Market AI API(8001), KIS KOSPI200 Bridge를 함께 시작합니다.

Market AI API만 단독으로 확인할 필요가 있을 때는 별도 BAT 없이 `market-ai` 폴더에서 직접 실행합니다.

```bat
python -m uvicorn app:app --host 127.0.0.1 --port 8001
```

기본 주소:

```text
http://127.0.0.1:8001
```

Swagger:

```text
http://127.0.0.1:8001/docs
```

기본 상태 확인:

```text
GET /api/health
GET /api/collector/status
GET /api/news/status
GET /api/ai-news/status
GET /api/signal/status
```

---

# KIS eFriend KOSPI200 Futures Bridge

## 실행파일 배포 위치

로컬 운영용 실행파일은 `market-ai` 루트의 다음 파일을 사용합니다.

```text
market-ai\KisKospi200Bridge.exe
```

`KisKospi200Bridge\bin\x86\Debug`는 개발 빌드 산출물 경로이므로 운영 실행 경로로 사용하지 않습니다. `build-kis-bridge-release.bat`가 최신 소스를 Release/x86으로 빌드하고 EXE, config, eFriend interop DLL을 `market-ai` 루트로 복사합니다. 투자성과 대시보드의 `start-local-server.bat`은 루트 실행파일이 없거나 소스보다 오래된 경우 이 빌드를 자동 시도합니다.

## 사전 조건

- eFriend Expert 설치
- Open API 사용 가능 상태
- eFriend Expert 로그인
- Visual Studio 2022 / `.NET 데스크톱 개발`
- Bridge:
  - `.NET Framework 4.8`
  - `x86`
- eFriend Expert와 Bridge는 관리자 권한 실행 기준

KOSPI200 근월물은 기본적으로 `AUTO`로 해석합니다.

현재 예시:

```text
2026-09 → A01609
```

AUTO 월물 판정의 단일 기준은 Market AI 서버입니다. 서버는 KRX `XKRX` 거래 캘린더를 우선 사용하고, 캘린더 지원 범위를 벗어난 미래 날짜는 한국 공휴일(설·추석·석가탄신일 포함) 계산으로 fallback합니다. KRX 규칙대로 명목상 두 번째 목요일이 휴장일이면 직전 거래일까지 최종거래일을 순차적으로 앞당깁니다.

실제 최종거래일에는 만기 월물이 15:20에 종료되므로 **15:20부터 다음 분기월로 rollover**합니다. 18:00 이후 야간거래는 다음 거래일에 속하며 이미 새 근월물을 사용합니다. C# Bridge의 `AUTO`는 자체 달력/시간 판정을 하지 않고 Market AI의 `/api/bridge/kis-efriend/route-code`를 5초마다 조회해 같은 월물과 `FC_R` / `CMEC_R` / `CLOSED` 상태를 그대로 따릅니다.

예측할 수 없는 임시휴장·선거일 등 거래소 특수 일정은 `.env`의 `MARKET_AI_KRX_CLOSED_DATES` / `MARKET_AI_KRX_OPEN_DATES`로 날짜만 override할 수 있습니다. 정규장은 열지만 해당 날짜 18시에 개시하는 야간장만 특별 휴장하는 경우에는 `MARKET_AI_KRX_NIGHT_CLOSED_DATES`를 사용합니다. 종목 자체를 긴급 고정해야 할 때만 `MARKET_AI_KIS_KOSPI200_CODE` 또는 Bridge 종목코드 입력란을 사용합니다.

---

## 실시간 서비스

주간:

```text
FC_R
```

야간:

```text
CMEC_R
```

Bridge AUTO 기준:

```text
KRX 거래일 08:45~15:45 → FC_R
장외/정규 휴장일           → CLOSED / 구독 해제
야간 개시일이 KRX 거래일인 18:00~익일06:00 → CMEC_R
야간 개시일이 주말·공휴일·휴장일          → CLOSED / 구독 해제
```

야간 휴장 여부는 **야간장이 시작되는 날짜**를 기준으로 판단합니다. 따라서 목요일 정규장이 정상 개장했다면 금요일이 공휴일이어도 목요일 18:00~금요일 06:00 야간장은 열리고, 공휴일 당일 18:00에 시작할 야간장은 열리지 않습니다.

AUTO session check:

```text
5초
```

eFriend raw Tick은 UI에서 모두 받지만 Market AI 전송은 최대:

```text
5초에 1회
```

heartbeat:

```text
10초
```

---

# KIS → Market AI 연동

Bridge가 Market AI에 사용하는 API:

```text
POST /api/bridge/kis-efriend/tick
POST /api/bridge/kis-efriend/heartbeat
GET  /api/bridge/kis-efriend/status
GET  /api/bridge/kis-efriend/contract
GET  /api/bridge/kis-efriend/contract-code
GET  /api/bridge/kis-efriend/route
GET  /api/bridge/kis-efriend/route-code
```

canonical symbol:

```text
FUTURES:KOSPI200
```

source:

야간:

```text
kis-efriend:night:CMEC_R:A01609
```

주간:

```text
kis-efriend:day:FC_R:A01609
```

실시간 snapshot은 KIS futures tick으로 갱신합니다.

SQLite history는 거래소 raw Tick을 모두 저장하지 않고 기본:

```text
60초
```

간격으로 샘플링합니다.

관련 환경변수:

```text
# blank = AUTO rollover, value = emergency fixed-code override
MARKET_AI_KIS_KOSPI200_CODE=
MARKET_AI_KIS_HISTORY_INTERVAL_SECONDS=60
MARKET_AI_KIS_HEARTBEAT_STALE_SECONDS=30
# one-off KRX calendar overrides (comma-separated YYYY-MM-DD)
# MARKET_AI_KRX_CLOSED_DATES=
# MARKET_AI_KRX_OPEN_DATES=
# MARKET_AI_KRX_NIGHT_CLOSED_DATES=
```

`MARKET_AI_KIS_KOSPI200_CODE`를 비워두면 서버가 현재 KRX 거래일·실제 최종거래일·15:20 cutoff를 기준으로 AUTO 근월물만 허용하며, 다른 종목코드는 `FUTURES:KOSPI200`으로 저장하지 않습니다. Bridge가 AUTO이면 서버가 알려주는 동일 코드와 현재 세션 정책(`FC_R` / `CMEC_R` / `CLOSED`)으로 자동 구독·해제합니다.

`MARKET_AI_KRX_CLOSED_DATES` / `MARKET_AI_KRX_OPEN_DATES`는 캘린더에 아직 반영되지 않은 일회성 정규장 휴장/개장일을 위한 날짜 override입니다. `MARKET_AI_KRX_NIGHT_CLOSED_DATES`는 정규장은 열지만 해당 날짜 18시에 시작하는 야간장만 특별 휴장하는 경우를 위한 override입니다. fallback 캘린더는 KRX 고유 휴장인 5월 1일 근로자의 날과 연말 휴장일까지 반영합니다. 종목코드 고정 override는 마지막 비상수단으로만 사용합니다.

heartbeat도 주간 `FC_R/day`, 야간 `CMEC_R/night`, 장외 `service=null/closed` 조합만 허용합니다.

---

# 실제 야간 연동 확인 상태

야간 `CMEC_R`은 실제 eFriend Expert 시세로 실증 완료했습니다.

확인된 경로:

```text
eFriend Expert
→ CMEC_R
→ C# Bridge
→ Market AI API
→ market_snapshot
→ FUTURES:KOSPI200
→ Signal Engine
```

Bridge 화면에서:

- 실제 가격 갱신
- 전일대비율
- 거래량
- 매도1 / 매수1
- Tick count
- `Market AI 연결됨 · N건`

을 확인했고, 사용자가 보는 증권앱의 야간선물 가격과 동일함을 확인했습니다.

`GET /api/signal/latest`에서도:

```text
kospi200_futures.available = true
source = kis-efriend:night:CMEC_R:A01609
freshness_weight = 1.0
quality = 1.0
```

으로 실제 KIS 선물이 Signal Engine에 반영되는 것을 확인했습니다.

주간 `FC_R`은 코드가 준비되어 있으나 실제 주간장에서 1회 live 확인이 남아 있습니다.

---

# 데이터 무결성 원칙

가장 중요한 원칙입니다.

Yahoo:

```text
^KS200
```

은 KOSPI200 **현물지수 proxy**일 뿐 실제 KOSPI200 선물이 아닙니다.

따라서:

- `FUTURES:KOSPI200`에 실제 선물처럼 저장하지 않음
- proxy를 사용할 경우 source에서 명확히 표시
- 실제 KIS futures snapshot을 proxy가 덮어쓰지 못하도록 보호
- Signal / Backtest / Calibration에 잘못된 label을 남기지 않음

기본값:

```text
MARKET_AI_ALLOW_KOSPI200_INDEX_PROXY=false
```

---

# 주요 API

## 시장 데이터

```text
GET /api/market-data/catalog
GET /api/market-data/snapshot
GET /api/market-data/history/{symbol}
```

## Collector

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

## OpenAI 뉴스

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

현재 Signal Engine:

```text
stage6_rule_v3
```

반도체 방향 입력은 현재 다음처럼 구성합니다.

```text
한국: 삼성전자 + SK하이닉스
미국: SK hynix ADR + NVIDIA + Micron + SOX 선물(SOX=F)
```

`INDEX:KOSPI(^KS11)`와 `INDEX:SOX(^SOX)`는 실제 지수 표시용으로 수집하며,
`FUTURES:SOX(SOX=F)`는 반도체 Signal 입력에 사용합니다.

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

# OpenAI 뉴스 분석 (선택 기능)

Market AI의 필수 기능이 아닙니다. OpenAI를 사용하지 않아도 시장 데이터, KIS 선물, Signal Engine, Backtest, Calibration은 정상 동작합니다.

기본:

```text
MARKET_AI_AI_ENABLED=false
```

나중에 기능을 사용할 경우의 live test 권장 순서:

```text
1. 로컬 .env에 OPENAI_API_KEY 설정
2. Market AI 재시작
3. GET  /api/ai-news/status
4. POST /api/news/run-once
5. POST /api/ai-news/run-once?limit=3
6. GET  /api/ai-news/latest
7. usage / cost 확인
8. 정상 확인 후 자동 분석 활성화
```

API Key는 채팅, ZIP, GitHub에 넣지 않습니다.

API Key가 없으면 `disabled_by_config`로 취급하며 오류가 아닙니다. API Key가 있어도 `MARKET_AI_AI_ENABLED=false`이면 자동 분석은 `manual_only` 상태로 유지되고 `POST /api/ai-news/run-once` 수동 테스트는 가능합니다. 비활성 상태에서는 과거 DB에 AI 뉴스 분석이 남아 있어도 새 Signal 계산에는 사용하지 않습니다.

---

# Backtest / Calibration

Backtest 공식 forecast는 기본적으로:

```text
09:00 KST 직전 가장 최근 Signal
```

을 사용하며, 기본 최대 forecast age는:

```text
12시간
```

입니다.

Calibration 방식:

```text
quantile_beta_pava_v1
```

기본 최소 조건:

```text
평가 완료 30일 이상
positive 5개 이상
negative 5개 이상
서로 다른 raw score 3개 이상
```

No-lookahead 원칙을 유지합니다.

---

# 보존해야 할 파일

## 운영 DB

```text
db/market_signal.db
```

누적 이력 데이터가 포함되므로 업데이트/패치 시 임의 삭제하거나 덮어쓰지 않습니다.

## 로컬 비밀설정

```text
.env
```

PC에서는 유지하지만 공유 ZIP에는 넣지 않습니다.

## eFriend 참고자료

```text
eFriendQA/
├─ expert_manual.pdf
└─ expert_CS_Sample.zip
```

현재는 별도 보관합니다. 실행 필수는 아니지만 향후 eFriend QA에 사용할 수 있습니다.

---

# GitHub 상태

현재 프로젝트 운영에 GitHub가 필요하지 않습니다.

현재 기준 ZIP에는:

```text
.git/
```

이 포함되어 있지 않습니다.

당분간 로컬 프로젝트로 유지하고, 안정화 후 필요할 때 새로 GitHub를 연결하면 됩니다.

---

# 인수인계

상세 작업 히스토리와 다음 QA 범위는:

```text
market_ai_project_handover.md
```

를 기준으로 합니다.

새 채팅에 최신 `market-ai` ZIP을 첨부하고:

```text
인수인계
```

라고 입력하면, 먼저 인수인계 문서를 읽고 **작업을 자동 시작하지 않은 상태에서** 다음 작업을 안내해야 합니다.

Bridge 2차 수정본 QA는 **58/58 PASS로 완료**되었습니다.

현재 다음 요청:

```text
주간 FC_R 확인
```

즉 새 채팅에서는:

```text
인수인계
```

→ 인수인계 확인 응답

→ 사용자가 주간장 실통신 확인이 가능한 시점에 직접:

```text
주간 FC_R 확인
```

을 입력

→ 실제 `FC_R` 수신 → C# Bridge → Market AI → Signal Engine 경로를 확인

순서로 진행합니다.

### 통합 로컬 실행

평소에는 `market-ai` 폴더에서 별도 BAT를 실행하지 않습니다. 형제 폴더인 투자 대시보드의 `start-local-server.bat` 하나가 Dashboard(:8000), Market AI API(:8001), KIS KOSPI200 Bridge를 함께 실행합니다. 최초 실행에서 Market AI 핵심 Python 패키지가 없으면 자동으로 `requirements.txt`를 설치합니다. OpenAI 기능은 선택 사항이며 기본 `requirements.txt`에는 포함되지 않습니다. 나중에 OpenAI 기능을 사용할 때만 `pip install -r requirements-openai.txt`를 실행합니다.
