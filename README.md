This is a Python data-science core for a Kenyan wholesale, retail, or distribution planning problem. It intentionally does not build a website. The core work is:

Fit ARIMA as a univariate baseline.
Fit ARIMAX/SARIMAX with known future external variables.
Feed p50/p90 lead-time demand, inventory and supplier constraints into CVXPY.
Real data included
data/public/wfp_food_prices_ken.csv is a real WFP Kenya market-price file downloaded from HDX. It is used for a reproducible price-model run. It is not company demand, so the public demonstration must not be described as demand accuracy or inventory savings.

Run the public Kenyan model demonstration
bash python3 -m pip install -r requirements.txt python3 scripts/profile_public_data.py python3 scripts/run_core_models.py --market Nairobi --target 'Oil (vegetable)' --exog Bread --holdout 6 --horizon 6

This writes ARIMA and ARIMAX forecasts plus holdout metrics to data/processed/core_model/. On the current snapshot, the six-month public-price holdout produced WAPE of 23.13% for ARIMA and 23.62% for ARIMAX. That is a price-model demonstration, not a demand result.
Run the CVXPY replenishment model
Prepare an employer planning input using the header in data/optimization_input_template.csv, then run:

bash python3 scripts/run_cvxpy_plan.py \ --planning-input path/to/employer_planning_input.csv \ --budget-ksh 250000

Required fields are sku_id, location_id, p50_demand, p90_demand, inventory_position, unit_cost_ksh, storage_capacity, supplier_capacity, order_multiple, holding_cost_ksh, and shortage_penalty_ksh. The model returns solver status, order quantities, spend, ending inventory and shortage units. It uses HIGHS through CVXPY to enforce integer order multiples when available.

Employer explanation
“I did not stop at predicting demand. ARIMA gives the baseline, ARIMAX adds known commercial or Kenyan market drivers, and CVXPY chooses the feasible order plan under the KSh budget, supplier limits and service-risk penalty. The public data proves the modeling path; the employer's sell-through and inventory history is required before claiming company-specific accuracy or savings.”

Sources
The data-availability report is reports/kenya_data_and_employer_story.md. Public context sources are KNBS Leading Economic Indicators, KAMIS, the World Bank Kenya price catalog, and Kenya Meteorological Department services.
