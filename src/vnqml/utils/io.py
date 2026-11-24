"""Đọc/ghi parquet và tạo thư mục run có timestamp."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml


def save_parquet(df: pd.DataFrame, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return path


def load_parquet(path: str | Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def new_run_dir(cfg: dict, name: str | None = None) -> Path:
    """experiments/<YYYYmmdd-HHMMSS>_<name>/ kèm bản sao config để tái lập kết quả."""
    name = name or Path(cfg["_meta"]["config_path"]).stem
    d = Path(cfg["project"]["run_dir"]) / f"{datetime.now():%Y%m%d-%H%M%S}_{name}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "config.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return d


def save_json(obj: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=float))
