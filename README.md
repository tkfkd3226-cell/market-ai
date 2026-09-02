# Market AI

로컬 Windows PC에서 시장 데이터, eFriend 실시간 KOSPI·삼성전자·SK하이닉스, 실제 KOSPI200 선물, Signal Engine, Backtest, Calibration을 통합해 **AI Market Signal**을 생성하고 투자 대시보드에 제공하는 프로젝트입니다.

> 자동 주문 시스템이 아닙니다.  
> 주문 API, 계좌번호, 계좌 비밀번호를 사용하지 않습니다.

---

# 1. 현재 운영 구조

## 1.1 Python-free Local Suite

일반 사용자는 대상 PC에 Python, pip, venv를 별도로 설치하지 않습니다.

```text
Desktop shortcut
→ Windows Scheduled Task (Highest)
→ InvestmentLocalSuite.exe + _suite_internal/
→ eFriend Expert
→ 자동 로그인 / 인증서 선택
→ KisKospi200Bridge.exe (KIS eFriend Market Bridge · x86)
→ MarketAI.exe + _internal/
→ FastAPI 127.0.0.1:8001
→ Dashboard embedded HTTP :8000
→ 브라우저 / 시스템 트레이
```

현재 런처와 Market AI는 모두 PyInstaller **onedir** 구조입니다.

```text
InvestmentLocalSuite.exe
_suite_internal/

MarketAI.exe
_internal/
```

`InvestmentLocalSuite.exe`는 관리자 권한이 필요한 현재 자동화 구조를 유지합니다. 일반 실행은 미리 등록한 Highest Scheduled Task를 호출하는 바탕화면 바로가기를 사용하여 매번 UAC 승인을 반복하지 않는 운영 형태를 기준으로 합니다.

Market AI API 자체는 계속 다음 loopback 주소에서 실행됩니다.

```text
http://127.0.0.1:8001
```

외부 Python 실행 파일이나 `python -m uvicorn`, `python -m http.server`, runtime pip 설치에는 의존하지 않습니다.

시스템 트레이는 `InvestmentLocalSuite.exe` 하나로 통합합니다.

```text
Local Suite 상태/로그
KIS eFriend Market Bridge
eFriend 자동 로그인 설정
-------------------------
서버·Bridge 종료
서버·Bridge·eFriend 종료
```

- Bridge는 별도 x86/ActiveX 프로세스로 유지하지만 자체 트레이 아이콘은 표시하지 않습니다.
- `KIS eFriend Market Bridge` 메뉴에서 숨겨진 4종 모니터 창을 열 수 있습니다.
- Bridge 창의 `X`/최소화는 프로세스 종료가 아니라 화면 숨김입니다.
- `서버·Bridge 종료`는 eFriend를 유지합니다.
- `서버·Bridge·eFriend 종료`는 서버 → Bridge → eFriend 순서로 전체 종료합니다.
- eFriend 자동 로그인 정보는 Windows Credential Manager에 저장하며 트레이 메뉴에서 설정/삭제합니다.

---

## 1.2 실행 폴더와 개발 폴더 분리

현재 폴더 역할은 다음과 같습니다.

### 실행 전용

```text
market-ai\
├─ _internal\
├─ _suite_internal\
├─ db\
│  └─ market_signal.db
├─ tools\
│  └─ close-efriend-tray.ps1
├─ .gitignore
├─ AxInterop.ITGExpertCtlLib.dll
├─ Interop.ITGExpertCtlLib.dll
├─ InvestmentLocalSuite.exe
├─ InvestmentLocalSuite.ico
├─ KisKospi200Bridge.exe
├─ KisKospi200Bridge.exe.config
├─ MarketAI.exe
└─ README.md
```

`.env`는 **기본 실행에 필수 파일이 아닙니다.** OpenAI 뉴스 분석이나 운영 override 등 환경설정이 실제로 필요한 경우에만 외부 파일로 둘 수 있습니다.

### 개발 / 재빌드

