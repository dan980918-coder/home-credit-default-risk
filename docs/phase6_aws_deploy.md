# Phase 6: AWS EC2 프리티어 배포 계획 (착수 전, 확인 필요)

Render 대신 AWS EC2 프리티어로 직접 배포하기로 결정. `/predict`(사전계산 조회) 제외 원칙은 배포처와 무관하게 그대로 적용.

## 1. AWS CLI / 자격증명 상태

```
$ aws --version
aws-cli/2.36.29 Python/3.14.7 Darwin/24.6.0 source/arm64   (설치 전엔 없었음 — brew install awscli로 설치함)

$ aws configure list
profile    : <not set>
access_key : <not set>
secret_key : <not set>
region     : <not set>
```

**자격증명 미설정 상태.** 아래 "필요한 것" 항목을 콘솔에서 발급받아 `aws configure`로 등록하면 CLI 사용 가능.

### 콘솔에서 받아야 할 것

| 항목 | 어디서 | 용도 |
|---|---|---|
| **IAM 사용자 Access Key ID + Secret Access Key** | IAM → 사용자 → 보안 자격 증명 → 액세스 키 생성 (**root 계정 키는 사용하지 말 것** — EC2 권한만 있는 IAM 사용자를 새로 만들어 발급받는 걸 권장) | `aws configure`로 CLI 인증, EC2 인스턴스 생성/관리를 CLI로 자동화하려는 경우 |
| **EC2 키 페어(.pem)** | EC2 콘솔 → 키 페어 → 새 키 페어 생성(형식: .pem, RSA) | 인스턴스에 SSH 접속할 때 필요. 다운로드한 .pem은 `chmod 400`으로 권한 제한 필요 |

CLI 자동화 없이 콘솔에서 직접 인스턴스를 만드실 거면 Access Key는 없어도 되고, SSH 접속용 키 페어만 있으면 됩니다.

## 2. EC2 프리티어 인스턴스 생성 계획

| 항목 | 값 | 근거 |
|---|---|---|
| 인스턴스 타입 | **t2.micro** (아래 §4 참고 — t3.micro 대비 메모리 차이 없음) | AWS 프리티어(12개월) 대상 |
| AMI | Ubuntu 24.04 LTS (또는 22.04 LTS), 64비트 (Arm 또는 x86, 아래 참고) | Docker 설치가 쉽고 커뮤니티 자료 많음 |
| 스토리지 | 8~10GB gp3 (프리티어 30GB까지 무료) | 우리 이미지(238MB) + OS + 여유분 감안하면 충분 |
| 보안 그룹(인바운드) | SSH(22) — 내 IP만 / HTTP API 포트(8000 또는 80) — 0.0.0.0/0(공개 데모 목적) | 22번은 전체 공개하지 않는 게 안전 |
| 키 페어 | 위 §1에서 발급받은 .pem | SSH 접속용 |

**아키텍처 주의**: 이 Mac은 Apple Silicon(arm64)이라 로컬에서 빌드한 이미지는 arm64용입니다. EC2도 **Arm 기반 t2.micro/t3.micro는 없고(t2/t3 시리즈는 x86_64 전용)**, Arm 인스턴스를 쓰려면 t4g.micro(Graviton, 이것도 프리티어 대상)를 선택해야 합니다. 즉:
- **t2.micro/t3.micro(x86_64)를 쓸 거면 EC2에서 이미지를 다시 빌드**해야 함(크로스 빌드 or 인스턴스에서 직접 `docker build`)
- **t4g.micro(Arm)를 쓰면 로컬(Apple Silicon)과 아키텍처가 같아** 이미지를 그대로 옮겨도 됨 — 다만 사용자가 지정한 후보는 t2.micro/t3.micro이므로 이 문서는 그 전제로 진행하고, EC2 인스턴스 안에서 `docker build`로 새로 빌드하는 방식을 기본으로 제안(§3)

## 3. Docker 설치 + 이미지 배포 방법

### 3.1 Docker 설치 (Ubuntu EC2 인스턴스 안에서, SSH 접속 후)

```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker $USER   # 재로그인 후 sudo 없이 docker 명령 가능
```

(Colima는 로컬 macOS에 Docker Desktop 없이 컨테이너를 돌리기 위한 것이었고, EC2는 Linux라 처음부터 진짜 Docker를 바로 설치하면 됨 — Colima 불필요)

### 3.2 이미지를 인스턴스에 올리는 방법 — **A안(인스턴스에서 직접 빌드)으로 확정**

| 후보 | 방법 | 장단점 |
|---|---|---|
| **A. 인스턴스에서 직접 빌드 (확정)** | `git clone` 저장소 → `docker build` | 레지스트리 계정/인증 불필요, 가장 단순. 아키텍처 이슈도 자동 해결(인스턴스의 실제 아키텍처로 빌드됨). §5에서 `data/` 의존성을 제거해뒀기 때문에 **git clone만으로 완결** — 원본 데이터를 별도로 옮길 필요가 전혀 없음 |
| B. Docker Hub/ECR에 push 후 pull | 로컬에서 빌드 → 레지스트리 push → 인스턴스에서 pull | 레지스트리 계정 필요, 아키텍처 불일치 시 `--platform` 멀티아치 빌드 필요해 더 복잡 — A안이 더 간단해서 채택 안 함 |

