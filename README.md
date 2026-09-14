# Market AI

> **문서 성격**: 이 README는 `market-ai` **운영 Runtime 저장소의 실행 · 상태 확인 · 장애 분리 · 데이터 보존 · 배포 파일 구성**을 설명합니다.  
> Python/C#/PyInstaller의 상세 빌드·정리 contract는 `market-ai-dev/market_ai_project_handover.md`에서 관리하고, 이 README에는 운영자가 필요한 재빌드 매핑만 간단히 적습니다.
>
> **운영 환경**: Windows + KIS eFriend Expert + x86 ActiveX Bridge를 사용하는 대상 PC입니다. 최종 runtime은 Python-free입니다. 로컬 Bridge/유지보수 API는 `127.0.0.1:8001`을 사용하고, 외부 Dashboard는 Tailscale Serve가 연결된 `127.0.0.1:8002` GET-only proxy를 통해 조회 결과만 소비합니다.

로컬 Windows PC에서 시장 데이터, eFriend 실시간 KOSPI·KOSPI200 선물·동적 KRX 보유종목, Signal Engine, Backtest, Calibration을 통합해 **AI Market Signal과 보유종목 실시간 현재가**를 투자 대시보드에 제공하는 프로젝트입니다.

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
→ Remote GET-only proxy 127.0.0.1:8002
→ Tailscale 상태 / Serve 자가복구 (optional, :8002만 공개)
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

이 full API bind는 runtime 코드에서 고정합니다. `.env`나 Windows 환경변수의 `MARKET_AI_HOST` / `MARKET_AI_PORT`로 LAN 또는 다른 포트에 재바인딩하지 않습니다. 원격 조회는 반드시 8002 GET-only 경계를 사용합니다.

Local Suite는 원격 Dashboard용으로 별도 GET-only proxy도 loopback에 엽니다.

```text
http://127.0.0.1:8002
```

8002는 원격 Dashboard가 실제 사용하는 조회 API만 allowlist로 노출하고 해당 경로의 `GET / HEAD / OPTIONS`만 8001로 전달합니다. `POST / PUT / PATCH / DELETE`는 405로 차단하고, allowlist 밖의 GET도 backend에 전달하지 않습니다. `/api/market-data/krx-quotes`는 원격 `client_id`를 `remote-<hash>` namespace로 바꿔 로컬 lease와 충돌하지 않게 하며 client당 요청 ticker는 최대 64개로 제한합니다. **proxy는 lease table을 따로 보관하지 않습니다.** 실제 원격 client 수·전체 ticker capacity admission은 8001 `KrxQuoteService`가 단일 lock에서 관리하고, 원격은 로컬 lease·Signal baseline과 첫 local request 전의 **local restart bootstrap 예약 용량**을 제외한 남은 capacity만 사용할 수 있습니다. 원격이 먼저 capacity를 차지했더라도 이후 로컬 Dashboard 요청이 필요하면 backend가 오래된 원격 lease부터 회수하여 로컬을 우선합니다. 첫 **admission 성공 local request**만 bootstrap을 authoritative하게 해제하며, capacity 초과 등으로 거절된 local request와 원격 요청은 bootstrap을 해제하거나 `dashboard_quote_universe.json` restart state에 기록할 수 없습니다. KIS Bridge의 tick/heartbeat와 로컬 유지보수 write API는 기존대로 8001에 직접 연결하고 Tailscale Serve에는 노출하지 않습니다.

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
- `KIS eFriend Market Bridge` 메뉴에서 숨겨진 Bridge 네이티브 모니터 창을 열 수 있습니다.
- Bridge 창의 `X`/`Alt+F4`는 실제 종료를 시작하지 않고 `SC_CLOSE` 단계에서 즉시 Hide합니다. 최소화도 화면 숨김으로 처리합니다.
- 숨긴 Bridge 창은 같은 프로세스를 유지하며 Local Suite 트레이 메뉴에서 다시 표시됩니다. 실제 Bridge 종료는 Local Suite 종료 명령이 담당합니다.
- `서버·Bridge 종료`는 eFriend를 유지합니다.
- `서버·Bridge·eFriend 종료`는 서버 → Bridge → eFriend 순서로 전체 종료합니다.
- eFriend 자동 로그인 정보는 Windows Credential Manager에 저장하며 트레이 메뉴에서 설정/삭제합니다.

### Web Monitor

Market AI backend는 브라우저용 **read-only 운영 모니터**도 함께 제공합니다.

