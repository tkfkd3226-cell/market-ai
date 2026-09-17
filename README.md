# Market AI

> **문서 성격**: 이 README는 `market-ai` **운영 Runtime 저장소**의 실행, 상태 확인, 장애 분리, 데이터 보존, 배포 파일 구성을 설명합니다.  
> 개발 구조·빌드 상세·회귀 contract는 `market-ai-dev/market_ai_project_handover.md`, 평가 기준은 `market-ai-dev/market_ai_evaluation_guide.md`를 따릅니다.

Market AI는 Windows + KIS eFriend Expert 환경에서 KOSPI·KOSPI200 선물·동적 KRX 보유종목 시세, Signal Engine, Backtest/Calibration 결과를 투자 Dashboard에 제공합니다. 자동 주문 시스템이 아니며 주문 API·계좌번호·계좌 비밀번호를 사용하지 않습니다.

---

# 1. 운영 Runtime 구조

## 1.1 기본 실행 흐름

```text
Desktop shortcut
→ Windows Scheduled Task (Highest)
→ InvestmentLocalSuite.exe + _suite_internal/
→ eFriend Expert
→ KisKospi200Bridge.exe (x86 ActiveX Bridge)
→ MarketAI.exe + _internal/
→ FastAPI 127.0.0.1:8001
→ Remote GET-only proxy 127.0.0.1:8002
→ Tailscale Serve (optional, :8002만 공개)
→ Dashboard embedded HTTP :8000
```

일반 사용자는 Python, pip, venv를 별도로 설치하지 않습니다. `InvestmentLocalSuite.exe`와 `MarketAI.exe`는 PyInstaller **onedir** 구조이며 EXE와 support directory를 항상 같은 빌드 세트로 취급합니다.

```text
InvestmentLocalSuite.exe + _suite_internal/
MarketAI.exe           + _internal/
```

FastAPI full API는 코드에서 `127.0.0.1:8001`로 고정합니다. LAN bind나 다른 포트로 우회하지 않고, 원격 조회는 8002 GET-only 경계를 사용합니다.

## 1.2 운영 폴더

```text
market-ai\
├─ _internal\
├─ _suite_internal\
├─ db\
│  ├─ .gitkeep
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

`market-ai`는 실행·배포 전용 Runtime 저장소입니다. Python/C#/JS 원본의 개발 Source of Truth는 `market-ai-dev`입니다.

## 1.3 시스템 트레이

시스템 트레이는 `InvestmentLocalSuite.exe` 하나가 소유합니다.

```text
Local Suite 상태/로그
KIS eFriend Market Bridge
eFriend 자동 로그인 설정
-------------------------
서버·Bridge 종료
서버·Bridge·eFriend 종료
```

Bridge는 별도 x86 프로세스지만 자체 tray icon을 만들지 않습니다. Bridge 창의 `X`/`Alt+F4`와 최소화는 프로세스 종료가 아니라 Hide이며, 실제 종료는 Local Suite 메뉴가 담당합니다.

---

# 2. Web Monitor

Market AI backend는 read-only 운영 Monitor를 제공합니다.

```text
로컬
http://127.0.0.1:8001/monitor/

