.PHONY: install data check-data snapshot freeze features train backtest report test lint app thesis all

CFG ?= configs/base.yaml

install:
	pip install -e ".[data,dev,app]"
	pre-commit install

data:        ## tải giá + danh sách VN30 → data/raw, làm sạch → data/interim
	python scripts/01_download_data.py --config $(CFG)
	python scripts/02_build_dataset.py --config $(CFG)

END ?= $(shell date +%Y-%m-%d)
snapshot:    ## snapshot nghiên cứu: mọi cổ phiếu (cả mã huỷ niêm), 2014 → END, giá + BCTC (~2 giờ)
	python scripts/01_download_data.py --config $(CFG) --universe all-stocks --start 2014-01-01 --end $(END) --snapshot $(END)

freeze:      ## đóng băng snapshot END: checksum + zip sao lưu
	python scripts/freeze_snapshot.py --config $(CFG) --snapshot $(END) --zip

check-data:  ## kiểm tra snapshot mới nhất (+ kiểm chéo KBS cho FPT)
	python scripts/check_data.py --config $(CFG) --crosscheck FPT

features:    ## tạo feature + nhãn → data/processed/panel.parquet
	python scripts/03_build_features.py --config $(CFG)

train:       ## walk-forward LightGBM + conformal → experiments/<run_id>/
	python scripts/04_train_walkforward.py --config $(CFG)

backtest:    ## backtest long-only có ràng buộc biên độ, T+2, phí
	python scripts/05_backtest.py --config $(CFG)

report:      ## bảng/hình cho luận văn → reports/ và thesis/
	python scripts/06_make_report.py --config $(CFG)

all: data features train backtest report

test:
	pytest -q

lint:
	ruff check src tests scripts && ruff format --check src tests scripts

app:
	streamlit run app/streamlit_app.py

thesis:
	cd thesis && latexmk -pdf main.tex