```text
market-ai-dev\
├─ _internal\
├─ ai\
├─ backtest\
├─ bridges\
├─ calibration\
├─ collectors\
├─ db\
├─ eFriendQA\
├─ KisKospi200Bridge\
├─ market\
├─ news\
├─ signals\
├─ tools\
├─ .env.example
├─ .gitignore
├─ app.py
├─ AxInterop.ITGExpertCtlLib.dll
├─ build-investment-local-suite.ps1
├─ build-kis-bridge-release.bat
├─ build-market-ai.ps1
├─ config.py
├─ Interop.ITGExpertCtlLib.dll
├─ InvestmentLocalSuite.ico
├─ KisKospi200Bridge.exe
├─ KisKospi200Bridge.exe.config
├─ KisKospi200Bridge.sln
├─ market_ai_project_handover.md
├─ MarketAI.exe
├─ requirements.txt
├─ requirements-openai.txt
├─ run_market_ai.py
├─ Sign-InvestmentLocalSuite.ps1
└─ start-local-server.pyw
```

개발 폴더에는 소스·빌드 스크립트와 함께 배포 직전 확인용 빌드 산출물(`MarketAI.exe + _internal/`, KIS Bridge EXE/config/interop DLL)이 존재할 수 있습니다. 이 산출물은 재생성 가능하며, 개발 소스와 빌드 스크립트를 Source of Truth로 보존합니다.

---

## 1.3 재빌드 계약

### Market AI 백엔드 수정

```text
market-ai-dev의 Python source 수정
→ build-market-ai.ps1
→ MarketAI.exe + _internal/
→ market-ai 실행 폴더의 두 항목을 함께 교체
```

`MarketAI.exe`와 `_internal/`은 **항상 한 세트**로 배포합니다.

### Local Suite 수정

```text
start-local-server.pyw 수정
→ build-investment-local-suite.ps1
→ InvestmentLocalSuite.exe + _suite_internal/
→ market-ai 실행 폴더에 함께 배포
```

현재 launcher는 EDR heuristic 회귀를 피하기 위해 **onedir 구조**를 유지합니다. 특별한 이유 없이 onefile 구조로 되돌리지 않습니다.

### KIS Bridge 수정

실행 파일명 `KisKospi200Bridge.exe`는 호환성을 위해 유지하지만, 현재 역할은 K200뿐 아니라 KOSPI·삼성전자·SK하이닉스까지 수신하는 **KIS eFriend Market Bridge**입니다.

```text
KisKospi200Bridge source 수정
→ build-kis-bridge-release.bat
→ Release/x86 빌드
→ 실행 폴더의 EXE/config/interop DLL 갱신
```

### Dashboard 수정

```text
investment-dashboard의 HTML/CSS/JS 수정
→ EXE 재빌드 불필요
```

---

# 2. 외부 Dashboard에서 Market AI 사용

Market AI 계산, eFriend, 인증서, KIS eFriend Market Bridge, SQLite는 계속 로컬 PC에서 동작합니다.

외부 대시보드는 Tailscale Serve를 통해 **API 결과만** 조회합니다.

## 2.1 현재 원격 조회 경로

```text
GitHub Pages Dashboard
https://tkfkd3226-cell.github.io/investment-dashboard
        ↓
dashboard-market-ai.js
        ↓
https://node.tail60a98e.ts.net
        ↓
Tailscale Serve
        ↓
http://127.0.0.1:8001
        ↓
MarketAI.exe
```

Tailscale Serve endpoint:

```text
https://node.tail60a98e.ts.net
```

Market AI API의 8001 포트를 인터넷에 직접 포트포워딩하지 않습니다. FastAPI는 계속 `127.0.0.1:8001`에만 바인딩하고 Tailscale Serve가 tailnet 내부 HTTPS reverse proxy 역할을 합니다.

외부에서 Market AI가 표시되려면:

1. Market AI가 설치된 Windows PC가 켜져 있어야 함
2. Investment Local Suite가 실행 중이어야 함
3. PC의 Tailscale이 연결되어 있어야 함
4. 외부에서 보는 폰/PC도 같은 tailnet에 연결되어 있어야 함

PC나 Tailscale이 꺼져 있어도 GitHub Pages 대시보드의 일반 기능은 계속 사용할 수 있고 Market AI 부분만 사용할 수 없습니다.

---

## 2.2 CORS 운영 계약

GitHub Pages의 JavaScript가 Tailscale Serve 경유 Market AI API를 `fetch()`할 수 있도록 FastAPI `app.py`의 CORS 허용 Origin에 다음을 포함합니다.

```text
https://tkfkd3226-cell.github.io
```

주의:

- CORS에는 `/investment-dashboard` 같은 path가 아니라 **Origin**만 등록합니다.
- 모든 Origin을 의미하는 `*`로 넓히지 않고 실제 대시보드 Origin을 명시적으로 허용하는 현재 방식을 유지합니다.
- GitHub Pages host가 바뀌면 `app.py`의 CORS Origin도 함께 수정해야 합니다.
- `app.py`를 수정한 경우 `build-market-ai.ps1`로 다시 빌드하고 **MarketAI.exe + `_internal/`을 함께 교체**해야 실제 런타임에 반영됩니다.

