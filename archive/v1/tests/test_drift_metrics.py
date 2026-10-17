"""dashboard/drift_metrics.py의 PSI/KS 계산 함수 단위 테스트.

psi_continuous/ks_test는 NaN 사전 제거를 가정하고, 빈 배열이면 nan(psi_continuous는
0.0인 상수-분포 케이스도 별도)을 반환하도록 방어 로직이 있다. psi_categorical은
reference에 없던 카테고리가 batch에 새로 나타나도(비율 0 -> 1e-4로 floor) 에러 없이
동작하도록 돼 있다. 아래 테스트는 이 기존 동작을 검증한다.
"""
import math
import numpy as np
import pytest

from dashboard.drift_metrics import psi_continuous, psi_categorical, ks_test, PSI_WARNING

RNG = np.random.default_rng(42)


# ---------------------------------------------------------------------------
# psi_continuous
# ---------------------------------------------------------------------------

def test_psi_continuous_identical_distribution_is_near_zero():
    x = RNG.normal(size=2000)
    assert psi_continuous(x, x) == pytest.approx(0.0, abs=1e-9)


def test_psi_continuous_shifted_distribution_exceeds_warning_threshold():
    reference = RNG.normal(loc=0, scale=1, size=2000)
    batch = RNG.normal(loc=5, scale=1, size=2000)  # 완전히 갈라진 분포
    assert psi_continuous(reference, batch) > PSI_WARNING


def test_psi_continuous_empty_array_returns_nan():
    assert math.isnan(psi_continuous(np.array([]), np.array([1.0, 2.0, 3.0])))
    assert math.isnan(psi_continuous(np.array([1.0, 2.0, 3.0]), np.array([])))


def test_psi_continuous_degenerate_breakpoints_returns_zero():
    """buckets=1이면 분위수 경계가 (-inf, +inf) 둘로만 붕괴해 '의미있는 구간을
    만들 수 없음' 방어 분기(len(breakpoints) < 3)를 탄다. 참고: 기본값
    buckets=10에서는 상수 reference라도 경계가 (-inf, 값, +inf) 3개로 남아
    이 분기를 타지 않고 실제 PSI를 계산한다 — 상수 분포 자체가 곧 PSI=0을
    보장하는 것은 아니다."""
    reference = np.full(100, 5.0)
    batch = RNG.normal(size=100)
    assert psi_continuous(reference, batch, buckets=1) == 0.0


# ---------------------------------------------------------------------------
# psi_categorical
# ---------------------------------------------------------------------------

def test_psi_categorical_identical_distribution_is_near_zero():
    cats = np.array(["A", "A", "B", "B", "C"] * 20)
    assert psi_categorical(cats, cats) == pytest.approx(0.0, abs=1e-9)


def test_psi_categorical_shifted_ratio_increases_psi():
    reference = np.array(["A"] * 90 + ["B"] * 10)
    batch = np.array(["A"] * 10 + ["B"] * 90)  # 비율이 뒤집힘
    assert psi_categorical(reference, batch) > PSI_WARNING


def test_psi_categorical_new_category_not_in_reference_does_not_crash():
    reference = np.array(["A", "A", "B", "B"])
    batch = np.array(["A", "B", "C", "C"])  # "C"는 reference에 없던 카테고리
    result = psi_categorical(reference, batch)
    assert math.isfinite(result)
    assert result > 0  # 신규 카테고리 등장은 drift 신호로 반영돼야 함


# ---------------------------------------------------------------------------
# ks_test
# ---------------------------------------------------------------------------

def test_ks_test_identical_distribution_is_not_significant():
    x = RNG.uniform(size=200)
    stat, p = ks_test(x, x)
    assert stat == pytest.approx(0.0, abs=1e-9)
    assert p > 0.05


def test_ks_test_clearly_different_distribution_is_significant():
    reference = RNG.uniform(0, 1, size=200)
    batch = RNG.uniform(10, 11, size=200)  # 값 범위가 아예 겹치지 않음
    stat, p = ks_test(reference, batch)
    assert stat == pytest.approx(1.0)
    assert p < 0.05