```text
로컬
http://127.0.0.1:8001/monitor/

폰/외부 tailnet
https://node.tail60a98e.ts.net/monitor/
```

개발 Source of Truth의 Web Monitor는 과분리하지 않고 다음 3파일만 유지합니다. 빌드 시 `MarketAI.exe + _internal/`에 포함됩니다.

```text
market-ai-dev/monitor/
├─ index.html
├─ monitor.css
└─ monitor.js
```

- Web Monitor는 **10초 polling**으로 read-only `/api/bridge/kis-efriend/quote-universe`를 조회합니다.
- 조회 endpoint는 Dashboard용 `client_id` lease를 생성하거나 연장하지 않습니다.
- 화면은 process-memory realtime/latest 값을 우선하고, 장마감·재시작 복원에만 durable `MarketSnapshot`을 fallback으로 사용합니다.
- K200/KOSPI는 `상태 · 세션 · 시간 · 현재가 · 등락률`을 표시하며, 내부 `FC_R / CMEC_R / JUC_R / SC_R` 서비스 코드나 instrument code는 사용자 화면에 노출하지 않습니다.
- 보유종목은 `정상 / 시간외 / 장마감 / 대기 / 지연 / 오류`를 구분합니다.
- `business_time`은 실제 `HHMMSS` 범위만 유효하며 `888888` 같은 값은 실제 시각처럼 표시하지 않습니다. 유효값이 없으면 모니터는 `observed_at`의 KST 시각을 fallback으로 사용할 수 있습니다.
- Phone에서도 **K200/KOSPI 시장 카드와 보유종목 카드 모두 한 줄 2개(2열)**를 유지합니다. 760px 이하/420px 이하에서도 보유종목을 1열로 강제하지 않습니다.
- Web Monitor polling 10초, Dashboard polling 10초, client lease 120초, dynamic KRX DB snapshot write throttle 30초는 서로 다른 contract입니다.

---

## 1.2 `market-ai` 운영 폴더의 역할

`market-ai`는 **실행·배포 전용 runtime 저장소**입니다. 운영 PC에서 Python/C# 원본을 직접 수정하거나 이 폴더를 개발 Source of Truth로 사용하지 않습니다.

기본 runtime 구성:

```text
market-ai\
├─ _internal\
├─ _suite_internal\
├─ db\
│  ├─ .gitkeep
│  └─ market_signal.db        # 로컬 mutable DB, Git 제외
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

운영 PC에는 `market-ai-dev` 폴더가 없어도 실행할 수 있습니다.

### 운영 중 생성·변경될 수 있는 파일

`db/market_signal.db`는 Signal / Backtest / Calibration 누적 이력을 가진 **mutable 운영 데이터**입니다. GitHub runtime 배포 파일과 별개로 보존합니다.

`.env`는 기본 실행에 필수 파일이 아닙니다. OpenAI 뉴스 분석이나 명시적 운영 override가 필요한 경우에만 외부 mutable configuration으로 둘 수 있으며 Git/공유 ZIP에 넣지 않습니다.

Local Suite 실행 시 root에 다음 로그가 생성될 수 있습니다.

```text
start-local-server.log
```

이 로그는 현재 PC의 기동·Market AI·Bridge·Dashboard·Tailscale 상태를 확인하기 위한 로컬 runtime 로그이며 배포 필수 파일이 아닙니다. 필요하면 삭제할 수 있고 다음 실행에서 다시 생성됩니다.

## 1.3 Runtime 업데이트 / 교체 원칙

빌드와 서명은 `market-ai-dev`에서 수행하고, 운영 `market-ai`에는 **완성된 runtime 세트만** 반영합니다.

```text
Market AI backend
→ MarketAI.exe + _internal/

KIS eFriend Market Bridge
→ KisKospi200Bridge.exe
→ KisKospi200Bridge.exe.config
→ AxInterop.ITGExpertCtlLib.dll
→ Interop.ITGExpertCtlLib.dll

