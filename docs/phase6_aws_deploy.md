# Phase 6: AWS EC2 프리티어 배포 계획

Render 대신 AWS EC2 프리티어로 직접 배포하기로 결정. `/predict`(사전계산 조회) 제외 원칙은 배포처와 무관하게 그대로 적용.

## 0. 인스턴스 생성 완료 (2026-08-23)

| 항목 | 값 |
|---|---|
| Instance ID | `i-095d7fd112ba42311` |
| 상태 | **running** |
| 퍼블릭 IP | **`43.203.234.170`** |
| 인스턴스 타입 | **`t3.micro`** (계획은 t2.micro였으나 아래 참고) |
| 보안 그룹 | `sg-0d3618d0bb17ca9d5` (home-credit-sg) |

**계획과 달라진 점**: `t2.micro`로 생성 시도했으나 AWS가 `InvalidParameterCombination: The specified instance type is not eligible for Free Tier`로 거부함 — 이 계정(2026년 생성)은 `t2.micro`가 프리티어 대상이 아니고, `describe-instance-types --filters Name=free-tier-eligible,Values=true`로 확인한 실제 프리티어 대상은 `t3.micro`/`t4g.micro`/`t3.small`/`t4g.small` 등. 처음에 사용자가 제시한 두 후보(t2.micro 또는 t3.micro) 중 **t3.micro로 전환해 생성** — §4에서 이미 "t2.micro와 t3.micro는 RAM 동일(1GiB)"임을 실측 확인해뒀으므로 메모리 결론은 그대로 유효함.

## 0.1 실제 배포 완료 및 테스트 결과 (2026-08-23)

**배포 과정에서 하나 더 달라진 점**: 저장소가 비공개(private)라 인스턴스에서 익명 `git clone`이 `fatal: could not read Username`으로 실패함 — GitHub 토큰을 인스턴스에 심는 대신(자격증명을 다루지 않는다는 원칙 유지), **로컬 작업 트리를 `rsync`로 직접 전송**해 빌드에 필요한 파일(`app/`, `scripts/`, `models/`, `Dockerfile`, `.dockerignore`, `requirements-serving.txt`)만 옮김. 결과적으로 동일한 이미지가 빌드됨(git clone과 기능적으로 동일).

진행: `apt-get install docker.io` → `rsync`로 소스 전송 → `docker build` → `docker run -p 8000:8000 -e PUBLIC_DEPLOYMENT=true`. (사용자 요청으로 포트는 80 대신 8000 직접 사용 — 보안그룹에 8000 인바운드 0.0.0.0/0 추가로 열어둠)

### 외부(퍼블릭 IP)에서 실제 테스트

| 엔드포인트 | 결과 |
|---|---|
| `GET http://43.203.234.170:8000/health` | 200, `{"status":"ok"}` |
| `GET .../model/info` | 200, **`predict_lookup_enabled: false`** 확인 |
| `POST .../predict/live` (bureau 이력 포함) | 200, SHAP 상위 요인 포함 정상 응답 |
| `POST .../predict` (SK_ID_CURR=100001) | **403** — "disabled in public deployments..." 메시지 정상 |

### 실측 메모리 (t3.micro, 실제 인스턴스)

```
$ free -h
               total        used        free      shared  buff/cache   available
Mem:           911Mi       623Mi        62Mi       2.8Mi       405Mi       287Mi

$ docker stats home-credit-api --no-stream
MEM USAGE / LIMIT     MEM %
199.9MiB / 911.3MiB   21.93%
```

컨테이너 자체는 200MB 안팎으로 로컬에서 `--memory=1g`로 근사했던 실측치(154~178MB)와 거의 일치 — **사전 검토가 정확했음이 실제 배포로 재확인됨.** 시스템 전체 여유(available)도 287MiB 남아 있어 t3.micro(1GiB)로 안정적으로 운영 가능.

**퍼블릭 데모 URL**: `http://43.203.234.170:8000` (`/docs`에서 Swagger UI, `/predict/live`만 사용 가능) — ⚠️ 아래 §0.2에서 인스턴스를 stop했으므로 **현재는 접속 안 됨**

## 0.2 인스턴스 중지 (2026-08-23) 및 재시작 방법

프리티어 시간 관리를 위해 테스트 완료 후 인스턴스를 stop함(terminate 아님 — EBS 볼륨/설정은 그대로 보존, 과금은 중단됨). 상태:

```
$ aws ec2 stop-instances --instance-ids i-095d7fd112ba42311 --region ap-northeast-2
$ aws ec2 describe-instances --instance-ids i-095d7fd112ba42311 ...
stopped   (PublicIpAddress: None)
```

### 재시작 방법

**1) 인스턴스 시작**
```bash
aws ec2 start-instances --instance-ids i-095d7fd112ba42311 --region ap-northeast-2
aws ec2 wait instance-running --instance-ids i-095d7fd112ba42311 --region ap-northeast-2
```

**2) ⚠️ 퍼블릭 IP가 바뀝니다** — 이 인스턴스는 고정 IP(Elastic IP)를 안 붙였기 때문에, stop/start를 하면 **매번 새 퍼블릭 IP가 배정됨**(43.203.234.170은 더 이상 유효하지 않을 수 있음). 재시작 후 새 IP 확인:
```bash
aws ec2 describe-instances --instance-ids i-095d7fd112ba42311 --region ap-northeast-2 \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text
```
(데모 URL을 고정하고 싶으면 Elastic IP를 할당해 붙이는 방법이 있음 — 추후 필요시 검토)

