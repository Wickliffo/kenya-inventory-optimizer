from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core_models import optimize_replenishment

REQUIRED = [
    "sku_id", "location_id", "p50_demand", "p90_demand", "inventory_position",
    "unit_cost_ksh", "storage_capacity", "supplier_capacity", "order_multiple",
    "holding_cost_ksh", "shortage_penalty_ksh",
]
parser = argparse.ArgumentParser(description="Solve a CVXPY replenishment plan from employer forecast outputs")
parser.add_argument("--planning-input", required=True, help="CSV containing one row per SKU-location planning line")
parser.add_argument("--budget-ksh", required=True, type=float)
parser.add_argument("--output-dir", default="data/processed/cvxpy_plan")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
planning = pd.read_csv(root / args.planning_input)
missing = sorted(set(REQUIRED) - set(planning.columns))
if missing:
    raise SystemExit(f"Missing required columns: {missing}")
result = optimize_replenishment(planning, args.budget_ksh)
out_dir = root / args.output_dir
out_dir.mkdir(parents=True, exist_ok=True)
result.order_plan.to_csv(out_dir / "order_plan.csv", index=False)
(out_dir / "optimization_result.json").write_text(json.dumps({"status": result.status, "solver": result.solver, "objective_value": result.objective_value, "constraints": result.constraints, "message": result.message}, indent=2, default=str))
print(json.dumps({"status": result.status, "solver": result.solver, "objective_value": result.objective_value, "constraints": result.constraints, "message": result.message}, indent=2, default=str))
print(f"Wrote {out_dir / 'order_plan.csv'}")
