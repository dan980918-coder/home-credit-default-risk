# 이미지 크기 절감을 위해 slim 베이스 + 서빙 전용 requirements(requirements-serving.txt) 사용.
# data/(원본 CSV·전처리 parquet)는 이미지에 굽지 않고 런타임에 볼륨 마운트로 제공
# (PROJECT_GUIDELINES.md §4: 원본 데이터는 배포/공개하지 않는다는 원칙과 일치,
# 이미지 크기도 그만큼 줄어듦).
FROM python:3.13-slim

# LightGBM은 OpenMP(libgomp)가 필요함 — slim 이미지엔 기본 미포함
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-serving.txt .
RUN pip install --no-cache-dir -r requirements-serving.txt

COPY app/ ./app/
COPY scripts/ ./scripts/
COPY models/ ./models/

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
