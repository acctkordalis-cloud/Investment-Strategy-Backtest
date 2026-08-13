import os

import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from pandas_datareader import data as web


# --------------------------------------------------
# 1. PROJECT SETTINGS
# --------------------------------------------------

start_date = "1996-01-01"

# We use February 1, 2026 as the download end date
# so that January 2026 month-end data is included.
end_date = "2026-02-01"

spy_ticker = "SPY"
TBILL_SERIES = "TB3MS"

INITIAL_CAPITAL = 10000

YEARS = 30
MONTHS = YEARS * 12

SPY_WEIGHT = 0.50
TBILL_WEIGHT = 0.50

DAYS_TO_MATURITY = 91


# --------------------------------------------------
# 2. DOWNLOAD SPY DATA FROM YAHOO FINANCE
# --------------------------------------------------

spy_data = yf.download(
    spy_ticker,
    start=start_date,
    end=end_date,
    auto_adjust=True,
    progress=False
)

print("\nSPY raw data:")
print(spy_data.head())


# --------------------------------------------------
# 3. KEEP ONLY SPY ADJUSTED CLOSING PRICES
# --------------------------------------------------

# yfinance may return MultiIndex columns.
if isinstance(spy_data.columns, pd.MultiIndex):
    spy_prices = spy_data["Close"][spy_ticker].copy()
else:
    spy_prices = spy_data["Close"].copy()

print("\nSPY daily adjusted prices:")
print(spy_prices.head())


# --------------------------------------------------
# 4. CONVERT DAILY PRICES TO MONTH-END PRICES
# --------------------------------------------------

spy_monthly = spy_prices.resample("ME").last()

print("\nSPY monthly prices:")
print(spy_monthly.head())


# --------------------------------------------------
# 5. CALCULATE SPY MONTHLY RETURNS
# --------------------------------------------------

spy_returns = spy_monthly.pct_change().dropna()

print("\nSPY monthly returns:")
print(spy_returns.head())


# --------------------------------------------------
# 6. DOWNLOAD 3-MONTH TREASURY BILL DATA FROM FRED
# --------------------------------------------------

tbill_data = web.DataReader(
    TBILL_SERIES,
    "fred",
    start_date,
    end_date
)

print("\nRaw T-Bill data:")
print(tbill_data.head())


# --------------------------------------------------
# 7. RENAME T-BILL COLUMN
# --------------------------------------------------

tbill_data = tbill_data.rename(
    columns={"TB3MS": "TBill_Yield"}
)


# --------------------------------------------------
# 8. CONVERT T-BILL YIELD FROM PERCENT TO DECIMAL
# --------------------------------------------------

tbill_data["TBill_Yield"] = (
    tbill_data["TBill_Yield"] / 100
)


# --------------------------------------------------
# 9. CALCULATE APPROXIMATE T-BILL PRICE
# --------------------------------------------------

# Face value is normalized to 1.
tbill_data["TBill_Price"] = 1 - (
    tbill_data["TBill_Yield"]
    * DAYS_TO_MATURITY
    / 360
)


# --------------------------------------------------
# 10. CALCULATE 3-MONTH HOLDING-PERIOD RETURN
# --------------------------------------------------

tbill_data["TBill_3M_Return"] = (
    1 / tbill_data["TBill_Price"]
) - 1


# --------------------------------------------------
# 11. CONVERT 3-MONTH RETURN TO MONTHLY RETURN
# --------------------------------------------------

tbill_data["TBill_Monthly_Return"] = (
    (1 + tbill_data["TBill_3M_Return"]) ** (1 / 3)
) - 1

print("\nT-Bill calculations:")
print(tbill_data.head())


# --------------------------------------------------
# 12. ALIGN T-BILL DATES WITH MONTH-END
# --------------------------------------------------

tbill_monthly = (
    tbill_data["TBill_Monthly_Return"]
    .copy()
)

tbill_monthly.index = (
    tbill_monthly.index
    .to_period("M")
    .to_timestamp("M")
)


# --------------------------------------------------
# 13. COMBINE SPY AND T-BILL MONTHLY RETURNS
# --------------------------------------------------

returns_data = pd.concat(
    [spy_returns, tbill_monthly],
    axis=1,
    sort=False
)

returns_data.columns = [
    "SPY_Return",
    "TBill_Return"
]

returns_data = returns_data.dropna()


# Keep exactly 360 monthly return observations
returns_data = returns_data.iloc[:MONTHS].copy()


print("\nCombined monthly returns:")
print(returns_data.head())