현재 원격 조회가 정상인지 확인할 때는 Tailscale 연결 상태에서 다음과 같은 API를 직접 확인할 수 있습니다.

```text
https://node.tail60a98e.ts.net/api/health
```

---

# 3. 투자 대시보드 연동

Dashboard용 주요 조회 API:

```text
GET /api/health
GET /api/market-data/snapshot
GET /api/signal/latest?include_details=true
GET /api/bridge/kis-efriend/status
```

현재 Dashboard의 시장 metric은 다음 네 가지를 사용합니다.

```text
KOSPI
KOSPI200 선물
SOX
NQ100 선물
```

KOSPI는 `INDEX:KOSPI` snapshot의 실제 `source`를 기준으로 툴팁에 `KIS eFriend KOSPI 실시간` 또는 Yahoo fallback을 표시합니다. provider 명칭을 Yahoo로 고정하지 않습니다.

SOX 화면 표시도 현재 `INDEX:SOX` 현물지수를 사용합니다. `FUTURES:SOX`는 현재 Dashboard Market AI 표시나 Signal weight의 대체값으로 사용하지 않습니다.

Dashboard는 선택한 과거 투자 기준일과 별개로 **현재 시점의 Market AI**를 표시합니다.

Dashboard frontend의 레이아웃, Mobile dialog, `dashboard-view` 파라미터, CSS/responsive contract는 `investment-dashboard` 프로젝트의 `main_dashboard_maintenance_handover.md`가 Source of Truth입니다.

---

# 4. 현재 기능 상태

```text
시장 데이터 수집                     ✅
뉴스 수집                           ✅
OpenAI 뉴스 분석 코드                ✅ 선택 기능
Signal Engine                       ✅ stage6_rule_v7
Backtest                            ✅
Calibration                         ✅
eFriend Expert C# Market Bridge     ✅
KOSPI JUC_R 실시간                   ✅
삼성전자·SK하이닉스 SC_R 실시간       ✅
국내 현물 Yahoo 장애 fallback         ✅
KOSPI200 주간 FC_R                   ✅
KOSPI200 야간 CMEC_R                 ✅
실제 KIS 선물 → Signal Engine        ✅
KOSPI200 근월물 AUTO rollover       ✅
KRX 휴장일/session 정책             ✅
Dashboard endpoint 실패 격리         ✅
Dashboard 로컬 Market AI 조회        ✅
Dashboard 원격 Tailscale 조회        ✅
GitHub Pages CORS 허용               ✅
Python-free target runtime           ✅
External Python process 불필요       ✅
Local Suite 단일 트레이              ✅
Bridge monitor Local Suite에서 열기   ✅
서버·Bridge / 전체 종료 분리          ✅
OpenAI 실제 API live QA              ⏸ 선택 기능
```

---

# 5. 환경설정

기본 Market AI 실행에는 `.env`가 필요하지 않습니다.

OpenAI 뉴스 분석이나 명시적 운영 override가 필요한 경우에만 `.env.example`을 참고하여 개발/운영 PC에 `.env`를 둘 수 있습니다.

예:

```text
MARKET_AI_AI_ENABLED=false
OPENAI_API_KEY=
```

OpenAI가 비활성화되어 있거나 API Key가 없으면 기본 Market AI 운영 오류로 취급하지 않습니다.

실제 API Key, 인증정보, 비밀값은 GitHub, 공유 ZIP, README, handover에 넣지 않습니다.

---

# 6. 데이터 보존

## 6.1 운영 DB

```text
db/market_signal.db
```

누적 Signal / Backtest / Calibration 및 운영 이력이 들어 있는 mutable resource입니다.

다음 작업에서 삭제하거나 초기화하지 않습니다.

- EXE 빌드
- `_internal` 교체
- 런처 교체
- 문서 정리
- runtime 폴더 cleanup

DB schema/data migration이 필요한 경우에도 기존 운영 데이터 보존을 최우선으로 합니다.

## 6.2 `.env`

`.env`가 존재하는 PC에서는 외부 mutable configuration으로 취급합니다.

- EXE에 포함하지 않음
- GitHub/공유 ZIP에 넣지 않음
- 기본 실행 필수로 가정하지 않음

