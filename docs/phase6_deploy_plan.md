# Phase 6: Render 배포 계획 (착수 전, 확인 필요)

목표: GitHub 저장소 연결 → Render가 `Dockerfile` 기반으로 자동 빌드/배포. **이 문서는 계획이며, 아직 실제 배포는 진행하지 않았습니다.**

## ⚠️ 가장 중요한 결정: `/predict`(사전계산 조회)를 공개 배포에 포함할지

로컬/컨테이너 테스트 때는 문제없었지만, **인터넷에 공개되는 서비스로 올리는 순간 상황이 달라집니다.**

- `/predict`는 `SK_ID_CURR`만 입력하면 `train/test_features_leanA.parquet`에서 **실제 고객의 원본에 가까운 feature 값**(소득, 대출액, 생년월일 기반 나이 등)을 조회해 `top_factors.feature_value`로 그대로 응답에 실어 보냅니다.
- Phase 1에서 확인한 Kaggle 대회 규정: *"you may access and use the Competition Data only for the purposes of the Competition"*, *"No private sharing outside teams"*. PROJECT_GUIDELINES.md §4는 "원본 데이터는 비공개, 코드/집계결과만 공개"로 정했는데, **`/predict`를 공개 배포하면 사실상 SK_ID_CURR을 아는 누구나 개별 고객의 데이터를 조회할 수 있는 통로가 생겨** 이 원칙과 정면으로 부딪힙니다. `train_features_leanA.parquet`은 "집계결과"라기보다 고객 단위 원본에 파생 feature를 얹은 것에 가까워서, §4의 "집계결과는 공개 가능" 예외로 보기 어렵다고 판단했습니다.

### 후보

| 후보 | 방식 | 장단점 |
|---|---|---|
| **A. `/predict` 제외, `/predict/live`만 공개 배포 (제안)** | 공개 Render 배포에는 `/health`, `/model/info`, `/predict/live`만 포함. `/predict`는 로컬/사설 환경에서만 사용 | 데이터 노출 위험 없음. `/predict/live`는 입력을 전부 사용자가 주는 방식이라 그 자체로 라이선스 문제 없음. 오히려 포트폴리오 데모로는 "실시간 심사"가 더 인상적 |
| B. `/predict`도 배포하되 인증/접근제한 추가 | API 키나 IP 제한 등으로 `/predict` 보호 | 구현 복잡도 증가, 그래도 "누구나" 접근 가능한 상태보다 나을 뿐 여전히 라이선스 조항의 "competition 목적 외 사용" 자체는 해소 안 됨 |
| C. 그대로 전부 공개 | 별도 조치 없음 | 비추천 — 라이선스 리스크 가장 큼 |

**제안: A** — `/predict/live`만 공개 배포. 이렇게 하면 아래 "데이터 접근 문제"도 대부분 같이 해결됩니다.

## 배포 환경에 데이터를 어떻게 포함시킬지

로컬에서는 `-v $(pwd)/data:/app/data:ro`로 볼륨 마운트했는데, Render 같은 관리형 클라우드는 호스트 디스크를 마운트하는 방식 자체가 없습니다. 실제로 필요한 게 무엇인지 다시 보면:

- `/predict` (사전계산 조회): `data/processed/{train,test}_features_leanA.parquet` **데이터 내용 자체**가 필요 (37MB) → 위에서 A안으로 결정하면 **아예 필요 없어짐**
- `/predict/live`: `app/feature_live.py`가 `data/raw/*.csv`를 참조하긴 하지만, 코드를 확인해보니 **`DESCRIBE ... read_csv_auto(...)`로 컬럼명/타입만 조회**할 뿐 실제 행 데이터는 전혀 읽지 않습니다. 즉 진짜 필요한 건 "6개 원본 CSV의 스키마(컬럼명+타입) 정보"뿐, 2.5GB 원본 데이터 자체가 아닙니다.
- `models/lean_a_lightgbm_v1.joblib`(710KB) + schema.json: 이미 git에 커밋돼 있어서 Dockerfile의 `COPY models/`로 자동 해결됨 — 추가 조치 불필요

**제안**: 6개 CSV(`application_test`, `bureau`, `bureau_balance`, `credit_card_balance`, `POS_CASH_balance`, `installments_payments`, `previous_application`)의 스키마만 한 번 추출해 `models/csv_schemas.json` 같은 작은 파일(컬럼명+타입만, 실데이터 0건)로 커밋하고, `feature_live.py`가 매번 raw CSV를 스캔하는 대신 이 파일을 읽도록 수정. 이러면:
1. 배포 환경에 `data/` 자체가 전혀 필요 없어짐 (데이터 접근 문제 자동 해결)
2. 개인정보/라이선스 우려도 없음 (컬럼명·타입 메타데이터일 뿐 실데이터 아님)
3. 컨테이너 시작이 더 빨라짐 (CSV 스캔 불필요)

(A안 승인 시 반영할 코드 변경 — 아직 적용 안 함)

## 환경변수

| 변수 | 필요 이유 | 값 |
|---|---|---|
| `PORT` | Render는 서비스가 Render가 지정하는 포트에서 리슨하기를 기대함(기본 10000, 서비스마다 다를 수 있음) | Render가 자동 주입 — Dockerfile CMD를 `${PORT:-8000}`을 읽도록 고쳐야 함(현재는 8000 하드코딩, exec-form CMD라 셸 변수 치환이 안 됨 → shell-form으로 수정 필요) |

그 외 API 키/시크릿은 현재 인증 기능이 없어서 불필요.

## 무료 티어 리소스 관련 참고

- Render 무료 플랜은 보통 512MB RAM, 일정 시간 미사용 시 sleep(cold start 지연 발생) — LightGBM+SHAP(scikit-learn/scipy/numba 포함) 로딩 자체는 가벼운 편(로컬 이미지 238MB)이라 크게 문제될 것 같지 않지만, 첫 요청 시 cold start로 몇 초~수십 초 지연은 감안 필요
- 이 프로젝트 규모(모델 710KB, 스키마 메타데이터만 사용)면 무료 티어로 충분해 보임

## render.yaml (초안)

```yaml
services:
  - type: web
    name: home-credit-api
    runtime: docker
    dockerfilePath: ./Dockerfile
    dockerContext: .
    plan: free
    healthCheckPath: /health
    envVars:
      - key: PORT
        value: 8000
```

## 사용자가 직접 해야 하는 부분

Render 대시보드에서 GitHub 계정/저장소 연결은 Render 계정 권한이 필요해 제가 대신 할 수 없습니다 — render.yaml이 저장소 루트에 있으면 Render의 "New Blueprint Instance"로 저장소만 연결하면 나머지는 자동으로 인식됩니다.

## 확인 요청

1. **`/predict`를 공개 배포에서 제외(A안)하는 것에 동의하시나요?**
2. 위 두 코드 변경(CSV 스키마 사전추출 파일화, Dockerfile PORT 대응)을 지금 반영해도 될까요?

승인해주시면 코드 변경 + render.yaml 커밋까지 진행하고, 실제 Render 대시보드 연결은 사용자분이 진행하시면 됩니다.