Investment Local Suite
→ InvestmentLocalSuite.exe + _suite_internal/
```

EXE와 support directory/DLL은 같은 빌드 세트로 교체합니다.

일반 빌드 배포에서 다음 운영 자원은 덮어쓰지 않습니다.

```text
db/market_signal.db
.env                         # 실제 사용하는 경우
README.md
.gitignore
InvestmentLocalSuite.ico
tools/close-efriend-tray.ps1
```

정적 지원 파일 자체가 수정된 경우에만 해당 파일을 별도로 반영합니다. 특히 dev의 `db/market_signal.db`를 운영 DB 위에 빌드 산출물처럼 복사하지 않습니다.

운영 README는 build command, PyInstaller 임시 폴더, dev cleanup 절차를 소유하지 않습니다. 재빌드 순서와 개발 산출물 정리는 `market-ai-dev/market_ai_project_handover.md`를 기준으로 합니다.

Dashboard HTML/CSS/JS만 수정한 경우 Market AI runtime EXE 재빌드는 필요하지 않습니다.

## 1.4 재빌드 매핑

개발 소스를 수정했다면 `market-ai-dev`에서 변경 대상에 맞는 빌드만 수행합니다.

```text
Market AI backend / Web Monitor
→ build-market-ai.ps1
→ MarketAI.exe + _internal/

KIS eFriend Market Bridge
→ build-kis-bridge-release.bat
→ KisKospi200Bridge.exe
→ KisKospi200Bridge.exe.config
→ AxInterop.ITGExpertCtlLib.dll
→ Interop.ITGExpertCtlLib.dll

Investment Local Suite / Tailscale GET-only proxy
→ build-investment-local-suite.ps1
→ InvestmentLocalSuite.exe + _suite_internal/
```

`MarketAI.exe`와 `_internal/`, `InvestmentLocalSuite.exe`와 `_suite_internal/`은 각각 같은 빌드 세트로 배포합니다. Dashboard HTML/CSS/JS만 바뀐 경우 위 EXE를 재빌드하지 않습니다.

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
http://127.0.0.1:8002
        ↓  GET-only proxy (허용 API의 GET / HEAD / OPTIONS)
http://127.0.0.1:8001
        ↓
MarketAI.exe
```

Tailscale Serve endpoint:

```text
https://node.tail60a98e.ts.net
```

Market AI API의 8001/8002 포트를 인터넷에 직접 포트포워딩하지 않습니다. FastAPI 전체 API는 `127.0.0.1:8001`에만 바인딩하고, Tailscale Serve는 Local Suite의 `127.0.0.1:8002` GET-only proxy만 tailnet 내부 HTTPS로 제공합니다. 따라서 원격 write method는 FastAPI에 도달하지 않습니다.

8002 원격 allowlist는 현재 **Dashboard 조회 API + Web Monitor read-only surface**로 제한합니다.

```text
/api/health
/api/signal/latest
/api/market-data/snapshot
/api/market-data/krx-quotes
/api/bridge/kis-efriend/status
/api/bridge/kis-efriend/quote-universe

/monitor/
/monitor/index.html
/monitor/monitor.css
/monitor/monitor.js
```

`/monitor` 요청은 `/monitor/`로 **308 canonical redirect**하여 상대 CSS/JS가 같은 tailnet origin에서 정상 로드되게 합니다. 이 목록 밖의 GET은 404로 proxy에서 종료합니다. `krx-quotes`는 proxy에서 client당 최대 64 ticker와 query/client 형식을 검사하고, 원격 client 16개 상한과 local/remote/Signal을 합친 실제 64-ticker capacity는 backend `KrxQuoteService`에서 원자적으로 관리합니다. `64`는 요청 형식상 최대치이며, 실제 허용 여부는 Signal baseline과 local/remote active lease의 **고유 ticker 합집합**이 64개 이내인지 backend가 판단합니다. 따라서 baseline 2개를 요청에 포함한 64-ticker Dashboard도 물리 universe가 64개라면 정상 허용될 수 있고, 반대로 64개가 모두 non-baseline이면 capacity 초과로 거절될 수 있습니다. capacity가 부족한 remote 요청은 422로 거절되고 기존 local lease를 밀어내지 않습니다. 반대로 local 요청은 필요하면 오래된 remote lease를 회수하므로 remote 선점 때문에 정상 local 요청이 거절되지 않습니다. 따라서 8002를 "모든 GET을 허용하는 read-only API"로 해석하지 않습니다.

외부에서 Market AI가 표시되려면:

1. Market AI가 설치된 Windows PC가 켜져 있어야 함
2. Investment Local Suite가 실행 중이어야 함
3. PC의 Tailscale이 연결되어 있어야 함
4. 외부에서 보는 폰/PC도 같은 tailnet에 연결되어 있어야 함

PC나 Tailscale이 꺼져 있어도 GitHub Pages 대시보드의 일반 기능은 계속 사용할 수 있고 Market AI 부분만 사용할 수 없습니다.

Local Suite는 startup에서 Tailscale service / tailnet 연결 / Serve 설정을 확인합니다.

