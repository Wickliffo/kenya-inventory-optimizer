from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "data/public/wfp_food_prices_ken.csv"
report_dir = ROOT / "reports"
report_dir.mkdir(exist_ok=True)
df = pd.read_csv(source, parse_dates=["date"])
df["price"] = pd.to_numeric(df["price"], errors="coerce")
valid = df.dropna(subset=["date", "price"]).copy()
profile = {
    "rows": int(len(valid)),
    "date_min": valid["date"].min().date().isoformat(),
    "date_max": valid["date"].max().date().isoformat(),
    "markets": int(valid["market"].nunique()),
    "commodities": int(valid["commodity"].nunique()),
    "price_types": valid["pricetype"].value_counts().to_dict(),
    "units_top": valid["unit"].value_counts().head(12).to_dict(),
    "missing_top": df.isna().sum().sort_values(ascending=False).head(10).to_dict(),
    "bad_dates": int(pd.to_datetime(df["date"], errors="coerce").isna().sum()),
    "bad_prices": int(pd.to_numeric(df["price"], errors="coerce").isna().sum()),
}
(report_dir / "public_data_profile.json").write_text(json.dumps(profile, indent=2, default=str))
text = [
    "# Real WFP Kenya price-data profile", "",
    "This profile was generated from `data/public/wfp_food_prices_ken.csv`. It is a market-price dataset, not an employer demand dataset.", "",
    f"- Rows after basic date/price cleaning: **{profile['rows']:,}**",
    f"- Date range: **{profile['date_min']} to {profile['date_max']}**",
    f"- Markets: **{profile['markets']:,}**",
    f"- Commodity labels: **{profile['commodities']:,}**", "", "## Price types", "",
]
text += [f"- {k}: {v:,}" for k, v in profile["price_types"].items()]
text += ["", "## Interpretation", "", "The file is appropriate for Kenyan price context, volatility analysis and ARIMAX experiments. It cannot measure company sell-through, stockouts, inventory position or supplier capacity. Those inputs must come from an employer operations export.", ""]
(report_dir / "public_data_profile.md").write_text("\n".join(text))
print(json.dumps(profile, indent=2, default=str))