print("\nNumber of monthly return observations:")
print(len(returns_data))

print("\nDataset start date:")
print(returns_data.index.min())

print("\nDataset end date:")
print(returns_data.index.max())


# Check that we really have 30 years of monthly returns
if len(returns_data) != MONTHS:
    raise ValueError(
        f"Expected {MONTHS} monthly returns, "
        f"but found {len(returns_data)}."
    )


# ==================================================
# STRATEGY 1
# 50% SPY + 50% T-BILLS
# LUMP-SUM INVESTMENT
# ==================================================


# --------------------------------------------------
# 14. INITIALIZE LUMP-SUM PORTFOLIO
# --------------------------------------------------

spy_balance = INITIAL_CAPITAL * SPY_WEIGHT
tbill_balance = INITIAL_CAPITAL * TBILL_WEIGHT

lump_sum_spy_values = []
lump_sum_tbill_values = []
lump_sum_values = []
lump_sum_returns = []


# --------------------------------------------------
# 15. RUN LUMP-SUM BACKTEST
# --------------------------------------------------

for date, row in returns_data.iterrows():

    starting_value = (
        spy_balance
        + tbill_balance
    )

    spy_balance *= (
        1 + row["SPY_Return"]
    )

    tbill_balance *= (
        1 + row["TBill_Return"]
    )

    portfolio_value = (
        spy_balance
        + tbill_balance
    )

    portfolio_return = (
        portfolio_value / starting_value
    ) - 1

    lump_sum_spy_values.append(
        spy_balance
    )

    lump_sum_tbill_values.append(
        tbill_balance
    )

    lump_sum_values.append(
        portfolio_value
    )

    lump_sum_returns.append(
        portfolio_return
    )


# --------------------------------------------------
# 16. SAVE LUMP-SUM RESULTS
# --------------------------------------------------

returns_data["LumpSum_SPY"] = (
    lump_sum_spy_values
)

returns_data["LumpSum_TBill"] = (
    lump_sum_tbill_values
)

returns_data["LumpSum_Total"] = (
    lump_sum_values
)

returns_data["LumpSum_Return"] = (
    lump_sum_returns
)

final_lump_sum_value = (
    returns_data["LumpSum_Total"].iloc[-1]
)


# ==================================================
# STRATEGY 2
# 50% SPY + 50% T-BILLS
# MONTHLY CONTRIBUTIONS
# ==================================================


# --------------------------------------------------
# 17. MONTHLY CONTRIBUTION SIZE
# --------------------------------------------------

monthly_contribution = (
    INITIAL_CAPITAL / MONTHS
)

monthly_spy_contribution = (
    monthly_contribution * SPY_WEIGHT
)

monthly_tbill_contribution = (
    monthly_contribution * TBILL_WEIGHT
)


# --------------------------------------------------
# 18. INITIALIZE MONTHLY STRATEGY
# --------------------------------------------------

# Contribution #1 is invested before the first
# return period.
monthly_spy_balance = (
    monthly_spy_contribution
)

monthly_tbill_balance = (
    monthly_tbill_contribution
)

cumulative_contributions = (
    monthly_contribution
)

monthly_spy_values = []
monthly_tbill_values = []
monthly_portfolio_values = []
monthly_contributions_history = []
monthly_strategy_returns = []


# --------------------------------------------------
# 19. RUN MONTHLY CONTRIBUTION BACKTEST
# --------------------------------------------------

for i, (date, row) in enumerate(
    returns_data.iterrows()
):

    starting_value = (
        monthly_spy_balance
        + monthly_tbill_balance
    )

    # Existing capital earns this month's return
    monthly_spy_balance *= (
        1 + row["SPY_Return"]
    )

    monthly_tbill_balance *= (
        1 + row["TBill_Return"]
    )

    value_before_contribution = (
        monthly_spy_balance
        + monthly_tbill_balance
    )

    portfolio_return = (
        value_before_contribution
        / starting_value
    ) - 1

    monthly_strategy_returns.append(
        portfolio_return
    )

    # Add next month's contribution,
    # except after the final return period.
    if i < len(returns_data) - 1:

        monthly_spy_balance += (
            monthly_spy_contribution
        )

        monthly_tbill_balance += (
            monthly_tbill_contribution
        )

        cumulative_contributions += (
            monthly_contribution
        )

    monthly_portfolio_value = (
        monthly_spy_balance
        + monthly_tbill_balance
    )

    monthly_spy_values.append(
        monthly_spy_balance
    )

    monthly_tbill_values.append(
        monthly_tbill_balance
    )

    monthly_portfolio_values.append(
        monthly_portfolio_value
    )

    monthly_contributions_history.append(
        cumulative_contributions
    )