**실행 명령 (SSH 접속 후, EC2 인스턴스 안에서)**:

```bash
git clone https://github.com/dan980918-coder/home-credit-default-risk.git
cd home-credit-default-risk
docker build -t home-credit-api:latest .

# 공개 배포이므로 PUBLIC_DEPLOYMENT=true 필수 (/predict 비활성화)
# data/ 볼륨 마운트는 불필요 (모델은 이미지에 포함, /predict/live는 스키마 JSON만 사용)
docker run -d --name home-credit-api \
  -p 80:8000 \
  -e PUBLIC_DEPLOYMENT=true \
  --restart unless-stopped \
  home-credit-api:latest

# 확인
curl http://localhost/health
curl http://localhost/model/info   # predict_lookup_enabled: false 여야 정상
```

## 4. 메모리 검토: t2.micro(1GiB)에서 버틸 수 있는가 — **실측 완료**

**먼저 바로잡을 점**: t2.micro와 t3.micro는 **RAM이 둘 다 1GiB로 동일**합니다(vCPU 개수와 버스트 성능 방식만 다름 — t2는 CPU 크레딧 방식, t3는 "Unlimited" 기본 지원으로 더 유연함). "t3.micro가 RAM이 더 넉넉하다"는 전제는 사실이 아니라서, RAM 부족 시 t3.micro로 바꿔도 해결되지 않습니다. 프리티어 micro 인스턴스는 사실상 전부 1GiB가 한도입니다.

**실측**: 로컬에서 실제 이미지(`home-credit-api:latest`, 238MB)를 `docker run --memory=1g --memory-swap=1g`로 1GiB cgroup 제한을 걸어 EC2 t2.micro 조건을 근사해 테스트:

| 시점 | 메모리 사용량 |
|---|---|
| 컨테이너 시작 직후(idle) | **154MiB** / 1GiB (15%) |
| `/predict/live` 5회 연속 호출 후(SHAP 계산 포함) | **177.6MiB** / 1GiB (17%) |
| `/predict` 조회(parquet 스캔) 후 | **178.4MiB** / 1GiB (17%) |

**결론: t2.micro(1GiB)로 충분합니다.** LightGBM+SHAP(scikit-learn/scipy/numba 전이 의존성 포함)이 들어간 이미지인데도 실제 사용량은 180MB 안팎으로, 1GiB 중 800MB+ 여유가 남습니다. 다만 이 수치는 **컨테이너 프로세스만의 사용량**이라, 실제 EC2에서는 여기에 Ubuntu OS 자체(대략 100~200MB) + Docker 데몬(수십MB)이 추가로 올라간다는 점은 감안해야 합니다 — 그래도 합산해도 1GiB 안에 넉넉히 들어올 것으로 보입니다.

→ **t2.micro로 진행해도 무방**, t3.micro로 바꿀 이유는 메모리 때문이 아니라면 딱히 없음(원한다면 vCPU 여유·버스트 정책 차이로 t3.micro를 선택할 수는 있음).

## 5. 반영 완료 (2026-08-23)

- **`/predict` 공개 제외**: `app/main.py`에 `PUBLIC_DEPLOYMENT` 환경변수 추가. `true`면 `/predict`가 403(명확한 사유 메시지 포함)을 반환하고, `/predict/live`·`/health`·`/model/info`는 그대로 동작. `/model/info` 응답에 `predict_lookup_enabled` 필드로 현재 상태 노출.
- **`/predict/live`의 데이터 의존성 제거**: `scripts/extract_csv_schemas.py`로 7개 원본 CSV의 컬럼명·타입만(실데이터 0건) `models/csv_schemas.json`(12KB)에 미리 추출해 git에 커밋. `app/feature_live.py`가 더는 `data/raw/*.csv`를 스캔하지 않음.
- **로컬 검증**: `data/` 디렉터리를 통째로 이름 바꿔 없앤 상태 + `PUBLIC_DEPLOYMENT=true`로 실제 배포 환경을 그대로 재현해 `/health`(200), `/predict`(403), `/predict/live`(200, bureau 이력 포함 정상 처리)까지 전부 확인함 — **위 §3.2의 `git clone`만으로 배포가 완결된다는 것이 실증됨**.
- **Dockerfile CMD의 PORT 하드코딩**: EC2는 `docker run -p 80:8000`으로 직접 포트 매핑하므로 Render와 달리 PORT 환경변수 대응이 필수가 아니라서 그대로 둠.

남은 것은 §1의 자격증명 발급과 실제 인스턴스 생성/배포 실행뿐입니다.
