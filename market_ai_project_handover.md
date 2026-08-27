# Market AI 프로젝트 인수인계

> 기준본: 이 문서와 함께 제공되는 최신 `market-ai` ZIP  
> 현재 기준: 필수 통합 QA가 완료된 운영 기준본  
> 문서 목적: 변경 이력이 아니라 **현재 유효한 Market AI 유지보수 계약**을 보존한다.

---

## 0. 새 채팅 시작 규칙

사용자가 최신 `market-ai` ZIP을 첨부한 뒤 `인수인계`라고만 입력하면 다음 순서로 처리한다.

1. 최신 ZIP 내부의 `market_ai_project_handover.md`와 `README.md`를 먼저 확인한다.
2. 실제 소스와 문서의 현재 기준을 확인한다.
3. 과거 작업을 다시 설명해 달라고 요구하지 않는다.
4. **QA를 자동으로 시작하지 않는다.**
5. 오래된 차수의 미완료 작업을 임의로 다시 제안하지 않는다.
6. 현재 필수 후속 작업이 없다면 짧게 인수인계 완료만 알리고 사용자의 새 요청을 기다린다.

권장 응답 예:

```text
인수인계 확인 완료.
현재 Market AI 운영 기준과 Signal/KIS Bridge 계약을 확인했습니다.
필수 후속 작업은 임의로 시작하지 않고 새 요청부터 진행하겠습니다.
```

---

# 1. 작업 및 문서 운영 원칙

## 1.1 작업 운영

- 항상 **현재 채팅에 첨부된 최신 ZIP**을 코드 기준본으로 사용한다.
- 최소 변경 원칙을 유지한다.
- 구현/수정과 QA를 구분한다.
  - 사용자가 `1차`, `2차` 등 구현 차수를 지정하면 해당 범위만 수행한다.
  - `QA` 요청 시 현재 수정본을 검증한다.
  - `수정` 요청 시 확인된 문제 범위만 수정한다.
- 사용자가 명시하지 않은 전체 QA, 리팩터링, 기능 확대를 자동으로 붙이지 않는다.
- 실제 선물과 proxy를 절대 혼동하지 않는다.
- 시장 데이터가 없으면 결측으로 두는 것이 잘못된 대체값을 실제값처럼 저장하는 것보다 낫다.
- 저장된 시장 데이터는 Signal / Backtest / Calibration의 후속 근거가 되므로 데이터 의미를 임의로 바꾸지 않는다.
- 투자 대시보드의 `dashboard-market-ai.js`, CSS, responsive UI 유지보수는 대시보드 프로젝트의 `main_dashboard_maintenance_handover.md`가 담당한다.
- GitHub는 현재 Market AI 실행의 필수 구성요소가 아니다. Git 연결 여부 때문에 소스 구조를 바꾸지 않는다.

## 1.2 handover 문서 수정 기준

**Market AI 파일을 수정했다는 이유만으로 이 문서를 자동으로 수정하지 않는다.**

코드·설정·UI 변경 후 먼저 handover 영향 여부를 판단하고, **장기 유지보수 contract가 실제로 변경된 경우에만** 이 문서를 수정한다.

다음은 handover 반영 대상이다.

- 아키텍처 또는 모듈 책임 경계 변경
- Signal 계산 의미, 입력 구성, phase 의미 변경
- provider / symbol / 실제값·proxy 의미 변경
- KIS Bridge API, session, rollover 등 장기 운영 contract 변경
- 데이터 저장·무결성·보존 정책 변경
- Backtest / Calibration의 의미 또는 호환성 contract 변경
- 향후 유지보수자가 잘못 바꿀 가능성이 높은 의도된 동작이나 제약 변경

다음은 원칙적으로 handover에 누적하지 않는다.

- 단발성 버그 수정 내역
- 특정 QA의 PASS 개수나 실행 로그
- 특정 시점의 가격, 거래량, tick count, instrument code 실증값
- 현재 소스를 보면 바로 확인 가능한 함수·endpoint 전체 목록
- 특정 차수에서 무엇을 수정했다는 작업 이력
- 단순 UI 배치·비율·px·freshness 숫자 같은 구현 세부값
- README에 이미 충분히 설명된 실행 절차