# --------------------------------------------------
# 20. SAVE MONTHLY STRATEGY RESULTS
# --------------------------------------------------

returns_data["Monthly_SPY"] = (
    monthly_spy_values
)

returns_data["Monthly_TBill"] = (
    monthly_tbill_values
)

returns_data["Monthly_Total"] = (
    monthly_portfolio_values
)

returns_data["Monthly_Contributions"] = (
    monthly_contributions_history
)

returns_data["Monthly_Strategy_Return"] = (
    monthly_strategy_returns
)

final_monthly_value = (
    returns_data["Monthly_Total"].iloc[-1]
)


# ==================================================
# BENCHMARK 1
# 100% SPY LUMP SUM
# ==================================================


# --------------------------------------------------
# 21. LUMP-SUM SPY BENCHMARK
# --------------------------------------------------

benchmark_lump_sum_balance = (
    INITIAL_CAPITAL
)

benchmark_lump_sum_values = []

for date, row in returns_data.iterrows():

    benchmark_lump_sum_balance *= (
        1 + row["SPY_Return"]
    )

    benchmark_lump_sum_values.append(
        benchmark_lump_sum_balance
    )

returns_data["Benchmark_LumpSum"] = (
    benchmark_lump_sum_values
)

final_benchmark_lump_sum = (
    returns_data["Benchmark_LumpSum"].iloc[-1]
)


# ==================================================
# BENCHMARK 2
# 100% SPY MONTHLY CONTRIBUTIONS
# ==================================================


# --------------------------------------------------
# 22. MONTHLY SPY BENCHMARK
# --------------------------------------------------

benchmark_monthly_contribution = (
    INITIAL_CAPITAL / MONTHS
)

# Contribution #1
benchmark_monthly_balance = (
    benchmark_monthly_contribution
)

benchmark_monthly_values = []
benchmark_monthly_contributions = (
    benchmark_monthly_contribution
)

for i, (date, row) in enumerate(
    returns_data.iterrows()
):

    benchmark_monthly_balance *= (
        1 + row["SPY_Return"]
    )

    if i < len(returns_data) - 1:

        benchmark_monthly_balance += (
            benchmark_monthly_contribution
        )

        benchmark_monthly_contributions += (
            benchmark_monthly_contribution
        )

    benchmark_monthly_values.append(
        benchmark_monthly_balance
    )

returns_data["Benchmark_Monthly"] = (
    benchmark_monthly_values
)

final_benchmark_monthly = (
    returns_data["Benchmark_Monthly"].iloc[-1]
)


# ==================================================
# PERFORMANCE METRICS
# ==================================================


# --------------------------------------------------
# 23. ANNUALIZED TIME-WEIGHTED RETURN
# --------------------------------------------------

def annualized_return(monthly_returns):

    total_growth = (
        1 + monthly_returns
    ).prod()

    number_of_months = len(
        monthly_returns
    )

    return (
        total_growth
        ** (12 / number_of_months)
    ) - 1


# --------------------------------------------------
# 24. ANNUALIZED VOLATILITY
# --------------------------------------------------

def annualized_volatility(monthly_returns):

    return (
        monthly_returns.std(ddof=1)
        * np.sqrt(12)
    )


# --------------------------------------------------
# 25. SHARPE RATIO
# --------------------------------------------------

def sharpe_ratio(
    monthly_returns,
    monthly_risk_free_returns
):

    excess_returns = (
        monthly_returns
        - monthly_risk_free_returns
    )

    if excess_returns.std(ddof=1) == 0:
        return np.nan

    return (
        excess_returns.mean()
        / excess_returns.std(ddof=1)
    ) * np.sqrt(12)


# --------------------------------------------------
# 26. MAXIMUM DRAWDOWN
# --------------------------------------------------

def maximum_drawdown(monthly_returns):

    wealth_index = (
        1 + monthly_returns
    ).cumprod()

    running_max = (
        wealth_index.cummax()
    )

    drawdown = (
        wealth_index / running_max
    ) - 1

    return drawdown.min()


# --------------------------------------------------
# 27. CREATE RETURN SERIES
# --------------------------------------------------

lump_sum_return_series = pd.Series(
    returns_data["LumpSum_Return"],
    index=returns_data.index
)

monthly_return_series = pd.Series(
    returns_data["Monthly_Strategy_Return"],
    index=returns_data.index
)