- 정상 Serve가 이미 있으면 다시 쓰지 않습니다.
- Serve 설정이 없거나 `127.0.0.1:8002` GET-only proxy를 가리키지 않으면 `tailscale serve --bg 8002` 복구를 best-effort로 시도합니다.
- 8002 GET-only proxy 자체가 기동하지 못하면 원격 기능을 **fail-closed**로 두고 canonical Serve root를 `tailscale serve off`로 해제합니다. 과거 `Serve → 8001` 설정이 재사용되어 write API가 다시 원격 노출되는 것을 허용하지 않습니다.
- 정상 `Serve → 8002`가 보이더라도 다른 handler/path에 `Serve → 8001`이 동시에 남아 있으면 **unsafe mixed mapping**으로 판정해 Serve root를 내리고 8002만 다시 구성합니다.
- GET-only Serve 복구 자체가 실패하거나 복구 후 안전한 상태를 다시 확인할 수 없으면 `serve off`를 best-effort로 시도하고 remote를 정상으로 판정하지 않은 채 로컬 8001만 유지합니다.
- Tailscale service가 멈춰 있으면 Windows `Tailscale` service 시작을 시도할 수 있습니다.
- `NeedsLogin`, Tailscale 미설치, Serve/remote health 실패는 원격 기능 경고이며 로컬 Market AI 기동 실패로 처리하지 않습니다.

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
- CORS는 browser origin 허용 규칙일 뿐 write 접근제어 수단이 아닙니다. 원격 write 차단은 Local Suite의 8002 GET-only proxy가 담당합니다.

현재 원격 조회가 정상인지 확인할 때는 Tailscale 연결 상태에서 다음을 직접 확인할 수 있습니다.

```text
https://node.tail60a98e.ts.net/api/health
https://node.tail60a98e.ts.net/monitor/
```

원격 경계 QA에서는 위 GET이 정상이어야 하고, allowlist 밖 GET은 404, 잘못된 ticker/과도한 ticker 요청은 422, backend의 remote client 수 또는 남은 ticker capacity 초과도 422, Tailscale URL을 통한 POST/PUT/PATCH/DELETE는 8002 proxy에서 405로 차단되어야 합니다. 원격 `client_id`는 backend에서 `remote-<hash>` namespace로 관측되어야 합니다. 원격 62 ticker를 먼저 점유한 뒤 서로 다른 local ticker를 요청하는 반례에서도 local이 성공하고 remote lease가 회수되어야 합니다. 또한 재시작 직후 remote가 먼저 붙어도 local bootstrap은 유지되어야 하고, remote 요청만으로 `dashboard_quote_universe.json`이 바뀌면 안 됩니다. Bridge의 실제 POST는 localhost 8001 direct path를 계속 사용합니다.

---

# 3. 투자 대시보드 연동

Dashboard용 주요 조회 API:

```text
GET /api/health
GET /api/market-data/snapshot
GET /api/signal/latest?include_details=true
GET /api/bridge/kis-efriend/status

GET /api/bridge/kis-efriend/quote-universe
GET /api/market-data/krx-quotes?tickers=...&client_id=...
```

Market AI Dashboard 연동은 두 역할로 나뉩니다.

## 3.1 현재 시장 / AI Signal

시장 metric은 다음 네 가지를 사용합니다.

```text
KOSPI
KOSPI200 선물
SOX
NQ100 선물
```

KOSPI는 `INDEX:KOSPI` snapshot의 실제 `source`를 기준으로 툴팁에 `KIS eFriend KOSPI 실시간` 또는 Yahoo fallback을 표시합니다. provider 명칭을 Yahoo로 고정하지 않습니다.

SOX 화면 표시도 현재 `INDEX:SOX` 현물지수를 사용합니다. `FUTURES:SOX`는 현재 Dashboard Market AI 표시나 Signal weight의 대체값으로 사용하지 않습니다.

이 Signal panel은 선택한 과거 투자 기준일과 별개로 **현재 시점의 Market AI**를 표시합니다.

## 3.2 보유종목 실시간 현재가 / 평가 overlay

Dashboard의 현재 보유 ticker는 Dashboard가 소유하며 Market AI에 `client_id`와 함께 quote를 요청합니다. 현재 Dashboard의 Market AI signal 조회와 보유종목 live valuation 조회는 visible 상태에서 **10초 주기**를 사용하고 visible 복귀 시 즉시 갱신합니다. KIS realtime 수신 자체는 polling과 별개로 계속 실시간입니다.

