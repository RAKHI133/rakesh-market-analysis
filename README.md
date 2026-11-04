# Rakesh Market Analysis

A free Streamlit dashboard for Indian-market research and paper trading.

## Features
- Indian and global market overview
- Price charts with SMA and RSI
- Basic technical scanner
- Manual options expiry payoff calculator
- Best-effort retrieval of published NSE FII/FPI and DII daily cash-market figures
- Position sizing and risk calculator
- Paper-trading journal

## Run locally
```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

## Data and risk limitations
Yahoo Finance data accessed through yfinance is unofficial and may be delayed, stale, incomplete, rate-limited, or unavailable. The NSE FII/DII endpoint is best-effort and may be restricted or changed; the figures are published daily cash-market summaries, not live intraday flows. The options calculator uses manually entered values and is not a live option-chain tool.

This project is for educational market research and paper trading only. It does not connect to a broker or place orders. Verify all market data with official exchange sources before making decisions. Nothing here is investment advice.