기존 규칙과 같은 목적의 내용이 이미 있으면 새 항목을 추가하지 않고 **기존 문장을 수정·통합·삭제**한다.

코드 변경으로 기존 handover 문장이 더 이상 유효하지 않으면 새 설명을 덧붙이는 대신 **기존 내용을 현재 상태로 교체**한다.

> **이 문서는 changelog가 아니라 현재 유효한 Market AI 유지보수 계약이다.**

---

# 2. 프로젝트 목표와 책임 경계

Market AI는 로컬 PC에서 동작하는 **AI Market Signal** 시스템이다.

주요 책임:

- 국내/미국 시장 데이터 수집
- 실제 KOSPI200 선물 수신
- 반도체 관련 시장 데이터 수집
- 환율 / 유가 / 미국채 금리 수집
- 뉴스 수집
- 선택적 OpenAI 뉴스 구조화 분석
- Rule-based Signal Engine
- Prediction Outcome / Backtest
- Probability Calibration
- 투자 대시보드가 조회할 Signal/시장 API 제공

자동 주문 시스템이 아니다.

**주문 API, 계좌번호, 계좌 비밀번호를 사용하지 않는다.**

대시보드는 Market AI의 소비자다. Market AI 백엔드는 대시보드 DOM/UI state를 알지 않으며, 대시보드 UI 규칙을 이 프로젝트에 역으로 끌어오지 않는다.

---

# 3. 현재 프로젝트 구조와 ownership

핵심 구조:

```text
market-ai/
├─ app.py                         # FastAPI entry / HTTP API
├─ config.py                      # 환경설정
├─ requirements.txt
├─ requirements-openai.txt
├─ .env.example
├─ README.md                      # 실행법·설정·API 사용법
├─ market_ai_project_handover.md # 장기 유지보수 contract
│
├─ ai/                            # OpenAI 뉴스 구조화 분석
├─ backtest/                      # forecast/outcome/evaluation
├─ bridges/                       # KIS eFriend / KOSPI200 contract
├─ calibration/                   # probability calibration
├─ collectors/                    # 시장 수집 orchestration
├─ db/                            # SQLAlchemy models/repository + 운영 DB
├─ market/                        # provider/catalog/market source
├─ news/                          # 뉴스 수집
├─ signals/                       # Rule Signal Engine
│
├─ KisKospi200Bridge/             # C# eFriend real-time bridge
├─ KisKospi200Bridge.sln
│
└─ eFriendQA/                     # eFriend 참고/QA 자료
```

소유권 원칙:

- `app.py`: 외부 HTTP contract와 service 조합
- `signals/`: 시장 입력을 Rule Signal로 변환하는 계산 책임
- `bridges/`: KIS eFriend 데이터와 KOSPI200 근월물/session 계약
- `market/`, `collectors/`: 일반 시장 provider와 snapshot/history 수집
- `backtest/`, `calibration/`: 사후 평가와 확률 보정
- `db/`: 저장 contract
- `KisKospi200Bridge/`: eFriend ActiveX real-time 수신 및 Market AI 전송
- `README.md`: 현재 실행법·환경변수·endpoint reference의 Source of Truth
- 이 문서: 왜 그렇게 설계됐는지와 깨면 안 되는 의미/경계의 Source of Truth

---

# 4. 전체 아키텍처

