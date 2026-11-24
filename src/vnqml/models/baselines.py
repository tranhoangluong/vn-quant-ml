"""Baseline bắt buộc trong luận văn: luật momentum và hồi quy tuyến tính."""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import Ridge

from .base import BaseModel


class MomentumRule(BaseModel):
    def __init__(self, feature: str = "mom_12_1", **_):
        self.feature = feature

    def fit(self, X, y, X_val=None, y_val=None):
        return self

    def predict(self, X) -> np.ndarray:
        return X[self.feature].fillna(0).to_numpy()


class RidgeModel(BaseModel):
    def __init__(self, alpha: float = 1.0, **_):
        self.m = Ridge(alpha=alpha)

    def fit(self, X, y, X_val=None, y_val=None):
        self.m.fit(X.fillna(0), y)
        return self

    def predict(self, X) -> np.ndarray:
        return self.m.predict(X.fillna(0))