**3) 컨테이너 재시작** — 이미지는 인스턴스 안에 그대로 남아있으므로 다시 빌드할 필요 없이 바로 실행 가능:
```bash
ssh -i home-credit-key.pem ubuntu@<새 퍼블릭 IP>
sudo docker start home-credit-api   # 기존 컨테이너 재사용 (docker run 다시 안 해도 됨)
# 만약 컨테이너/이미지가 없다면(예: 인스턴스를 새로 만든 경우):
#   cd ~/home-credit-default-risk && sudo docker build -t home-credit-api:latest .
#   sudo docker run -d --name home-credit-api -p 8000:8000 -e PUBLIC_DEPLOYMENT=true --restart unless-stopped home-credit-api:latest
```

**4) 보안그룹**: `sg-0d3618d0bb17ca9d5`의 SSH(22) 인바운드가 특정 IP(`218.53.83.49/32`)로 제한돼 있으므로, 재시작 시점에 내 IP가 바뀌었다면 콘솔에서 이 규칙을 현재 IP로 갱신해야 SSH 접속 가능(HTTP 8000/80 규칙은 계속 공개라 그대로 사용 가능).

**5) 완전히 정리하고 싶을 때(더 이상 안 쓸 경우)**: `aws ec2 terminate-instances --instance-ids i-095d7fd112ba42311` — 이건 되돌릴 수 없음(EBS 볼륨도 함께 삭제, DeleteOnTermination=true였음).

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
| 인스턴스 타입 | **t2.micro** (§4 — t3.micro 대비 메모리 차이 없음) | AWS 프리티어(12개월) 대상 |
| AMI | **`ami-05fa22e12f2cb12aa`** — Ubuntu 24.04 LTS(Noble) amd64, ap-northeast-2, 2026-07-14 빌드 | `aws ec2 describe-images`로 Canonical(099720109477) 공식 이미지 중 최신 버전을 직접 조회해 확인(추측 아님) |
| 리전/AZ | `ap-northeast-2` (서울), AZ `ap-northeast-2a` | 이미 설정된 리전 |
| VPC/서브넷 | 기본 VPC `vpc-05ea55000cfaa1752` / 서브넷 `subnet-0a4fbb138f8268018` | 계정에 이미 존재하는 default VPC 사용(추가 생성 불필요) |
| 스토리지 | 8GB gp3 (AMI 기본값) | 프리티어 30GB까지 무료, 우리 이미지 238MB 감안하면 충분 |
| 보안 그룹 | 신규 생성: `home-credit-sg` | 아래 인바운드 규칙 참고 |
| 키 페어 | **`home-credit-key`** (사용자가 콘솔에서 생성 예정) | SSH 접속용 |

**아키텍처**: 이 Mac은 Apple Silicon(arm64)이지만 t2.micro는 x86_64 전용이라, 위 AMI도 amd64로 골랐고 §3.2 계획대로 **인스턴스 안에서 직접 `docker build`**하므로 크로스 아키텍처 문제가 자동으로 해결됨.

### 보안 그룹 인바운드 규칙

| 포트 | 프로토콜 | 소스 | 용도 |
|---|---|---|---|
| 22 (SSH) | TCP | **`218.53.83.49/32`** (현재 이 세션에서 확인한 접속 IP) | SSH 접속. **주의**: IP가 유동적이면 나중에 접속 안 될 수 있어, 그때는 콘솔에서 이 규칙의 소스 IP를 현재 IP로 갱신 필요 |
| 80 (HTTP) | TCP | `0.0.0.0/0` | 공개 API 데모 접근 (`docker run -p 80:8000`로 매핑 예정) |

### 실행할 명령 (키 페어 생성 후, 아직 미실행 — 확인 후 진행)

```bash
# 1) 보안 그룹 생성
aws ec2 create-security-group \
  --group-name home-credit-sg \
  --description "Home Credit API demo - SSH(my IP) + HTTP(public)" \
  --vpc-id vpc-05ea55000cfaa1752 \
  --region ap-northeast-2

# 2) 인바운드 규칙 추가 (위에서 나온 SG ID로 치환)
aws ec2 authorize-security-group-ingress \
  --group-id <SG_ID> \
  --protocol tcp --port 22 --cidr 218.53.83.49/32 \
  --region ap-northeast-2

aws ec2 authorize-security-group-ingress \
  --group-id <SG_ID> \
  --protocol tcp --port 80 --cidr 0.0.0.0/0 \
  --region ap-northeast-2

# 3) 인스턴스 생성 (키 페어는 콘솔에서 home-credit-key로 먼저 생성해두어야 함)
aws ec2 run-instances \
  --image-id ami-05fa22e12f2cb12aa \
  --instance-type t2.micro \
  --key-name home-credit-key \
  --security-group-ids <SG_ID> \
  --subnet-id subnet-0a4fbb138f8268018 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=home-credit-api}]' \
  --region ap-northeast-2
```

인스턴스가 뜨면 `aws ec2 describe-instances --filters "Name=tag:Name,Values=home-credit-api"`로 퍼블릭 IP를 확인해 `ssh -i home-credit-key.pem ubuntu@<퍼블릭IP>`로 접속 → §3의 Docker 설치/빌드/실행 순서대로 진행.

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
