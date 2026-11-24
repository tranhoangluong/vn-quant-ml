"""Conformal prediction cho khoảng dự báo lợi suất.

- SplitConformal: khoảng tĩnh từ tập calibration (giả định trao đổi được).
- ACI (Gibbs & Candès 2021): cập nhật alpha_t theo lỗi phủ, bền với dịch chuyển phân phối.
- DtACI (Gibbs & Candès 2024): chạy nhiều gamma và trộn theo trọng số mũ.

Lưu ý thời gian: nhãn horizon h chỉ biết sau h phiên, nên phản hồi lỗi phủ
được trễ `horizon` ngày (xem `predict_online`). Đây là chi tiết dễ làm sai.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class NoCalibrator:
    def fit(self, y, pred):
        return self

    def predict_online(self, y: pd.Series, pred: np.ndarray, horizon: int = 1):
        return np.full(len(pred), -np.inf), np.full(len(pred), np.inf)


class SplitConformal:
    def __init__(self, alpha: float = 0.1):
        self.alpha = alpha
        self.scores: np.ndarray | None = None

    def fit(self, y, pred):
        self.scores = np.sort(np.abs(np.asarray(y) - np.asarray(pred)))
        return self

    def quantile(self, alpha: float) -> float:
        n = len(self.scores)
        if alpha <= 0:
            return np.inf
        if alpha >= 1:
            return 0.0
        k = int(np.ceil((n + 1) * (1 - alpha))) - 1
        return float(self.scores[min(max(k, 0), n - 1)]) if k < n else np.inf

    def predict_online(self, y: pd.Series, pred: np.ndarray, horizon: int = 1):
        q = self.quantile(self.alpha)
        return pred - q, pred + q


class ACI(SplitConformal):
    """Một alpha_t chung cho cả tiết diện mỗi ngày; cập nhật bằng tỷ lệ lỗi phủ của ngày."""

    def __init__(self, alpha: float = 0.1, gamma: float = 0.005):
        super().__init__(alpha)
        self.gamma = gamma

    def _run(self, y: pd.Series, pred: np.ndarray, horizon: int, gamma: float):
        dates = y.index.get_level_values("date")
        udates = pd.DatetimeIndex(sorted(set(dates)))
        pos = udates.searchsorted(dates)
        lo, hi = np.empty(len(pred)), np.empty(len(pred))
        alpha_t = self.alpha
        errs: dict[int, float] = {}
        alphas = np.empty(len(udates))
        yv = y.to_numpy()
        for i in range(len(udates)):
            if i - horizon in errs:  # chỉ dùng lỗi đã quan sát được
                alpha_t = alpha_t + gamma * (self.alpha - errs[i - horizon])
            alphas[i] = alpha_t
            m = pos == i
            q = self.quantile(alpha_t)
            lo[m], hi[m] = pred[m] - q, pred[m] + q
            errs[i] = float(np.mean((yv[m] < lo[m]) | (yv[m] > hi[m])))
        self.alpha_path_ = pd.Series(alphas, index=udates)
        return lo, hi, errs

    def predict_online(self, y, pred, horizon=1):
        lo, hi, _ = self._run(y, np.asarray(pred), horizon, self.gamma)
        return lo, hi


class DtACI(ACI):
    """Phiên bản đơn giản: chọn chuyên gia (gamma) theo pinball-loss có trọng số mũ."""

    def __init__(self, alpha: float = 0.1, gammas=(0.001, 0.005, 0.01, 0.05), eta: float = 2.0):
        super().__init__(alpha)
        self.gammas, self.eta = list(gammas), eta

    def predict_online(self, y, pred, horizon=1):
        runs = [self._run(y, np.asarray(pred), horizon, g) for g in self.gammas]
        miss = np.array([[runs[j][2][i] for i in sorted(runs[j][2])] for j in range(len(runs))])
        loss = np.abs(miss - self.alpha)  # TODO: thay bằng pinball loss đúng theo bài báo
        cum = np.cumsum(np.pad(loss, ((0, 0), (horizon, 0)))[:, : loss.shape[1]], axis=1)
        w = np.exp(-self.eta * cum)
        w /= w.sum(0, keepdims=True)
        dates = y.index.get_level_values("date")
        pos = pd.DatetimeIndex(sorted(set(dates))).searchsorted(dates)
        lo = sum(w[j, pos] * runs[j][0] for j in range(len(runs)))
        hi = sum(w[j, pos] * runs[j][1] for j in range(len(runs)))
        return lo, hi
