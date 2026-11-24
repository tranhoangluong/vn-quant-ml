from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class BaseModel(ABC):
    """Giao diện chung để walk-forward không phụ thuộc mô hình cụ thể."""

    @abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series, X_val=None, y_val=None) -> BaseModel: ...

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray: ...