- `005930`, `000660`은 Signal Engine 입력을 위해 물리 `SC_R` baseline stream으로 항상 유지할 수 있습니다.
- Market AI/Bridge 시작 직후에는 현재 Dashboard 보유 10종목을 startup warm-up 대상으로 선구독하고, 첫 Dashboard 요청부터는 실제 active client들의 보유 ticker 합집합이 authoritative universe가 됩니다. `client_id + []`도 정상적인 empty universe입니다.
- Signal baseline이 Dashboard 보유 universe에서 빠져도 물리 stream/history는 유지할 수 있지만 Dashboard valuation quote cache는 폐기합니다. 다시 보유종목에 편입되면 다른 종목과 동일하게 새 실제 `SC_R` tick 전까지 `WARMING`입니다.
- 숫자뿐 아니라 `0163Y0`처럼 영문이 포함된 6자리 KRX ticker도 문자열로 처리합니다.
- PC / 폰 / 복수 탭의 ticker set은 active client lease 기준 합집합으로 관리하며 현재 lease는 120초입니다. 원격 `remote-<hash>` client는 최대 16개이며 local/remote admission은 backend의 같은 lock에서 처리합니다. local request가 capacity를 필요로 하면 remote lease보다 우선합니다.
- Market AI 시작 시 보유종목 bootstrap은 Python/C#에 종목을 하드코딩하지 않고 형제 `investment-dashboard/data/portfolio.json`의 현재 `qty > 0` 보유종목과 **이름 + 종목 type**을 읽습니다. Dashboard 저장소를 일시적으로 읽을 수 없을 때만 `market-ai/db/dashboard_quote_universe.json`의 마지막 **local-only authoritative universe**를 fallback으로 사용하며 이 파일에도 ticker/name/type을 함께 보존합니다. bootstrap은 첫 admission 성공 local Dashboard request까지 로컬 예약 용량으로 유지되므로 원격/Tailscale quote GET이 먼저 와도 해제되지 않으며, 원격 요청은 이 runtime state를 쓰지 않습니다. 로컬 복수 탭의 동시 write는 현재 local union으로 직렬화됩니다. 이 runtime state는 Git 추적 대상이 아닙니다.
- `dashboard_quote_universe.json`은 재시작 warm-up용 보조 상태입니다. local lease admission이 성공한 뒤 이 파일 저장만 실패하더라도 이미 정상 처리된 quote API를 500으로 뒤집지 않으며, warning 후 in-memory 상태를 계속 사용하고 다음 local 요청에서 다시 저장을 시도합니다.
- 특정 ticker의 subscription 장애는 전체 quote 실패로 확대하지 않고 해당 ticker만 `stale/unusable`로 처리합니다.
- subscription이 복구돼도 새 실제 `SC_R` tick을 받기 전에는 장애 전 quote를 다시 usable로 부활시키지 않습니다.
- 저유동 종목은 마지막 tick이 오래됐다는 이유만으로 자동 stale 처리하지 않습니다.

Dashboard 적용 규칙:

```text
KST 오늘
→ usable=true quote를 화면 평가 계산에 overlay
   - 정규장(open): state=live
   - 개별주식 15:30~20:00 extended: state=live
   - 신뢰 가능한 당일 session 종료: state=closed

특정 ticker warming/stale/unavailable/error
→ 해당 ticker만 JSON 저장값 fallback

과거 activeDate
→ 오늘 realtime quote를 절대 overlay하지 않고 historical JSON 유지
```

live quote는 **화면용 메모리 overlay**입니다.

Market AI가 소유하는 것:

```text
ticker
현재가
source
observed_at
subscription health
quote state / usable
```

Dashboard가 계속 소유하는 것:

```text
수량
원가
투입원금
매매흐름
실현손익
평가금액/평가손익/수익률 계산
historical snapshot
```

live quote를 `prices.json`, `performance_snapshots.json`, Pension JSON이나 GAS에 저장하지 않습니다.

Dashboard Hero 제목행은 날짜 기준만 표시하며 `LIVE / CLOSED / STALE / WARMING / JSON` 상태 문자열은 노출하지 않습니다. quote/fallback 판정은 내부 state로 유지하고, 종목/상품 라벨 셀의 source tooltip에서 Market AI·JSON·당일 매수원가 등 개별 현재가 출처와 관측시각/기준일을 확인할 수 있습니다.

KRX Action modal, 퇴직연금 금액조정 modal, 차트 확대 등 전체 render가 사용자 작업을 방해할 수 있는 상태에서는 live state만 갱신하고 Dashboard 전체 rerender를 보류했다가 안전해진 뒤 pending render를 반영합니다.