benchmark_return_series = (
    returns_data["SPY_Return"]
)

risk_free_return_series = (
    returns_data["TBill_Return"]
)


# --------------------------------------------------
# 28. CALCULATE METRICS
# --------------------------------------------------

lump_sum_annual_return = annualized_return(
    lump_sum_return_series
)

monthly_annual_return = annualized_return(
    monthly_return_series
)

benchmark_annual_return = annualized_return(
    benchmark_return_series
)


lump_sum_volatility = annualized_volatility(
    lump_sum_return_series
)

monthly_volatility = annualized_volatility(
    monthly_return_series
)

benchmark_volatility = annualized_volatility(
    benchmark_return_series
)


lump_sum_sharpe = sharpe_ratio(
    lump_sum_return_series,
    risk_free_return_series
)

monthly_sharpe = sharpe_ratio(
    monthly_return_series,
    risk_free_return_series
)

benchmark_sharpe = sharpe_ratio(
    benchmark_return_series,
    risk_free_return_series
)


lump_sum_max_drawdown = maximum_drawdown(
    lump_sum_return_series
)

monthly_max_drawdown = maximum_drawdown(
    monthly_return_series
)

benchmark_max_drawdown = maximum_drawdown(
    benchmark_return_series
)


# ==================================================
# SUMMARY TABLE
# ==================================================


# --------------------------------------------------
# 29. CREATE RESULTS SUMMARY
# --------------------------------------------------

summary = pd.DataFrame({

    "Strategy": [
        "50/50 Lump Sum",
        "50/50 Monthly",
        "100% SPY Lump Sum",
        "100% SPY Monthly"
    ],

    "Total Contributions": [
        INITIAL_CAPITAL,
        cumulative_contributions,
        INITIAL_CAPITAL,
        benchmark_monthly_contributions
    ],

    "Final Value": [
        final_lump_sum_value,
        final_monthly_value,
        final_benchmark_lump_sum,
        final_benchmark_monthly
    ],

    "Investment Gain": [
        final_lump_sum_value
        - INITIAL_CAPITAL,

        final_monthly_value
        - cumulative_contributions,

        final_benchmark_lump_sum
        - INITIAL_CAPITAL,

        final_benchmark_monthly
        - benchmark_monthly_contributions
    ],

    "Annualized TWR": [
        lump_sum_annual_return,
        monthly_annual_return,
        benchmark_annual_return,
        benchmark_annual_return
    ],

    "Annualized Volatility": [
        lump_sum_volatility,
        monthly_volatility,
        benchmark_volatility,
        benchmark_volatility
    ],

    "Sharpe Ratio": [
        lump_sum_sharpe,
        monthly_sharpe,
        benchmark_sharpe,
        benchmark_sharpe
    ],

    "Maximum Drawdown": [
        lump_sum_max_drawdown,
        monthly_max_drawdown,
        benchmark_max_drawdown,
        benchmark_max_drawdown
    ]
})


# --------------------------------------------------
# 30. PRINT SUMMARY
# --------------------------------------------------

print("\n")
print("=" * 80)
print("30-YEAR INVESTMENT STRATEGY COMPARISON")
print("=" * 80)

print(
    summary.to_string(
        index=False,
        formatters={
            "Total Contributions":
                lambda x: f"${x:,.2f}",

            "Final Value":
                lambda x: f"${x:,.2f}",

            "Investment Gain":
                lambda x: f"${x:,.2f}",

            "Annualized TWR":
                lambda x: f"{x:.2%}",

            "Annualized Volatility":
                lambda x: f"{x:.2%}",

            "Sharpe Ratio":
                lambda x: f"{x:.2f}",

            "Maximum Drawdown":
                lambda x: f"{x:.2%}"
        }
    )
)

print("=" * 80)


# ==================================================
# SAVE RESULTS
# ==================================================


# --------------------------------------------------
# 31. SAVE DATA TO CSV
# --------------------------------------------------

returns_data.to_csv(
    "portfolio_results.csv"
)

summary.to_csv(
    "summary_results.csv",
    index=False
)


# --------------------------------------------------
# 32. CREATE CHARTS DIRECTORY
# --------------------------------------------------

os.makedirs(
    "charts",
    exist_ok=True
)


# ==================================================
# GRAPH 1
# LUMP SUM ONLY
# ==================================================

plt.figure(figsize=(12, 6))

plt.plot(
    returns_data.index,
    returns_data["LumpSum_Total"],
    label="50/50 Lump Sum"
)