폰/외부 tailnet
https://node.tail60a98e.ts.net/monitor/
```

Runtime asset은 다음 3파일입니다.

```text
_internal/monitor/
├─ index.html
├─ monitor.css
└─ monitor.js
```

운영 contract:

- 10초 polling으로 read-only quote-universe endpoint를 조회하며 Dashboard client lease를 만들거나 연장하지 않습니다.
- process-memory 최신값을 우선하고 장마감·재시작 복원에서만 durable `MarketSnapshot`을 fallback합니다.
- K200/KOSPI와 보유종목은 사용자 의미의 상태·세션·시간·현재가·등락률만 표시하고 내부 TR/service code는 화면에 노출하지 않습니다.
- Web/Tablet은 남는 viewport 높이 때문에 카드가 늘어나지 않고 콘텐츠 자연 높이를 유지합니다.
- **Monitor 페이지 자체**는 Phone viewport에서 시장 카드 2열, 보유종목 카드 2열을 유지하며 좁은 폭에서도 카드 내부 텍스트가 부모 폭을 밀어내지 않아야 합니다. 정확한 spacing·padding 값은 `monitor.css`를 기준으로 합니다.
- Dashboard embedded Monitor에서는 외부 닫기 버튼과 theme toggle이 겹치지 않게 header tool 영역을 확보합니다.

투자 Dashboard의 `실시간 시세`는 Market AI 연결이 확인된 동안에만 노출됩니다. Web/Tablet은 Monitor content height를 받아 compact modal로 표시하고, Phone은 Main action modal의 responsive 외곽 geometry를 상속해 같은 Monitor를 엽니다. embedded Monitor의 정확한 spacing·radius·padding은 Dashboard CSS와 `market-ai-dev`의 Monitor UI contract를 기준으로 합니다.

### Monitor-only 빠른 운영 반영

`monitor/index.html`, `monitor.css`, `monitor.js` **정적 3파일만** 수정한 경우에는 Market AI를 종료한 뒤 운영 `market-ai\_internal\monitor\`의 동일 파일만 교체할 수 있습니다. 이 경우 `MarketAI.exe` 재빌드는 필요하지 않습니다.

단, 다음 중 하나라도 함께 바뀌면 `market-ai-dev`에서 `build-market-ai.ps1`로 정식 재빌드합니다.

- `app.py` 또는 backend Python
- Monitor mount/packaging 방식
- build script / dependency
- frozen runtime 동작 contract

운영에 직접 덮어쓴 Monitor 수정은 반드시 `market-ai-dev/monitor/`에도 동일하게 남겨 다음 정식 빌드에서 사라지지 않게 합니다.

---

# 3. Runtime 업데이트 / 재빌드

정식 build는 `market-ai-dev`에서 수행하며 **성공한 build 결과를 sibling `market-ai`에 자동 반영**합니다. 일반적인 backend/Bridge/Local Suite 업데이트에서 dev 산출물을 사람이 운영 폴더로 수동 복사하지 않습니다.

필수 배치:

```text
parent\
├─ market-ai-dev\
└─ market-ai\
```

공식 build/deploy는 두 폴더가 같은 부모의 형제인지, 이름이 정확한지, 운영 `market-ai\README.md`가 존재하는지 먼저 확인합니다.

변경 대상에 따라 필요한 build만 수행합니다.

| 변경 대상 | 실행할 개발 build | 성공 시 운영 반영 |
|---|---|---|
| Market AI backend | `build-market-ai.ps1` | `MarketAI.exe + _internal/` 자동 clean replacement |
| Web Monitor 정적 3파일만 | 재빌드 선택 | `_internal/monitor/` 3파일 direct replacement fast-path 가능 |
| KIS eFriend Market Bridge | `build-kis-bridge-release.bat` | EXE/config + Interop DLL 4파일 자동 반영 |
| Investment Local Suite / 8002 proxy | `build-investment-local-suite.ps1` | `InvestmentLocalSuite.exe + _suite_internal/` 자동 clean replacement |
| Dashboard HTML/CSS/JS | Market AI build 불필요 | Dashboard 저장소만 배포 |

### 자동 Runtime 종료

build가 운영 component를 교체해야 할 때 `market-ai-dev/tools/runtime-stop.ps1`이 실행 중인 Local Suite에 트레이 메뉴 **`서버·Bridge 종료`**와 같은 종료 명령을 우선 요청합니다.

```text
Dashboard embedded HTTP / MarketAI / Bridge / Local Suite 종료
eFriend Expert 유지
8000 / 8001 / 8002 free 확인
```

관리자 권한 Local Suite 때문에 필요한 경우 stop helper만 UAC 승격될 수 있습니다. 정상 tray 종료가 되지 않을 때도 sibling `market-ai`에서 실행된 예상 프로세스만 fallback 대상으로 하며, eFriend는 종료 대상으로 삼지 않습니다. 8000/8001/8002를 무관한 프로그램이 사용 중이면 그 프로그램을 강제로 종료하지 않고 build가 실패합니다.

build 완료 후 Runtime은 **자동 재시작되지 않습니다.** 여러 component를 재빌드한다면 모두 끝낸 뒤 평소 방식으로 `InvestmentLocalSuite.exe`를 한 번 실행합니다.

### 배포 안전 경계

정식 build는 component를 검증된 단위로 교체하고 배포 결과를 검증합니다. 실패 시 old/new 파일을 섞어 성공으로 처리하지 않습니다. 세부 rollback·SHA-256·staging 구현은 개발 handover가 소유합니다.

다음 운영 자원은 build artifact가 아니므로 일반 component 배포가 덮어쓰지 않습니다.

```text
db/market_signal.db
.env                 # 실제 사용하는 경우
README.md
.gitignore
InvestmentLocalSuite.ico
tools/close-efriend-tray.ps1
start-local-server.log
```

특히 dev의 `db/market_signal.db`를 운영 DB 위에 복사하지 않습니다.


### Build 성공 판정

콘솔 마지막의 다음 형식이 나타나야 해당 component의 **build + 운영 배포까지 완료**된 것입니다.

```text
... BUILD + DEPLOY : SUCCESS
Build         : PASS
Runtime stop  : PASS
Deploy verify : PASS
Dev cleanup   : PASS
```

MarketAI에는 staged Smoke QA, Local Suite에는 Authenticode signature 검증 등 component별 추가 PASS가 표시됩니다. 중간 `[ERROR]`가 발생하거나 최종 SUCCESS가 없으면 운영 반영 완료로 판단하지 않습니다.

### 전체 재빌드 권장 순서

```text
1. market-ai-dev\build-market-ai.ps1
2. market-ai-dev\build-kis-bridge-release.bat
3. market-ai-dev\build-investment-local-suite.ps1
4. 세 build의 최종 SUCCESS 확인
5. InvestmentLocalSuite.exe 실행
6. 아래 운영 확인 절차 수행
```

세 component는 dev root의 다른 runtime 산출물을 prerequisite로 사용하지 않으므로 필요한 component만 독립적으로 재빌드할 수 있습니다.

# 4. 원격 Dashboard / Tailscale

## 4.1 포트와 경계

```text
GitHub Pages Dashboard
→ https://node.tail60a98e.ts.net
→ Tailscale Serve
→ 127.0.0.1:8002 GET-only proxy
→ 127.0.0.1:8001 MarketAI.exe
```

- 8001: 로컬 full API. Bridge tick/heartbeat와 로컬 write/maintenance가 직접 사용합니다.
- 8002: 원격 Dashboard/Monitor용 GET-only proxy입니다.
- `POST / PUT / PATCH / DELETE`는 8002에서 405로 차단합니다.
- allowlist 밖 GET도 backend로 전달하지 않습니다.
- remote quote client는 backend capacity 정책을 따르며 local Dashboard를 밀어내지 않습니다.
- 8002가 기동하지 못하거나 Serve 안전 상태를 확인할 수 없으면 remote 기능은 fail-closed로 둡니다. 로컬 8001 기동까지 실패로 취급하지 않습니다.

원격 사용 조건:

1. Market AI Windows PC가 켜져 있음
2. Investment Local Suite 실행 중
3. PC Tailscale 연결
4. 외부 폰/PC도 같은 tailnet 연결

원격 기능이 끊겨도 GitHub Pages Dashboard의 저장 JSON 기반 기능은 계속 사용할 수 있습니다.

## 4.2 CORS

GitHub Pages Origin은 FastAPI CORS 허용 대상입니다.

```text
https://tkfkd3226-cell.github.io
```

CORS는 browser origin 허용 규칙일 뿐 write 접근제어가 아닙니다. 원격 write 차단은 8002 GET-only proxy가 담당합니다.

---

# 5. Dashboard 연동

Dashboard는 Market AI를 두 용도로 사용합니다.

1. 현재 시장 / AI Signal
2. 현재 평가 대상 거래일 보유종목의 현재가 overlay

주요 조회 API:

```text
GET /api/health
GET /api/market-data/snapshot
GET /api/signal/latest?include_details=true
GET /api/bridge/kis-efriend/status
GET /api/bridge/kis-efriend/quote-universe
GET /api/market-data/krx-quotes?tickers=...&client_id=...
```

`/api/market-data/snapshot`의 각 row에는 거래소 캘린더로 판정한 `input_status`가 포함됩니다. Dashboard 시장 카드는 이 상태를 우선 사용하므로 미국 휴장일·조기폐장일의 직전 확정값을 단순 경과시간만으로 `데이터 지연` 처리하지 않습니다.

## 5.1 보유종목 quote 의미

Dashboard가 수량·원가·투입원금·매매흐름·실현손익·historical snapshot을 소유하고, Market AI는 ticker별 현재가와 source/session/usable 상태만 제공합니다.

```text
개별주식
09:00~15:30  open / 정상
15:30~20:00  extended / 시간외
20:00 이후   closed / 장마감