Dashboard frontend의 상세 UI/responsive/lifecycle contract는 `investment-dashboard` 프로젝트의 `main_dashboard_maintenance_handover.md`가 Source of Truth입니다.

---

# 4. 현재 기능 상태

```text
시장 데이터 수집                         ✅
뉴스 수집                               ✅
OpenAI 뉴스 분석 코드                    ✅ 선택 기능
Signal Engine                           ✅ stage6_rule_v7
Backtest                                ✅
Calibration                             ✅
KIS eFriend Market Bridge               ✅
KOSPI JUC_R 실시간                       ✅
동적 보유종목 SC_R universe / quote       ✅
종목별 SC_R subscription health           ✅
국내 현물 Yahoo 장애 fallback             ✅
KOSPI200 주간 FC_R                       ✅
KOSPI200 야간 CMEC_R                     ✅
실제 KIS 선물 → Signal Engine            ✅
KOSPI200 근월물 AUTO rollover           ✅
KRX 휴장일/session 정책                 ✅
개별주식 15:30~20:00 시간외 상태          ✅
ETF·KOSPI 15:30 정규장 마감 유지          ✅
Dashboard endpoint 실패 격리             ✅
Dashboard 현재 보유종목 live valuation   ✅
Dashboard 로컬 Market AI 조회            ✅
Dashboard 원격 Tailscale 조회            ✅
Local Suite Tailscale Serve 자가복구      ✅
Remote GET-only proxy (:8002)           ✅
Tailscale Web Monitor `/monitor/`         ✅
GitHub Pages CORS 허용                   ✅
Python-free target runtime               ✅
External Python process 불필요           ✅
Local Suite 단일 트레이                  ✅
Bridge monitor Local Suite에서 열기       ✅
서버·Bridge / 전체 종료 분리              ✅
OpenAI 실제 API live QA                  ⏸ 선택 기능
```

---

# 5. 환경설정

기본 Market AI 실행에는 `.env`가 필요하지 않습니다.

OpenAI 뉴스 분석이나 명시적으로 허용된 기능 설정 override가 필요한 경우에만 `.env.example`을 참고하여 개발/운영 PC에 `.env`를 둘 수 있습니다. **네트워크 bind(`127.0.0.1:8001`)는 `.env` override 대상이 아닙니다.**

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

운영 저장소에서는 `db/market_signal.db`, `db/market_signal.db-wal`, `db/market_signal.db-shm`을 Git에서 제외합니다. `db/.gitkeep`만 추적하여 다른 PC에서 저장소를 내려받아도 SQLite parent directory가 유지되게 합니다.

다른 PC로 기존 누적 이력을 옮길 때는 Git이 아니라 별도 백업/복사로 `db/market_signal.db`를 이동합니다.

## 6.2 `.env`

`.env`가 존재하는 PC에서는 외부 mutable configuration으로 취급합니다.

- EXE에 포함하지 않음
- GitHub/공유 ZIP에 넣지 않음
- 기본 실행 필수로 가정하지 않음

---

# 7. KIS eFriend Market Bridge

Bridge는 KIS eFriend Expert의 실제 KOSPI200 선물, KOSPI 지수와 **동적 KRX 보유종목 SC_R**를 Market AI에 전달합니다.

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

고정 realtime service:

```text
KOSPI          JUC_R   / 0001
KOSPI200 주간  FC_R
KOSPI200 야간  CMEC_R
```

보유종목 quote service:

```text
KRX 현물/ETF      SC_R    / 6자리 ticker
Signal baseline   005930, 000660
startup warm-up   현재 Dashboard 보유 10종목
authoritative     Dashboard 활성 client들의 현재 보유 ticker 합집합
```

startup warm-up은 첫 Dashboard 요청 전의 준비 단계일 뿐 영구 baseline이 아닙니다. 첫 authoritative request 이후 실제 보유 universe에서 제거된 종목은 Dashboard valuation cache에서도 제거합니다. 삼성전자·SK하이닉스는 Signal Engine 입력 때문에 물리 stream을 계속 유지할 수 있지만 Dashboard valuation에서는 다른 종목과 같은 fresh-tick lifecycle을 따릅니다.

주요 Bridge / quote API:

