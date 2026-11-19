Kenyan Supply & Replenishment Planning Core
A Python data-science and constrained optimization engine designed for wholesale, retail, and distribution replenishment planning in Kenya. This repository intentionally does not build a website, dashboard UI, or web server. Its core work focuses cleanly on reproducible time-series forecasting, transparent data handling, and mathematical optimization:

Fitting ARIMA as a univariate baseline.

Fitting ARIMAX / SARIMAX with known future external variables.

Feeding p50 / p90 lead-time demand, current inventory position, cost parameters, and operational constraints into CVXPY (using HiGHS through CVXPY to enforce integer order multiples when available).

1. The Problem
Wholesale, retail, and distribution operators across Kenya navigate real operational and financial trade-offs when deciding how much stock to order and when to order it:

Uncertainty and changing market conditions: Demand and input costs are rarely static. Relying on static order rules or guesswork leaves operators exposed to stockouts during spikes or excess tied-up working capital when movement slows.

Hard operational, supplier, and budget constraints: Even a strong statistical forecast does not automatically translate into an executable purchase plan. Real replenishment decisions must stay within:

A fixed KSh budget (--budget-ksh)

Supplier capacity limits

Storage capacity limits

Order multiples (such as case, pack, carton, or batch sizes)

Trade-offs between holding costs and shortage penalties across central (p50) and high-risk (p90) demand scenarios

Separating public price benchmarks from internal demand: Publicly available market price datasets are useful for testing forecasting pipelines reproducibly, but market prices are not internal company demand or sell-through history. Presenting public price benchmarks as internal demand accuracy or realized inventory savings would be inaccurate.

2. The Solution
This project structures replenishment planning into a clear, reproducible pipeline:

Univariate Baseline (ARIMA): Establishes a clean baseline model on the target time series so any exogenous extensions must earn their complexity against a clear reference point.

Exogenous Modeling (ARIMAX / SARIMAX): Incorporates known or projected external drivers (such as related market prices, commercial drivers, or Kenyan market/seasonal context) to evaluate whether external variables add signal.

Constrained Replenishment Optimization (CVXPY): Combines p50_demand and p90_demand with inventory_position, unit_cost_ksh, storage_capacity, supplier_capacity, order_multiple, holding_cost_ksh, and shortage_penalty_ksh under --budget-ksh. It uses HiGHS through CVXPY when available to enforce integer order multiples and outputs:

Solver status

Order quantities

Spend (in KSh)

Ending inventory

Shortage units

Real Public Data Included (and Its Proper Scope)
data/public/wfp_food_prices_ken.csv is a real World Food Programme (WFP) Kenya market-price dataset downloaded from HDX.

It is included for a reproducible price-model run, not as company demand.

On the current snapshot, the six-month public-price holdout (--market Nairobi --target 'Oil (vegetable)' --exog Bread --holdout 6 --horizon 6) produced a WAPE of 23.13% for ARIMA and 23.62% for ARIMAX. This is a price-model demonstration, not a demand accuracy result or an inventory savings claim.

3. What to Install
Set up a clean Python environment and install the dependencies listed in requirements.txt:

Bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
Make sure requirements.txt includes your core Python data and optimization stack—such as pandas, numpy, statsmodels, cvxpy, and highspy (so HiGHS is available through CVXPY for integer order multiples).

4. How to Run It
Run all commands from the repository root with your virtual environment activated.

Step 1: Profile the Public Data and Run the ARIMA / ARIMAX Demonstration
Bash
python3 scripts/profile_public_data.py
python3 scripts/run_core_models.py --market Nairobi --target 'Oil (vegetable)' --exog Bread --holdout 6 --horizon 6
This writes ARIMA and ARIMAX forecasts along with holdout metrics to data/processed/core_model/.

Step 2: Prepare the Planning Input CSV and Run the CVXPY Replenishment Model
Start from the header and structure in data/optimization_input_template.csv to prepare your employer planning input file (for example, path/to/employer_planning_input.csv), ensuring all required columns are present:

sku_id

location_id

p50_demand

p90_demand

inventory_position

unit_cost_ksh

storage_capacity

supplier_capacity

order_multiple

holding_cost_ksh

shortage_penalty_ksh

Then run the CVXPY replenishment script with your KSh budget:

Bash
python3 scripts/run_cvpy_plan.py --planning-input path/to/employer_planning_input.csv --budget-ksh 250000
The model returns the solver status, order quantities, KSh spend, ending inventory, and shortage units.
