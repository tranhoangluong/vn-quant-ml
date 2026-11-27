# vn-quant-ml

**Uncertainty-aware long-only stock selection on Vietnam's VN30**: LightGBM cross-sectional
return forecasts + adaptive conformal prediction (ACI / DtACI), backtested under real
Vietnamese market frictions (±7% price limits, T+2 settlement, no short selling, fees and tax).

> Master's thesis project, 2026–2027. Research code, not investment advice.

[![ci](https://github.com/tranhoangluong/vn-quant-ml/actions/workflows/ci.yml/badge.svg)](https://github.com/tranhoangluong/vn-quant-ml/actions/workflows/ci.yml)

## Why this project

- Most ML-for-stocks backtests ignore that in Vietnam you **cannot buy a stock locked at its
  ceiling, cannot sell one at the floor, cannot sell before T+2, and cannot short**. This repo
  models those constraints explicitly and measures how much of a "paper" Sharpe they destroy.
- Point forecasts are not enough: conformal intervals with **guaranteed coverage under
  distribution shift** decide *how much* to buy, not only *what*.
- Results are stress-tested against backtest overfitting with **Deflated Sharpe Ratio** and
  **Probability of Backtest Overfitting**.

## Results

_TODO (week ~18): headline table (IC, coverage, net Sharpe, max DD, DSR) + equity curve._

## Quickstart

```bash
git clone https://github.com/tranhoangluong/vn-quant-ml && cd vn-quant-ml
python -m venv .venv && source .venv/bin/activate
make install          # pip install -e ".[data,dev,app]"
make test             # offline, synthetic data
make all              # download → features → walk-forward → backtest → report
```

Run a single experiment: `make train backtest CFG=configs/experiments/E03_lgbm_aci.yaml`

## Method in one picture

```
prices (Vietcap API) ─► point-in-time VN30 universe ─► features (rank) ─► LightGBM
     ─► conformal interval [lo, hi] (ACI) ─► long-only sizing ─► VN constraints ─► net returns
```

See [docs/architecture.md](docs/architecture.md) for the module map.

## Repository layout

```
configs/      YAML configs; experiments/ inherit base.yaml
data/         raw / interim / processed (git-ignored), external/ (VN30 membership, committed)
src/vnqml/    the package: data, features, labels, models, uncertainty, portfolio, backtest, evaluation
scripts/      numbered pipeline steps 01..07
notebooks/    exploration and figures only
tests/        unit (no look-ahead, splits, conformal, constraints) + synthetic end-to-end
experiments/  one folder per run with config + predictions + metrics (git-ignored)
reports/      generated tables and figures
thesis/       LaTeX source of the thesis
app/          Streamlit dashboard
docs/         architecture, data, experiment log, roadmap
```

## Experiments

| ID | Model | Uncertainty | Sizing | Purpose |
|---|---|---|---|---|
| E00 | Momentum 12-1 | none | equal | non-ML baseline |
| E01 | LightGBM | none | equal | point forecast |
| E02 | LightGBM | split conformal | conformal | static intervals |
| E03 | LightGBM | ACI | conformal | **main method** |
| E04 | LightGBM | DtACI | conformal | adaptive step size |
| E05 | LightGBM | ACI | conformal | ablation: no VN frictions |

## Data

Free sources only (Vietcap/KBS public web APIs, HOSE announcements, CafeF; see `docs/data_guide.md`). Raw data is not redistributed; `make data`
rebuilds it. Survivorship bias is handled with a hand-curated VN30 membership history in
`data/external/`. See [docs/data.md](docs/data.md).

## Limitations

Execution at next-day close (no intraday/VWAP), adjusted prices from a free provider, VN30 only.

## Citation / License

MIT. If you use this work, please cite the thesis (BibTeX to be added).