```text
GET  /api/bridge/kis-efriend/quote-universe
GET  /api/market-data/krx-quotes?tickers=...&client_id=...

POST /api/bridge/kis-efriend/tick
POST /api/bridge/kis-efriend/market-tick
POST /api/bridge/kis-efriend/heartbeat
GET  /api/bridge/kis-efriend/status

GET  /api/bridge/kis-efriend/contract
GET  /api/bridge/kis-efriend/contract-code
GET  /api/bridge/kis-efriend/route
GET  /api/bridge/kis-efriend/route-code
```

heartbeat는 Bridge 전체 상태뿐 아니라 동적 `SC_R` ticker별 subscription health도 전달합니다.

대표 의미:

```text
subscribed
last_error
last_tick_at
tick_count
forward_success_count
```

Bridge 전체가 살아 있어도 특정 ticker stream만 장애면 그 ticker만 unusable로 처리합니다. 이후 `subscribed=true`로 복구됐더라도 새 실제 tick을 받을 때까지 장애 전 quote를 다시 live/closed로 사용하지 않습니다.

동적 보유종목은 Signal/Backtest history를 늘리지 않고 Bridge 모니터 재시작 복원을 위한 최신 `MarketSnapshot`만 최대 30초 단위로 저장합니다. eFriend realtime 입력의 거래소 `business_time`은 **실제 `HHMMSS` 범위(`00:00:00`~`23:59:59`)일 때만** 저장·표시합니다. `888888`처럼 6자리지만 유효하지 않은 값은 `null`로 정규화하고 DB에도 저장하지 않습니다. 재시작 후 모니터의 `시간`은 유효한 시장 시각을 우선 복원하고, 없으면 `observed_at` KST 시각을 fallback으로 사용할 수 있습니다. 이 durable snapshot은 모니터 표시용이며 Dashboard valuation의 process-memory quote로 자동 승격하지 않습니다. 장마감 후 재시작 시에는 가장 최근 완료 KRX 거래일 값만 `장마감`으로 복원합니다.

Bridge 네이티브 모니터는 `K200 · KOSPI · 보유종목 실시간 모니터링` 구조로 운영합니다. K200/KOSPI는 `상태 · 세션 · 시간 · 현재가 · 전일대비율`만 표시하고, Dashboard 보유종목은 `정상 / 시간외 / 장마감 / 대기 / 지연 / 오류` lifecycle 요약과 기본 5열 동적 카드로 표시합니다. 사용자 화면에는 `FC_R / CMEC_R / JUC_R / SC_R` 같은 내부 TR/service code나 instrument code를 표시하지 않고 `주간 / 야간 / 정규장 / 시간외 / 장마감`처럼 의미 있는 상태만 표시합니다. Signal baseline은 실제 Dashboard 보유종목이 아닐 때 카드 수에 포함하지 않습니다. 하단은 연결 상태와 마지막 수신 시각만 표시하며 내부 Tick/AI/debug 수치는 로그로 확인합니다.

Native UI의 시각 기준은 Web Monitor의 현대식 카드 UI입니다. 보유종목 요약 Header와 Holdings Card Grid는 별도 layout row를 사용하여 첫 카드 행을 덮지 않으며, rounded card/pill은 부모 배경을 먼저 합성한 뒤 surface를 그려 모서리 검은 쐐기/클리핑이 생기지 않도록 합니다.

Bridge 자체 트레이 아이콘은 사용하지 않습니다. `InvestmentLocalSuite.exe` 트레이의 `KIS eFriend Market Bridge` 메뉴로 창을 열고, `X`/`Alt+F4`는 `SC_CLOSE` 단계에서 즉시 Hide합니다. 최소화도 Hide이며 프로세스는 유지됩니다. 같은 트레이 메뉴가 private window message로 기존 프로세스의 창을 다시 표시하고, 실제 종료는 Local Suite의 `서버·Bridge 종료` 또는 `서버·Bridge·eFriend 종료`가 담당합니다.

## 7.1 국내 현물 provider / session 우선순위

Signal/collector의 Yahoo 장애 fallback과 Dashboard 보유종목 realtime session은 서로 다른 contract입니다.

```text
Signal/collector 기준 KRX 정규장(09:00~15:30)
eFriend 정상 → eFriend 우선
eFriend stale(기본 90초, `MARKET_AI_KIS_FALLBACK_AFTER_SECONDS` 초과) → Yahoo/yfinance 장애 fallback

정규장 종료 후
마지막 검증 eFriend snapshot 유지
→ 단순히 90초가 지났다는 이유로 Yahoo가 덮어쓰지 않음
```

Dashboard 보유종목 `SC_R` quote의 시장 상태는 portfolio의 종목 `type`을 사용해 별도로 판정합니다.

