"""여러 학습/모델링 스크립트에서 반복되던 두 가지 패턴을 공유 함수로 분리.
train_serving_model.py, train_monitoring_model.py, phase4_modeling.py,
phase4_lr_rescale.py, phase4_shap_analysis.py, dashboard/monitoring_dashboard.py가
동일한 로직을 각자 인라인으로 갖고 있던 것을 여기로 모음 —
scripts/_lean_a_features.py를 배치 파이프라인과 API가 공유하는 것과 동일한 패턴.
"""
import lightgbm as lgb


def prepare_categorical_columns(X):
    """object/bool dtype 컬럼을 LightGBM 네이티브 categorical dtype으로 변환.
    X를 in-place로 수정하고 (X, cat_cols)를 반환한다."""
    cat_cols = [c for c in X.columns if X[c].dtype == object or str(X[c].dtype) == "bool"]
    for c in cat_cols:
        X[c] = X[c].astype(str).astype("category")
    return X, cat_cols


def train_lightgbm(X_train, y_train, scale_pos_weight, *, n_estimators=200,
                    random_state=42, categorical_feature="auto", **kwargs):
    """LightGBM 이진분류기 생성+학습. n_estimators/scale_pos_weight/random_state/
    verbosity=-1는 프로젝트 전반에서 반복되는 기본값 — 파일마다 필요한 추가
    하이퍼파라미터는 kwargs로 LGBMClassifier 생성자에 그대로 전달된다."""
    model = lgb.LGBMClassifier(
        n_estimators=n_estimators,
        scale_pos_weight=scale_pos_weight,
        random_state=random_state,
        verbosity=-1,
        **kwargs,
    )
    model.fit(X_train, y_train, categorical_feature=categorical_feature)
    return model
