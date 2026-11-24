from __future__ import annotations

import numpy as np
import pandas as pd

from .base import BaseModel


class LGBMModel(BaseModel):
    def __init__(self, **params):
        p = dict(params)
        self.n_estimators = p.pop("n_estimators", 1000)
        self.early_stopping_rounds = p.pop("early_stopping_rounds", 100)
        self.params = p
        self.booster = None

    def fit(self, X, y, X_val=None, y_val=None):
        import lightgbm as lgb

        dtrain = lgb.Dataset(X, y)
        valid, callbacks = [dtrain], []
        if X_val is not None:
            valid = [lgb.Dataset(X_val, y_val, reference=dtrain)]
            callbacks.append(lgb.early_stopping(self.early_stopping_rounds, verbose=False))
        self.booster = lgb.train(
            self.params, dtrain, self.n_estimators, valid_sets=valid, callbacks=callbacks
        )
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.booster.predict(X, num_iteration=self.booster.best_iteration or None)

    def feature_importance(self) -> pd.Series:
        return pd.Series(self.booster.feature_importance("gain"), index=self.booster.feature_name())