```text
개별주식
09:00~15:30  open / 정상
15:30~20:00  extended / 시간외
20:00 이후   closed / 장마감

ETF
09:00~15:30  open / 정상
15:30 이후   closed / 장마감

KOSPI 현물지수
15:30 정규장 마감 유지

K200 선물
기존 day / night / CLOSED route 유지
```

개별주식 `extended`에서도 새 `SC_R` tick이 수신되면 Dashboard quote는 `state=live`, `usable=true`로 계속 사용할 수 있습니다. ETF와 KOSPI의 15:30 정규장 마감, Signal Engine의 **15:30 KOSPI 종가 판정**은 20:00으로 연장하지 않습니다.

현재 화면과 API는 `SC_R` 수신 사실과 Market AI의 종목별 session 판정을 사용합니다. 특정 eFriend service가 NXT/ATS 체결을 어떤 방식으로 포함하는지까지 UI에서 추정하거나 별도 라벨로 단정하지 않습니다.


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
http://127.0.0.1:8002/api/health
http://localhost:8000/
```

원격 Tailscale 확인:

```text
https://node.tail60a98e.ts.net/api/health
https://node.tail60a98e.ts.net/monitor/
```

원격 경계 QA에서는 health와 `/monitor/`, `/api/bridge/kis-efriend/quote-universe` GET이 정상이어야 합니다. `/monitor`는 `/monitor/`로 308 정규화되고, allowlist 밖 GET은 404, 잘못된 ticker/과도한 ticker 요청은 422, backend의 remote client 수 또는 남은 ticker capacity 초과도 422여야 합니다. Tailscale URL을 통한 POST/PUT/PATCH/DELETE는 8002 proxy에서 405로 차단되어야 합니다. 원격 `client_id`는 backend에서 `remote-<hash>` namespace로 관측되어야 합니다. 원격 62 ticker를 먼저 점유한 뒤 서로 다른 local ticker를 요청하는 반례에서도 local이 성공하고 remote lease가 회수되어야 합니다. 또한 재시작 직후 remote가 먼저 붙어도 local bootstrap은 유지되어야 하고, remote 요청만으로 `dashboard_quote_universe.json`이 바뀌면 안 됩니다. Bridge의 실제 POST는 localhost 8001 direct path를 계속 사용합니다.

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

운영 `market-ai` 저장소는 **다른 Windows PC에서도 내려받아 실행 가능한 runtime 세트**를 보관하는 용도로 사용할 수 있습니다.

따라서 다음 runtime 파일은 GitHub에 포함할 수 있습니다.

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

`_internal/`과 `_suite_internal/` 안의 `*.pyd`는 Python cache가 아니라 PyInstaller onedir runtime에 필요한 **Windows native extension**이므로 Git 추적 대상입니다. Runtime `.gitignore`는 `*.pyc`, `*.pyo`만 제외하고 `*.pyd`를 제외하지 않아야 합니다. 새 clone 검증 시 `git ls-files "*.pyd"` 결과가 비어 있으면 배포가 불완전한 상태입니다.

반면 mutable 운영 DB는 Git에 올리지 않습니다.

```text
db/market_signal.db
db/market_signal.db-wal
db/market_signal.db-shm
```

따라서 새 PC에 GitHub 저장소만 내려받으면 runtime 프로그램 세트와 `db/` 폴더는 준비되지만 **기존 누적 Signal/Backtest/Calibration 이력은 포함되지 않습니다.**

기존 이력을 이어서 사용할 PC에는 `market_signal.db`를 별도 백업 경로로 복사합니다.

Market AI를 소비하는 투자 대시보드는 현재 GitHub Pages에서 제공되며, 해당 Pages Origin이 Market AI CORS 허용 대상입니다.

```text
Dashboard Origin
https://tkfkd3226-cell.github.io
```

Market AI runtime 저장소와 Dashboard 공개 호스팅은 서로 다른 역할입니다.

---

# 15. 인수인계

Market AI 개발 문서는 역할을 나눕니다.

```text
market-ai-dev\market_ai_project_handover.md
→ architecture / build / deploy / runtime 장기 contract

market-ai-dev\market_ai_evaluation_guide.md
→ 평가 / 점수 / A·B·C / 반례 / `수정해` 종료 기준
```

새 작업에서는 최신 개발 소스와 handover를 먼저 확인하고, 평가 요청이면 evaluation guide까지 함께 확인한 뒤 사용자의 현재 요청부터 진행합니다.