---

# 7. KIS eFriend Market Bridge

Bridge는 KIS eFriend Expert의 실제 KOSPI200 선물과 국내 현물 3종 real-time 데이터를 Market AI에 전달합니다.

실행 파일명은 호환성을 위해 계속:

```text
KisKospi200Bridge.exe
```

를 사용하지만 UI/운영 명칭은 **KIS eFriend Market Bridge**입니다.

환경:

```text
.NET Framework 4.8
x86
```

현재 실시간 service / canonical symbol:

```text
KOSPI          JUC_R   / 0001    → INDEX:KOSPI
삼성전자       SC_R    / 005930  → KRX:005930
SK하이닉스     SC_R    / 000660  → KRX:000660
KOSPI200 주간  FC_R              → FUTURES:KOSPI200
KOSPI200 야간  CMEC_R            → FUTURES:KOSPI200
```

국내 현물 eFriend source 형식:

```text
kis-efriend:JUC_R:0001
kis-efriend:SC_R:005930
kis-efriend:SC_R:000660
```

KOSPI200 선물 source 형식:

```text
kis-efriend:day:FC_R:<instrument_code>
kis-efriend:night:CMEC_R:<instrument_code>
```

`<instrument_code>`는 AUTO 근월물 정책에 따라 달라지므로 특정 월물 코드를 문서 상수처럼 고정하지 않습니다.

Bridge는 KOSPI200 선물에 대해서 서버의 route 정책을 기준으로 현재 근월물과 `FC_R / CMEC_R / CLOSED` 상태를 따릅니다. KOSPI·삼성전자·SK하이닉스는 위 service/code 조합을 독립 구독합니다.

주요 Bridge API:

```text
POST /api/bridge/kis-efriend/tick
POST /api/bridge/kis-efriend/market-tick
POST /api/bridge/kis-efriend/heartbeat
GET  /api/bridge/kis-efriend/status
GET  /api/bridge/kis-efriend/contract
GET  /api/bridge/kis-efriend/contract-code
GET  /api/bridge/kis-efriend/route
GET  /api/bridge/kis-efriend/route-code
```

heartbeat와 실제 quote freshness는 서로 다른 의미입니다. heartbeat가 정상이어도 오래된 quote를 fresh한 현재가로 간주하지 않습니다.

## 7.1 국내 현물 provider 우선순위

```text
KRX 정규장 중
eFriend 정상 → eFriend 우선
eFriend stale(기본 90초, `MARKET_AI_KIS_FALLBACK_AFTER_SECONDS` 초과) → Yahoo/yfinance 장애 fallback

KRX 정규장 종료 후
마지막 eFriend snapshot 유지
→ 단순히 90초가 지났다는 이유로 Yahoo가 덮어쓰지 않음
```

현재 설치된 eFriend Expert Viewer에서는 NXT/ATS 현물 실시간 TR이 확인되지 않았습니다. 따라서 `SC_R`은 현재 KRX 정규장 실시간 입력으로 취급하며, NXT 체결까지 eFriend가 통합 제공한다고 가정하지 않습니다.

Bridge 자체 트레이 아이콘은 사용하지 않습니다. `InvestmentLocalSuite.exe` 트레이의 `KIS eFriend Market Bridge` 메뉴로 4종 모니터를 열고, 창의 `X`/최소화는 화면만 숨깁니다.

---

# 8. KOSPI200 AUTO route

AUTO 근월물/session의 단일 기준은 Market AI 서버입니다.

`bridges/kospi200_contract.py`가 다음을 책임집니다.

- KRX 거래일 판정
- 휴장일 override
- 분기월/근월물 계산
- 실제 최종거래일 rollover
- 주간 / 야간 / CLOSED session
- Bridge route code

C# Bridge가 독자적인 월물·휴장일 정책을 별도로 유지하지 않습니다.

정확한 시간 경계와 override 값은 현재 소스 및 `.env.example`을 Source of Truth로 합니다.

---

# 9. 데이터 무결성

가장 중요한 원칙:

```text
FUTURES:KOSPI200
= 실제 KIS eFriend KOSPI200 선물
```

Yahoo `^KS200`은 KOSPI200 현물지수 proxy일 뿐 실제 KOSPI200 선물이 아닙니다.

따라서:

- proxy를 실제 `FUTURES:KOSPI200`으로 저장하지 않음
- 실제 KIS futures snapshot을 proxy가 덮어쓰지 않음
- 실제값이 없으면 결측을 허용
- 잘못된 source label을 Signal / Backtest / Calibration에 남기지 않음