ETF
09:00~15:30  open / 정상
15:30 이후   closed / 장마감
```

원칙적으로 KST 오늘에는 `usable=true` quote만 화면 평가 계산에 overlay합니다. 자정 이후 다음 KRX 정규장 시작 전에는 `observed_at`이 최근 완료 거래일과 일치하는 확정 `closed + usable` quote를 그 거래일 화면에만 이어서 적용합니다. unusable ticker만 저장 JSON 값으로 fallback하며 그보다 오래된 과거 날짜에는 Market AI quote를 overlay하지 않습니다.

장마감·재시작에서는 backend가 신뢰 가능한 최근 완료 KRX 거래일의 KIS snapshot을 `closed + usable=true`로 복원할 수 있습니다. 반대로 다음 정규장 시작 뒤의 전일 값, 더 오래된 snapshot, 비-KIS source, subscription/fresh-tick 조건을 충족하지 못한 값은 current quote로 복원하지 않습니다. 정확한 승격 조건은 `market_ai_project_handover.md`가 소유합니다.

Market AI overlay는 화면용이며 `prices.json`, 성과 snapshot, Pension JSON, GAS에 저장하지 않습니다.

---

# 6. KIS eFriend Market Bridge

Bridge는 KIS eFriend Expert의 실제 KOSPI200 선물, KOSPI 지수, 동적 KRX 보유종목 `SC_R`를 Market AI에 전달합니다.

```text
KOSPI          JUC_R / 0001
KOSPI200 주간  FC_R
KOSPI200 야간  CMEC_R
KRX 현물/ETF   SC_R / 6자리 ticker
```

Signal baseline `005930`, `000660`은 물리 stream으로 유지될 수 있지만 Dashboard valuation은 실제 active client 보유 universe와 fresh-tick lifecycle을 따릅니다.

특정 ticker subscription 장애는 전체 quote 실패로 확대하지 않습니다. 장애 후 `subscribed=true`로 돌아왔다는 사실만으로 과거 quote를 다시 usable하게 만들지 않고 새 실제 tick을 기다립니다.

KOSPI200 근월물/session route의 단일 기준은 Market AI 서버입니다. 정확한 rollover, 휴장일 override, provider fallback, Signal weight 등 개발 정책은 `market_ai_project_handover.md`를 Source of Truth로 합니다.

---

# 7. 데이터 보존 / 환경설정

## 7.1 운영 DB

```text
db/market_signal.db
```

Signal / Backtest / Calibration 및 운영 이력이 누적되는 mutable resource입니다. 다음 작업에서 삭제하거나 초기화하지 않습니다.

- EXE 빌드
- `_internal` 교체
- launcher 교체
- Monitor 정적 파일 교체
- 문서 정리
- runtime cleanup

Git에서는 아래를 제외합니다.

```text
db/market_signal.db
db/market_signal.db-wal
db/market_signal.db-shm
```

새 PC에서 기존 이력을 이어가려면 DB를 별도 백업/복사합니다.

## 7.2 `.env`

기본 Market AI 실행에는 `.env`가 필수는 아닙니다. OpenAI 뉴스 분석이나 명시적 optional 설정이 필요한 경우에만 사용하고 Git/공유 ZIP에 넣지 않습니다.

```text
MARKET_AI_AI_ENABLED=false
OPENAI_API_KEY=
```

실제 API Key와 인증정보는 README나 소스에 넣지 않습니다.

---

# 8. 운영 확인

정상 상태의 핵심 프로세스:

```text
InvestmentLocalSuite.exe
MarketAI.exe
KisKospi200Bridge.exe
efexpertmain.exe
```

기본 로컬 확인:

```text
http://127.0.0.1:8001/api/health
http://127.0.0.1:8002/api/health
http://127.0.0.1:8001/monitor/
http://localhost:8000/
```

원격 확인:

```text
https://node.tail60a98e.ts.net/api/health
https://node.tail60a98e.ts.net/monitor/
```

원격 QA에서 최소한 다음을 확인합니다.

- health / Monitor / 허용 read endpoint 정상
- `/monitor` → `/monitor/` canonical redirect
- allowlist 밖 GET → 404
- remote write method → 405
- 잘못된 quote 요청 / capacity 초과 → 422
- Bridge POST는 localhost 8001 direct path 유지

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

---

# 9. 현재 기능 요약

| 영역 | 상태 |
|---|---|
| 시장 데이터 / Signal Engine | ✅ |
| KIS KOSPI / KOSPI200 선물 | ✅ |
| 동적 KRX 보유종목 quote / subscription health | ✅ |
| ETF 장마감 / 개별주식 시간외·장마감 상태 | ✅ |
| Dashboard 오늘·제한된 직전 완료 거래일 valuation overlay | ✅ |
| Web Monitor / Tailscale Monitor | ✅ |
| Remote GET-only proxy | ✅ |
| Python-free target runtime | ✅ |
| Backtest / Calibration | ✅ |
| OpenAI 뉴스 분석 | 선택 기능 |

현재 Signal Engine version은 `stage6_rule_v8`입니다. 정확한 산식·weight·calibration contract는 개발 handover를 따릅니다.

---

# 10. GitHub / 인수인계

운영 `market-ai` 저장소에는 다른 Windows PC에서 실행 가능한 runtime 세트를 보관할 수 있습니다.

Git 추적 가능한 대표 runtime:

```text
MarketAI.exe
_internal/
InvestmentLocalSuite.exe
_suite_internal/
KisKospi200Bridge.exe
KisKospi200Bridge.exe.config
AxInterop.ITGExpertCtlLib.dll
Interop.ITGExpertCtlLib.dll
InvestmentLocalSuite.ico
tools/close-efriend-tray.ps1
README.md
.gitignore
db/.gitkeep
```

`_internal/`, `_suite_internal/`의 `*.pyd`는 PyInstaller runtime에 필요한 native extension이므로 제외하지 않습니다. mutable 운영 DB는 Git에 올리지 않습니다.

문서 역할:

```text
market-ai/README.md
→ 운영 Runtime 실행 / 상태 확인 / 배포 / 데이터 보존

market-ai-dev/market_ai_project_handover.md
→ architecture / build / deploy / runtime 장기 contract

market-ai-dev/market_ai_evaluation_guide.md
→ 평가 / 점수 / A·B·C / 반례 / 수정 종료 기준
```

새 작업에서는 최신 소스와 역할에 맞는 문서를 먼저 확인하고, 문서가 실제 소스와 다르면 **실제 최신 소스를 우선 확인한 뒤 문서를 동기화**합니다.