```text
투자 대시보드 (localhost:8000)
        │
        │ Market Snapshot / Signal / Bridge status 조회
        ▼
Market AI FastAPI (localhost:8001)
        │
        ├─ SQLite / SQLAlchemy
        ├─ 시장 데이터 collector
        ├─ 뉴스 / 선택적 OpenAI 분석
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

핵심 경계:

- 일반 시장 provider와 KIS futures Bridge는 별도 수집 경로다.
- `FUTURES:KOSPI200`은 **실제 KOSPI200 선물**만 canonical 값으로 저장한다.
- Yahoo 등의 KOSPI200 현물 proxy를 실제 선물로 승격하지 않는다.
- Signal Engine은 저장된 canonical snapshot의 의미를 신뢰하므로 upstream symbol 의미를 깨지 않는다.

---

# 5. 데이터 저장 및 무결성 contract

## 5.1 Snapshot과 History

시장 데이터는 최신 상태와 이력을 분리한다.

- 최신 snapshot은 현재 사용 가능한 최신 관측값을 나타낸다.
- history는 Signal/검증/분석용 시계열이다.
- 오래된 관측값이 더 최신 snapshot을 덮지 않도록 한다.
- provider의 관측 시각과 서버 수신 시각을 혼동하지 않는다.
- heartbeat가 살아 있다는 이유만으로 오래된 시장 가격을 fresh로 간주하지 않는다.

KIS Bridge 역시 heartbeat와 market-data freshness를 별개 의미로 유지한다.

## 5.2 실제 선물과 proxy

canonical symbol:

```text
FUTURES:KOSPI200
```

여기에는 실제 KIS eFriend futures tick만 저장하는 것을 원칙으로 한다.

Yahoo `^KS200` 등 현물지수는 개발용 proxy로 볼 수 있으나:

- 실제 futures로 표시하지 않는다.
- 실제 futures snapshot을 덮어쓰지 않는다.
- Signal Engine에서 실제 futures component로 사용하지 않는다.

실제값이 없으면 결측을 허용한다.

## 5.3 DB 호환성

기존 SignalRun / Backtest / Calibration 이력은 역사적 데이터다.

- 엔진 의미가 변경되면 engine version을 분리한다.
- 과거 엔진 기록을 현재 계산식으로 소급 재작성하지 않는다.
- Calibration은 해당 engine version과 target의 의미에 맞는 기록만 사용한다.
- DB schema/data migration이 필요한 경우 기존 누적 운영 데이터 보존을 최우선으로 한다.

---

# 6. 일반 시장 데이터와 SOX 의미

현재 주요 시장 symbol에는 국내/미국 주식, 지수, 선물, FX, 상품, 금리가 포함된다. 정확한 현재 catalog는 `market/catalog.py`, provider mapping은 `market/provider_map.py`를 Source of Truth로 한다.

## 6.1 SOX 현물과 SOX 선물

두 symbol의 의미를 구분한다.

```text
INDEX:SOX      = PHLX Semiconductor Index 현물지수
FUTURES:SOX    = SOX futures 시장 표시용 데이터
```

장기 불변조건:

- **Signal Engine의 SOX component는 `INDEX:SOX`만 사용한다.**
- `FUTURES:SOX`는 Signal weight에 포함하지 않는다.
- `FUTURES:SOX`는 대시보드 시장 metric 등 별도 표시 목적의 수집 데이터다.
- 현물/선물의 표시 전환 정책과 Signal 계산 정책을 섞지 않는다.
- provider의 실제 관측시각을 기준으로 stale 여부를 판단한다.
- stale한 마지막 값을 현재 가격처럼 가장하지 않는다.
- provider별 지연/유동성 특성에 따라 표시 freshness 정책을 조정할 수 있으며, 정확한 threshold는 해당 구현/config를 Source of Truth로 한다.

## 6.2 Nasdaq-100 선물

canonical symbol:

```text
FUTURES:NQ
```

provider symbol은 현재 Yahoo `NQ=F`를 사용한다.

Signal에서는 선행시장 component로 사용하며 SOX 현물과 역할을 혼동하지 않는다.

---

# 7. 현재 Signal Engine contract

현재 엔진 버전:

```text
stage6_rule_v7
```

엔진 버전은 계산 의미가 바뀔 때 과거 기록과 구분하는 호환성 경계다.

## 7.1 Rule Score 의미

주요 출력:

- `kospi_score`
- `semiconductor_score`
- `gap_up_probability`
- `up_close_probability`
- `confidence`
- `data_completeness`
- `calibrated`

중요:

- `calibrated=false`이면 네 핵심 signal 값은 **통계 확률이 아니라 0~100 Rule Score**다.
- `gap_up_probability`, `up_close_probability`라는 필드명은 기존 API/DB 호환성을 위해 유지된다.
- 비보정 상태에서는 별도의 legacy 압축을 적용하지 않고 direct weighted score 의미를 유지한다.
- 실제 Calibration이 적용된 target만 통계적 보정확률로 해석한다.

## 7.2 KOSPI 방향

현재 구성:

```text
KOSPI 현물       35%
KOSPI200 선물    65%
```

원칙:

- KOSPI 신호에는 KOSPI 현물과 KOSPI200 선물만 사용한다.
- 반도체·뉴스·금리·유가 같은 다른 의미의 입력을 섞지 않는다.
- 실제 KOSPI200 futures가 없으면 proxy를 대신 실제 futures로 사용하지 않는다.

## 7.3 반도체 방향

현재 구성:

```text
삼성전자          20%
SK하이닉스        20%
SOX 현물지수      20%
NVIDIA            15%
SK하이닉스 ADR    15%
Micron            10%
```

원칙:

- 직접 반도체 자산만 사용한다.
- SOX는 `INDEX:SOX`다.
- `FUTURES:SOX`를 반도체 Signal 입력으로 넣지 않는다.

## 7.4 갭상 Signal

장전/다음 거래일 예측 구성:

```text
KOSPI200 선물     50%
SOX 현물지수      25%
Nasdaq100 선물    20%
USD/KRW            5%
```

phase contract:

- KRX 현금장 **장전**에는 선행시장으로 당일 갭 방향을 예측한다.
- **장중**에는 09:00 직전 마지막 장전 checkpoint를 고정해서 사용한다.
- 장중 데이터로 개장 후 갭 signal을 다시 계산하지 않는다.
- 장전 checkpoint가 없으면 장중 갭 signal은 없는 값으로 처리할 수 있다.
- **장마감 후**에는 다음 KRX 거래일 갭 예측으로 전환한다.
- 주말/휴장일에는 다음 KRX 거래일을 대상으로 장전 예측 의미를 사용한다.

## 7.5 상승마감 Signal

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

phase contract:

- 장전에는 선행시장으로 당일 상승마감을 예측한다.
- 장중에는 KOSPI 현물 흐름을 포함해 계속 갱신한다.
- 15:30 이후 당일 KOSPI 종가 snapshot이 확인되면 예측값 대신 실제 상승/하락/보합 결과로 종료한다.
- 종가 snapshot이 아직 없으면 마지막 장중 checkpoint를 잠시 유지할 수 있으며 상태는 종가 확정 대기로 구분한다.
- 장전 학습 의미와 다른 장중/실제마감 `up_close`에 장전 Calibration 모델을 무조건 적용하지 않는다.

## 7.6 Freshness / Quality / Effective Weight

Signal component는 단순 configured weight만 사용하지 않는다.

- 각 시장 입력의 freshness와 quality가 실제 유효 가중치에 반영된다.
- 입력이 없거나 충분히 오래된 경우 component는 unavailable이 될 수 있다.
- `configured_weight`, `effective_weight`, `quality`의 의미를 구분한다.
- exact freshness threshold와 minimum data weight는 `signals/engine.py`의 현재 구현을 Source of Truth로 한다.
- consumer가 임의로 backend Signal 산식을 재구성해 다른 점수를 만들지 않는다.

## 7.7 Signal state metadata

Signal detail은 phase/mode/대상 거래일/checkpoint 같은 상태를 보존한다.

주요 의미:

- 현재 KRX session phase
- gap signal의 live/locked/next-session 의미
- up-close의 preopen/intraday/actual-close/post-close-pending 의미
- calibration 적용 가능 target
- component별 configured/effective weight와 quality

이 metadata는 단순 UI 설명용 문자열이 아니라 현재 signal 값의 **의미를 해석하기 위한 backend contract**다.

---

# 8. Backtest / Outcome contract

기존 `signal_runs`는 prediction ledger 역할을 유지한다.

Outcome/평가 데이터는 Signal 생성 시점 이후의 실제 결과를 사용한다.

핵심 원칙:

- 예측과 실제 결과를 시간 순서대로 분리한다.
- 평가 시 미래 정보를 prediction 생성에 역으로 섞지 않는다.
- 공식 forecast 선택 규칙은 코드의 현재 Backtest contract를 따른다.
- 동일한 signal target의 의미가 engine version에 따라 바뀌면 버전별 의미를 구분한다.
- 과거 SignalRun을 현재 엔진 의미로 소급 변환하지 않는다.

정확한 endpoint와 조회 옵션은 README/app.py를 Source of Truth로 한다.

---

# 9. Probability Calibration contract

현재 calibration 방식:

```text
quantile_beta_pava_v1
```

Calibration의 목적은 Rule Score 자체를 숨기거나 바꾸는 것이 아니라 충분한 평가 이력이 쌓였을 때 target별 통계적 확률 mapping을 별도로 제공하는 것이다.

장기 원칙:

- No-lookahead를 유지한다.
- KOSPI 상승 / 반도체 상승 / 갭상 / 상승마감 target을 독립적으로 취급한다.
- 충분한 데이터가 없는 경우 억지로 calibration을 적용하지 않는다.
- 같은 raw score는 같은 그룹과 같은 calibrated probability 의미를 유지한다.
- 단순 데이터 정렬 순서가 mapping 의미를 바꾸지 않도록 한다.
- engine version과 target 의미가 다르면 기존 calibration을 무조건 재사용하지 않는다.
- `calibration_eligible_targets`에 맞지 않는 phase에 모델을 적용하지 않는다.

정확한 최소 학습 조건과 모델 구현 상수는 calibration 소스를 Source of Truth로 한다.

---

# 10. KIS eFriend / C# Bridge 책임 경계

## 10.1 환경

현재 Bridge 환경:

```text
.NET Framework 4.8
x86
```

KIS eFriend Expert의 ActiveX/COM real-time 데이터를 C# Bridge가 수신하고 Market AI HTTP API로 전송한다.

주요 체결 서비스:

```text
주간   FC_R
야간   CMEC_R
```

Bridge는 tray resident process로 운영할 수 있으나, 현재 창 표시 방식·메뉴·UI 세부 구현은 C# 소스와 README를 Source of Truth로 한다.

통합 launcher는 투자 대시보드 프로젝트가 소유한다. Market AI에서 중요한 것은 **eFriend → Bridge → Market AI API**의 런타임 의존성이다.

## 10.2 Canonical futures symbol

Market AI 내부 canonical symbol:

```text
FUTURES:KOSPI200
```

source는 실제 route에 따라 KIS eFriend day/night 정보를 포함한다.

장기 원칙:

- actual futures tick만 canonical futures snapshot을 갱신한다.
- 일반 시장 collector가 actual KIS snapshot을 proxy로 덮지 않는다.
- 실제 instrument code는 AUTO route가 결정하며 특정 월물 코드를 handover 상수처럼 고정하지 않는다.

## 10.3 Server-side AUTO route

AUTO mode의 **단일 기준은 Market AI 서버**다.

Bridge가 로컬 시계만으로 session과 월물을 독자 판정하지 않는다.

주요 route contract:

- 서버가 현재 instrument code, service, session을 판정한다.
- Bridge는 route를 주기적으로 조회하고 그 결과에 따라 구독을 전환한다.
- 서버가 기대하는 route와 다른 tick/heartbeat는 거부한다.
- CLOSED 상태에서는 futures tick을 허용하지 않는다.
- fixed instrument code는 emergency override 용도이며 canonical 운영은 AUTO다.

핵심 route endpoint:

```text
GET  /api/bridge/kis-efriend/route-code
POST /api/bridge/kis-efriend/tick
POST /api/bridge/kis-efriend/heartbeat
```

정확한 전체 Bridge API 목록은 `app.py`와 README를 따른다.

## 10.4 Heartbeat와 오류 상태

- heartbeat는 Bridge 연결 상태 확인용이다.
- heartbeat 성공만으로 오래된 quote를 fresh하게 만들지 않는다.
- heartbeat 성공만으로 이전 tick 저장 오류를 지우지 않는다.
- 이후 정상 tick 처리 성공 시에만 관련 오류 상태를 정상화한다.
- status API는 connection과 마지막 수신 상태를 관측하기 위한 운영 정보다.

## 10.5 History sampling

KIS actual tick은 snapshot을 실시간으로 갱신하되 history DB 증가를 제한하기 위해 별도 sampling interval을 사용한다.

정확한 interval과 stale 설정은 `config.py` / `.env.example`을 Source of Truth로 한다.

---

# 11. KOSPI200 AUTO 근월물 / KRX session contract

근월물과 day/night/closed session 계산은 `bridges/kospi200_contract.py`가 canonical 책임을 가진다.

## 11.1 거래일 판정

- 가능한 범위에서는 `XKRX` 거래 캘린더를 우선한다.
- 캘린더 범위 밖은 정의된 한국 휴일/시장 휴장 fallback을 사용한다.
- 예측 불가능한 일회성 일정은 환경변수 override로 처리한다.
- override는 일반 자동 계산보다 명시적 운영 예외를 우선하기 위한 수단이다.

## 11.2 분기월 / 만기 rollover

- KOSPI200 선물은 분기월 기준 근월물을 계산한다.
- 명목상 두 번째 목요일이 휴장일이면 실제 최종거래일을 직전 거래일로 이동한다.
- 실제 최종거래일의 정규장 종료 특성을 반영해 다음 분기월로 rollover한다.
- 특정 월물 instrument code를 문서에 수동으로 계속 갱신하지 않는다.

## 11.3 Day / Night / Closed

장기 의미:

- 주간 KRX futures route는 `FC_R / day`
- 야간 futures route는 `CMEC_R / night`
- 휴장/장외 구간은 `CLOSED`
- 야간 session은 시작일과 다음 거래일 소속 규칙을 고려한다.
- 현재 route 계산과 contract code 계산은 같은 server-side 기준 시점을 사용한다.

정확한 시간 경계는 `bridges/kospi200_contract.py`를 Source of Truth로 한다. 시간 숫자를 handover에 중복 복제하지 않는다.

## 11.4 검증 기준

AUTO route 변경 시 최소 검증 대상:

- 일반 거래일 / 주말 / 휴장일
- day → closed → night 경계
- 실제 만기일 rollover 전후
- 수동 open/closed/night override
- `/contract`, `/route`, `/route-code`의 일관성
- 잘못된 tick/heartbeat route 거부
- CLOSED 상태에서 tick 거부

과거 QA의 개별 PASS 개수나 당시 월물 코드는 유지보수 contract가 아니므로 누적하지 않는다.

---

# 12. API 유지보수 원칙

Market AI API는 다음 책임군으로 나뉜다.

- health / market signal facade
- market data / collector
- KIS eFriend Bridge
- news
- AI news
- signal
- backtest / outcome
- calibration

정확한 현재 endpoint 전체 목록은 `app.py`와 `README.md`를 Source of Truth로 한다.

handover에는 다음과 같은 **의미적 contract가 바뀌는 경우에만** API 내용을 반영한다.

- canonical symbol 의미 변경
- request/response 필드의 장기 호환성 변경
- Signal field 의미 변경
- Bridge route/tick/heartbeat 검증 의미 변경
- Backtest/Calibration의 버전 호환 의미 변경

단순 endpoint 추가·이름 나열은 README에서 관리한다.

---

# 13. 뉴스 / OpenAI 기능

## 13.1 뉴스

뉴스 수집은 시장 Rule Signal과 독립된 기능이다.

현재 Rule Signal 4개에는 뉴스 score를 직접 섞지 않는다.

뉴스 source, topic, collector의 정확한 현재 목록은 소스/README를 따른다.

## 13.2 OpenAI 뉴스 구조화 분석

OpenAI 뉴스 분석 코드는 선택 기능이다.

기본적으로 실제 API 사용을 강제하지 않는다.

현재 구조화 결과에는 시장 관련성, sentiment, severity, confidence, time horizon, affected assets 등의 metadata가 포함될 수 있다.

SOX asset 의미는 Signal과 동일하게 현물 기준을 유지하며 `INDEX:SOX`와 `FUTURES:SOX`를 혼동하지 않는다.

실제 API Key는 로컬 `.env`에서만 관리한다.

OpenAI live API QA가 필요할 때만 명시적으로 수행한다.

---

# 14. Dashboard 연동 경계

Market AI backend는 대시보드에 다음 종류의 데이터를 제공한다.

- Market Snapshot
- Signal latest/details
- KIS Bridge status

Market AI가 보장해야 하는 것은 **API 데이터의 의미와 실패 격리 가능한 독립 endpoint contract**다.

대시보드의 다음 사항은 이 문서에서 관리하지 않는다.

- Hero layout
- Market/AI 카드 비율
- 모바일 dialog
- CSS selector/token
- SOX/SOX-F 실제 표시 위치
- responsive breakpoint

이러한 frontend 유지보수 규칙은 `main_dashboard_maintenance_handover.md`가 Source of Truth다.

다만 backend 의미로 다음은 유지한다.

- Signal과 market snapshot은 서로 다른 데이터다.
- Signal 오류가 정상 market snapshot 자체의 의미를 바꾸지 않는다.
- SOX 현물과 SOX 선물의 backend symbol 의미는 분리된다.
- Signal detail의 phase/effective weight/quality는 backend가 계산한 값을 기준으로 한다.

---

# 15. 파일 / 데이터 보존 규칙

## 15.1 반드시 보존

```text
db/market_signal.db
```

누적 운영 데이터가 들어 있으므로 임의 삭제·초기화·샘플 DB로 교체하지 않는다.

패치 파일을 만들 때도 최신 운영 DB를 불필요하게 포함하거나 덮어쓰지 않는다.

## 15.2 비밀값

로컬 PC의:

```text
.env
```

는 유지하되 ZIP/GitHub에 넣지 않는다.

API Key, 인증정보, 비밀값을 source code나 handover에 기록하지 않는다.

## 15.3 eFriend 참고자료

현재 `eFriendQA/`에는 eFriend API 참고자료가 보관될 수 있다.

실행 필수 파일은 아니며 향후 eFriend API 검증 시 참고한다.

## 15.4 GitHub

현재 프로젝트 실행은 `.git/` 존재 여부에 의존하지 않는다.

GitHub 연결 여부 때문에 Market AI runtime 구조나 데이터 저장 정책을 바꾸지 않는다.

---

# 16. 현재 운영 상태

현재 기준의 큰 기능 상태:

```text
FastAPI / SQLite                 ✅
일반 시장 데이터 수집            ✅
뉴스 수집                        ✅
Signal Engine                    ✅ stage6_rule_v7
Backtest / Outcome               ✅
Probability Calibration          ✅
KIS eFriend 실제 futures Bridge  ✅
AUTO 근월물 / KRX session route  ✅
주간 FC_R / 야간 CMEC_R 경로     ✅ 실증 완료
투자 대시보드 연동               ✅
OpenAI live API                  ⏸ 선택 기능
GitHub 연동                      ⏸ 현재 실행 비필수
```

과거 차수별 QA 숫자와 당시 실측값은 현재 운영 contract가 아니므로 이 문서에 유지하지 않는다.

---

# 17. 유지보수 시 필수 검증 범위

모든 작업에서 모든 QA를 반복하지 않는다. **변경한 책임 범위에 해당하는 검증만 선택해서 수행한다.**

## Signal 계산 변경 시

- engine version 분리 필요 여부
- configured/effective weight 합리성
- freshness/quality 적용
- Rule Score vs calibrated probability 의미
- gap/up-close phase 및 checkpoint 의미
- Calibration eligibility
- 기존 DB 이력 비소급 원칙

## 시장 provider / symbol 변경 시

- canonical symbol 의미
- 실제값 vs proxy 구분
- provider observed time
- snapshot 최신성 보호
- Signal component 연결 여부
- SOX 현물/선물 분리

## KIS Bridge / AUTO route 변경 시

- actual futures snapshot 보호
- instrument/session server-side 단일 판정
- day/night/closed route
- 만기 rollover
- 휴장일/override
- 잘못된 tick/heartbeat 거부
- heartbeat와 quote freshness 분리
- history sampling 회귀

## DB / Backtest / Calibration 변경 시

- 기존 `market_signal.db` 보존
- migration 안전성
- No-lookahead
- engine version / target 호환성
- 과거 기록 소급 변경 여부

## API 변경 시

- 기존 consumer 호환성
- 필드 의미 유지 여부
- 오류 상태가 다른 endpoint의 정상 데이터를 오염시키지 않는지
- README 업데이트 필요 여부

## 문서 변경 여부

작업 마지막에 항상 이 질문을 먼저 한다.

> **이번 변경이 향후 유지보수자가 반드시 알아야 할 장기 contract를 바꿨는가?**

아니라면 `market_ai_project_handover.md`를 수정하지 않는다.

---

# 18. 한 문장 원칙

> **Market AI는 실제 시장 데이터의 의미와 시간 순서를 지키고, Signal·Bridge·Backtest·Calibration의 책임을 분리하며, handover에는 현재 유효한 장기 contract만 남긴다.**