기본 정책:

```text
MARKET_AI_ALLOW_KOSPI200_INDEX_PROXY=false
```

---

# 10. Signal Engine

현재 engine version:

```text
stage6_rule_v7
```

## KOSPI 방향

```text
KOSPI 현물       35%
KOSPI200 선물    65%
```

## 반도체 방향

```text
삼성전자          20%
SK하이닉스        20%
SOX 현물지수      20%
NVIDIA            15%
SK하이닉스 ADR    15%
Micron            10%
```

SOX Signal component는:

```text
INDEX:SOX
```

만 사용합니다.

## 갭상

장전/다음 거래일:

```text
KOSPI200 선물     50%
SOX 현물지수      25%
Nasdaq100 선물    20%
USD/KRW            5%
```

- 장전: 당일 갭 예측
- 장중: 09:00 직전 마지막 장전 checkpoint 고정
- 장마감 후/휴장일: 다음 KRX 거래일 예측

## 상승마감

장전:

```text
KOSPI200 선물     50%
SOX 현물지수      30%
Nasdaq100 선물    20%
```

장중:

```text
KOSPI 현물        45%
KOSPI200 선물     35%
SOX 현물지수      12%
Nasdaq100 선물     8%
```

15:30 이후 당일 KOSPI 종가 snapshot이 확인되면 예측값이 아니라 실제 상승/하락/보합 결과로 종료합니다.

`gap_up_probability`, `up_close_probability` 필드명은 API/DB 호환을 위해 유지되며, calibration이 적용되지 않은 상태에서는 통계확률이 아니라 0~100 Rule Score 의미입니다.

---

# 11. Backtest / Calibration

Backtest와 Calibration은 미래 정보를 예측 시점에 역으로 섞지 않는 **No-lookahead** 원칙을 유지합니다.

현재 calibration 방식:

```text
quantile_beta_pava_v1
```

엔진 버전 또는 target 의미가 바뀌면 과거 기록을 현재 의미로 소급 변환하지 않습니다.

---

# 12. OpenAI 뉴스 분석

선택 기능입니다.

기본:

```text
MARKET_AI_AI_ENABLED=false
```

OpenAI를 사용하지 않아도:

- 시장 데이터
- KIS 선물
- Signal Engine
- Backtest
- Calibration
- Dashboard 조회

는 정상 동작합니다.

실제 API Key는 `.env`에서만 관리합니다.

---

# 13. 운영 확인

일반 실행은 바탕화면의 Investment Local Suite 바로가기를 사용합니다.

정상 상태의 핵심 프로세스:

```text
InvestmentLocalSuite.exe
MarketAI.exe
KisKospi200Bridge.exe
efexpertmain.exe
```

시스템 트레이 아이콘은 Investment Local Suite 하나만 표시되는 것이 정상입니다.

기본 로컬 확인:

```text
http://127.0.0.1:8001/api/health
http://localhost:8000/
```

원격 Tailscale 확인:

```text
https://node.tail60a98e.ts.net/api/health
```

Local Suite 종료 contract:

```text
서버·Bridge 종료
→ Dashboard embedded HTTP / MarketAI 종료
→ KIS eFriend Market Bridge 종료
→ eFriend Expert 유지

서버·Bridge·eFriend 종료
→ Dashboard embedded HTTP / MarketAI 종료
→ KIS eFriend Market Bridge 종료
→ eFriend Expert 종료
```

종료 메뉴명은 실제 종료 순서와 일치시킵니다.

---

# 14. GitHub 관계

Market AI 자체의 실행은 `.git/` 또는 GitHub에 의존하지 않습니다.

다만 **Market AI를 소비하는 투자 대시보드**는 현재 GitHub Pages에서 제공되며, 해당 Pages Origin이 Market AI CORS 허용 대상입니다.

```text
Dashboard Origin
https://tkfkd3226-cell.github.io
```

Market AI 소스 저장소 연결 여부와 Dashboard 공개 호스팅을 같은 의미로 취급하지 않습니다.

---

# 15. 인수인계

Market AI의 장기 유지보수 기준은 개발 폴더의:

```text
market-ai-dev\market_ai_project_handover.md
```

를 Source of Truth로 합니다.

새 작업에서는 최신 개발 소스와 handover를 먼저 확인한 뒤 사용자의 현재 요청부터 진행합니다.
