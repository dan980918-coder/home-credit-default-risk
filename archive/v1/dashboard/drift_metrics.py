"""
Phase 7: PSI(Population Stability Index) + KS(Kolmogorov-Smirnov) drift 지표.
신용평가/스코어카드 모니터링 업계 표준 방식으로 직접 구현(외부 drift 전용
라이브러리 미사용 — 계산 로직 자체를 명시적으로 보여주기 위함).
"""
import numpy as np
from scipy.stats import ks_2samp

# 업계 관행적 PSI 임계값
PSI_STABLE = 0.10
PSI_WARNING = 0.25


def psi_continuous(reference: np.ndarray, batch: np.ndarray, buckets: int = 10) -> float:
    """연속형 변수 PSI. reference의 분위수로 구간을 나누고 두 분포의 구간별
    비율 차이를 비교. NaN은 사전에 제거된 입력을 받는다고 가정."""
    reference = np.asarray(reference, dtype=float)
    batch = np.asarray(batch, dtype=float)
    if len(reference) == 0 or len(batch) == 0:
        return float("nan")

    breakpoints = np.percentile(reference, np.linspace(0, 100, buckets + 1))
    breakpoints[0] = -np.inf
    breakpoints[-1] = np.inf
    breakpoints = np.unique(breakpoints)  # 동일값이 많으면 구간이 줄어들 수 있음
    if len(breakpoints) < 3:
        return 0.0  # reference가 사실상 상수 -> 의미있는 구간을 만들 수 없음

    ref_counts, _ = np.histogram(reference, bins=breakpoints)
    batch_counts, _ = np.histogram(batch, bins=breakpoints)
    ref_pct = ref_counts / len(reference)
    batch_pct = batch_counts / len(batch)

    # 0으로 나누기/log(0) 방지용 최소값
    ref_pct = np.where(ref_pct == 0, 1e-4, ref_pct)
    batch_pct = np.where(batch_pct == 0, 1e-4, batch_pct)

    return float(np.sum((batch_pct - ref_pct) * np.log(batch_pct / ref_pct)))


def psi_categorical(reference: np.ndarray, batch: np.ndarray) -> float:
    """범주형 변수 PSI. 구간 대신 카테고리 값 자체를 버킷으로 사용."""
    reference = np.asarray(reference, dtype=object)
    batch = np.asarray(batch, dtype=object)
    categories = sorted(set(reference.tolist()) | set(batch.tolist()), key=str)

    ref_pct = np.array([np.mean(reference == c) for c in categories])
    batch_pct = np.array([np.mean(batch == c) for c in categories])
    ref_pct = np.where(ref_pct == 0, 1e-4, ref_pct)
    batch_pct = np.where(batch_pct == 0, 1e-4, batch_pct)

    return float(np.sum((batch_pct - ref_pct) * np.log(batch_pct / ref_pct)))


def ks_test(reference: np.ndarray, batch: np.ndarray) -> tuple[float, float]:
    """KS 통계량 + p-value (연속형 전용)."""
    reference = np.asarray(reference, dtype=float)
    batch = np.asarray(batch, dtype=float)
    if len(reference) == 0 or len(batch) == 0:
        return float("nan"), float("nan")
    stat, p = ks_2samp(reference, batch)
    return float(stat), float(p)


def psi_status(value: float) -> str:
    if np.isnan(value):
        return "unknown"
    if value < PSI_STABLE:
        return "stable"
    if value < PSI_WARNING:
        return "moderate"
    return "significant"


PSI_STATUS_COLOR = {
    "stable": "#2e7d32",      # green
    "moderate": "#f9a825",    # amber
    "significant": "#c62828",  # red
    "unknown": "#9e9e9e",
}
PSI_STATUS_LABEL_KO = {
    "stable": "안정",
    "moderate": "주의(중간 변화)",
    "significant": "경고(심각한 drift)",
    "unknown": "판단불가",
}
