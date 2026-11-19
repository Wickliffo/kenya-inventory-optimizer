from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core_models import fit_arima, fit_arimax, monthly_price_series, save_forecast, wape

parser = argparse.ArgumentParser(description="Run ARIMA and ARIMAX on a real Kenyan public market-price series")
parser.add_argument("--price-file", default="data/public/wfp_food_prices_ken.csv")
parser.add_argument("--market", default="Nairobi")
parser.add_argument("--target", default="Oil (vegetable)")
parser.add_argument("--exog", default="Bread")
parser.add_argument("--holdout", type=int, default=6)
parser.add_argument("--horizon", type=int, default=6)
parser.add_argument("--output-dir", default="data/processed/core_model")
args = parser.parse_args()

root = Path(__file__).resolve().parents[1]
out_dir = root / args.output_dir
out_dir.mkdir(parents=True, exist_ok=True)
prices = pd.read_csv(root / args.price_file, parse_dates=["date"])
series = monthly_price_series(prices, args.market, args.target, [args.exog], "Retail")
if len(series) <= args.holdout + 24:
    raise SystemExit(f"Only {len(series)} aligned monthly observations; need more history for a holdout.")

train = series.iloc[:-args.holdout]
test = series.iloc[-args.holdout:]
train_y = train["y"]
train_x = train[["x_0"]]
test_x = test[["x_0"]]
arima = fit_arima(train_y, args.holdout)
arimax = fit_arimax(train_y, train_x, test_x, args.holdout)
metrics = {
    "market": args.market,
    "target": args.target,
    "exogenous": args.exog,
    "price_type": "Retail",
    "observations": len(series),
    "holdout_months": args.holdout,
    "arima_wape_pct": wape(test["y"], arima.forecast["p50"]),
    "arimax_wape_pct": wape(test["y"], arimax.forecast["p50"]),
    "arima_diagnostics": arima.diagnostics,
    "arimax_diagnostics": arimax.diagnostics,
    "interpretation": "This is a public market-price forecasting demonstration. It is not company demand accuracy.",
}
(out_dir / "holdout_metrics.json").write_text(json.dumps(metrics, indent=2, default=str))
# Refit on all observed public data. Future exogenous values are held at the last observed value
# only for a mechanical demonstration; production must supply planned future regressors.
full_y = series["y"]
future_x = pd.DataFrame({"x_0": [series["x_0"].iloc[-1]] * args.horizon})
full_x = series[["x_0"]]
full_arima = fit_arima(full_y, args.horizon)
full_arimax = fit_arimax(full_y, full_x, future_x, args.horizon)
save_forecast(full_arima, out_dir / "arima_forecast.csv")
save_forecast(full_arimax, out_dir / "arimax_forecast.csv")
print(json.dumps(metrics, indent=2, default=str))
print(f"Wrote forecasts to {out_dir}")
