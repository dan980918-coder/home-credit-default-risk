# Phase 5: Docker 패키징

## Docker 런타임 준비

이 머신에 Docker가 설치돼 있지 않아서, GUI 없이 CLI만으로 동작하는 **Colima**(Lima VM 기반 경량 컨테이너 런타임)를 `brew install colima docker`로 설치하고 `colima start`로 띄웠음. Docker Desktop과 달리 GUI 상호작용이 필요 없어 이 환경에 적합.

## 설계 결정: 서빙 전용 requirements 분리

`requirements.txt`(전체 연구/개발용: scikit-learn, xgboost, matplotlib, scipy 포함)를 그대로 이미지에 넣으면 서빙에 안 쓰는 라이브러리까지 다 들어가 이미지가 불필요하게 커짐. `requirements-serving.txt`를 새로 만들어 실제 `app/*.py`가 import하는 것만 추림: `duckdb, pandas, numpy, lightgbm, shap, fastapi, uvicorn, pydantic, joblib`.

(참고: shap 자체가 scikit-learn/scipy/numba를 의존성으로 끌어오기 때문에 이들은 명시 안 해도 자동 설치됨 — 완전히 제거할 수는 없지만 xgboost/matplotlib은 확실히 뺐음)

## 설계 결정: 원본 데이터는 이미지에 굽지 않고 볼륨 마운트

`data/`(원본 CSV, 전처리 parquet)는 Dockerfile에서 COPY하지 않고 컨테이너 실행 시 `-v $(pwd)/data:/app/data:ro`로 마운트. 이유:
1. PROJECT_GUIDELINES.md §4(원본 데이터 비공개 원칙)와 일관성 — 이미지 자체에 데이터를 굽지 않으면 이미지를 어디에 올리더라도 데이터가 같이 퍼질 위험이 없음
2. 이미지 크기 절감에도 도움

## 빌드 결과

```
docker build -t home-credit-api:latest .
```

빌드 성공. `docker images` 출력의 "DISK USAGE"(1.11GB)는 베이스 이미지 등 다른 이미지와 공유되는 캐시 레이어까지 포함된 수치라 오해하기 쉬워서, `docker save`로 실제 내보내지는 이미지 크기를 직접 측정:

| 항목 | 크기 |
|---|---|
| **최종 이미지 실제 크기** (`docker save` 기준) | **238MB** |
| 베이스 이미지(`python:3.13-slim`) | 41.3MB |
| 애플리케이션 + 의존성(FastAPI/LightGBM/SHAP 등) | ~197MB |

**목표(너무 크지 않게) 달성** — LightGBM/SHAP처럼 무거워질 수 있는 라이브러리가 들어갔는데도 slim 베이스 + 서빙 전용 requirements 분리 덕분에 238MB로 가벼운 편.

## 컨테이너 실행 및 엔드포인트 재검증

```bash
docker run -d --name home-credit-api-test -p 8001:8000 \
  -v "$(pwd)/data:/app/data:ro" home-credit-api:latest
```

| 테스트 | 결과 | 비고 |
|---|---|---|
| `GET /health` | 200 | |
| `GET /model/info` | 200 | 로컬 uvicorn과 동일한 응답 |
| `POST /predict` (SK_ID_CURR=100001) | 200, `probability=0.2078` | **로컬 uvicorn 테스트와 완전히 동일한 수치** |
| `POST /predict` (존재하지 않는 ID) | 404 | |
| `POST /predict/live` (이력 있음) | 200, `probability=0.1394` | **로컬과 완전히 동일** |
| `POST /predict/live` (이력 없음) | 200, `probability=0.1141`, `has_bureau_record=false` | **로컬과 완전히 동일** |
| `POST /predict/live` (필드 누락) | 422 | |
| `/docs`, `/openapi.json` | 200 | |

로컬 uvicorn 실행과 컨테이너 실행의 예측 결과가 **소수점까지 완전히 일치** — 컨테이너화가 애플리케이션 동작을 바꾸지 않았음을 확인. 테스트 후 컨테이너 정리(`docker stop && docker rm`) 완료.