plt.title(
    "50/50 Lump-Sum Portfolio"
)

plt.xlabel("Date")
plt.ylabel("Portfolio Value ($)")

plt.legend()
plt.grid(True)

plt.tight_layout()

plt.savefig(
    "charts/01_lump_sum.png",
    dpi=300
)

plt.show()


# ==================================================
# GRAPH 2
# MONTHLY STRATEGY ONLY
# ==================================================

plt.figure(figsize=(12, 6))

plt.plot(
    returns_data.index,
    returns_data["Monthly_Total"],
    label="50/50 Monthly Investing"
)

plt.title(
    "50/50 Monthly-Contribution Portfolio"
)

plt.xlabel("Date")
plt.ylabel("Portfolio Value ($)")

plt.legend()
plt.grid(True)

plt.tight_layout()

plt.savefig(
    "charts/02_monthly_investing.png",
    dpi=300
)

plt.show()


# ==================================================
# GRAPH 3
# LUMP SUM VS MONTHLY
# ==================================================

plt.figure(figsize=(12, 6))

plt.plot(
    returns_data.index,
    returns_data["LumpSum_Total"],
    label="50/50 Lump Sum"
)

plt.plot(
    returns_data.index,
    returns_data["Monthly_Total"],
    label="50/50 Monthly Investing"
)

plt.title(
    "Lump Sum vs Monthly Investing"
)

plt.xlabel("Date")
plt.ylabel("Portfolio Value ($)")

plt.legend()
plt.grid(True)

plt.tight_layout()

plt.savefig(
    "charts/03_lump_sum_vs_monthly.png",
    dpi=300
)

plt.show()


# ==================================================
# GRAPH 4
# LUMP SUM VS BENCHMARK
# ==================================================

plt.figure(figsize=(12, 6))

plt.plot(
    returns_data.index,
    returns_data["LumpSum_Total"],
    label="50/50 Lump Sum"
)

plt.plot(
    returns_data.index,
    returns_data["Benchmark_LumpSum"],
    label="100% SPY Lump Sum Benchmark"
)

plt.title(
    "Lump-Sum Portfolio vs 100% SPY"
)

plt.xlabel("Date")
plt.ylabel("Portfolio Value ($)")

plt.legend()
plt.grid(True)

plt.tight_layout()

plt.savefig(
    "charts/04_lump_sum_vs_benchmark.png",
    dpi=300
)

plt.show()


# ==================================================
# GRAPH 5
# MONTHLY STRATEGY VS BENCHMARK
# ==================================================

plt.figure(figsize=(12, 6))

plt.plot(
    returns_data.index,
    returns_data["Monthly_Total"],
    label="50/50 Monthly Investing"
)

plt.plot(
    returns_data.index,
    returns_data["Benchmark_Monthly"],
    label="100% SPY Monthly Benchmark"
)

plt.title(
    "Monthly Investing vs 100% SPY"
)

plt.xlabel("Date")
plt.ylabel("Portfolio Value ($)")

plt.legend()
plt.grid(True)

plt.tight_layout()

plt.savefig(
    "charts/05_monthly_vs_benchmark.png",
    dpi=300
)

plt.show()


# ==================================================
# GRAPH 6
# ALL STRATEGIES + BENCHMARKS + SPY PERFORMANCE
# ==================================================

# Normalize SPY performance to the same initial capital
returns_data["SPY_Normalized"] = (
    INITIAL_CAPITAL
    * (1 + returns_data["SPY_Return"]).cumprod()
)


plt.figure(figsize=(12, 6))

plt.plot(
    returns_data.index,
    returns_data["LumpSum_Total"],
    label="50/50 Lump Sum"
)

plt.plot(
    returns_data.index,
    returns_data["Monthly_Total"],
    label="50/50 Monthly Investing"
)

plt.plot(
    returns_data.index,
    returns_data["Benchmark_LumpSum"],
    label="100% SPY Lump Sum Benchmark"
)

plt.plot(
    returns_data.index,
    returns_data["Benchmark_Monthly"],
    label="100% SPY Monthly Benchmark"
)

plt.plot(
    returns_data.index,
    returns_data["SPY_Normalized"],
    label="SPY Market Performance"
)

plt.title(
    "30-Year Investment Strategy Comparison"
)

plt.xlabel("Date")
plt.ylabel("Portfolio Value ($)")

plt.legend()
plt.grid(True)

plt.tight_layout()

plt.savefig(
    "charts/06_all_strategies.png",
    dpi=300
)

plt.show()