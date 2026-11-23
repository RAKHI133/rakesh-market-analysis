import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from pathlib import Path

st.set_page_config(page_title="Portfolio | Rakesh Market Analysis", page_icon="💼", layout="wide")

st.markdown("""
<style>
  .block-container {max-width:1400px;padding-top:1.3rem}
  [data-testid="stAppViewContainer"] {background:#0b1020}
  [data-testid="stHeader"] {background:#0b1020}
  [data-testid="stMetric"] {background:#151f34;border:1px solid #263650;border-radius:14px;padding:14px}
  h1,h2,h3,p,label,span {color:#e4edf8}
</style>
""", unsafe_allow_html=True)

st.title("💼 Portfolio")
st.caption("Your portfolio workspace · Equity holdings and imported Groww F&O performance")

DATA_FILE = Path(__file__).parent / "data" / "groww_fo_trades.csv"
fo = pd.read_csv(DATA_FILE)
fo["Buy Date"] = pd.to_datetime(fo["Buy Date"], errors="coerce")
fo["Sell Date"] = pd.to_datetime(fo["Sell Date"], errors="coerce")
fo_pnl_before = -1470.75
fo_charges = 2902.46
fo_net = -4373.21

@st.cache_data(ttl=30, show_spinner=False)
def get_quotes(tickers):
    if not tickers:
        return {}
    try:
        data = yf.download(list(tickers), period="5d", interval="5m", group_by="ticker",
                           auto_adjust=True, threads=True, progress=False, timeout=8)
    except Exception:
        return {t: None for t in tickers}
    out = {}
    for ticker in tickers:
        try:
            frame = data[ticker] if isinstance(data.columns, pd.MultiIndex) else data
            close = frame["Close"].dropna()
            out[ticker] = float(close.iloc[-1]) if not close.empty else None
        except Exception:
            out[ticker] = None
    return out

st.subheader("F&O performance · Groww import")
st.caption("Imported report period: 28 Sep 2026 – 13 Nov 2026 · 58 closed trades")
a,b,c,d = st.columns(4)
a.metric("Net F&O P&L", f"₹{fo_net:,.2f}", delta=f"After ₹{fo_charges:,.2f} charges", delta_color="inverse")
b.metric("Realised P&L before charges", f"₹{fo_pnl_before:,.2f}")
c.metric("Total charges", f"₹{fo_charges:,.2f}")
d.metric("Win / loss trades", "33 / 24", help="One additional trade was breakeven")
st.caption("Trade turnover: buy ₹1,32,119.75 · sell ₹1,30,649.00. Turnover is cumulative trade value, not unique capital invested.")
with st.expander("Charges breakdown"):
    st.write({"Brokerage": "₹2,200.00", "STT": "₹196.00", "GST": "₹412.24",
              "Exchange transaction charges": "₹89.96", "SEBI charges": "₹0.26",
              "Stamp duty": "₹4.00", "IPFT": "₹0.00"})
f1,f2 = st.columns([1,1])
with f1:
    instruments = ["All"] + sorted(fo["Scrip Name"].dropna().unique().tolist())
    selected = st.selectbox("Filter F&O instrument", instruments)
with f2:
    outcome = st.selectbox("Trade result", ["All", "Profit", "Loss", "Breakeven"])
view = fo.copy()
if selected != "All":
    view = view[view["Scrip Name"] == selected]
if outcome == "Profit":
    view = view[view["Realised P&L"] > 0]
elif outcome == "Loss":
    view = view[view["Realised P&L"] < 0]
elif outcome == "Breakeven":
    view = view[view["Realised P&L"] == 0]
st.dataframe(view.sort_values("Sell Date", ascending=False), use_container_width=True, hide_index=True)
st.download_button("Download imported F&O trades (CSV)", fo.to_csv(index=False).encode("utf-8"),
                   "groww_fo_trades.csv", "text/csv")

st.divider()
st.subheader("Equity holdings · add or import")
st.caption("The uploaded workbook does not contain equity holdings. Add them manually or upload a holdings file with columns: Symbol, Quantity, Average Cost. Use Yahoo Finance tickers such as RELIANCE.NS.")
if "equity_holdings" not in st.session_state:
    st.session_state["equity_holdings"] = []
with st.form("add_equity_holding", clear_on_submit=True):
    x,y,z = st.columns([2,1,1])
    symbol = x.text_input("Yahoo Finance symbol", placeholder="RELIANCE.NS")
    qty = y.number_input("Quantity", min_value=0.0001, value=1.0, step=1.0)
    avg = z.number_input("Average buy price (₹)", min_value=0.01, value=100.0, step=1.0)
    add = st.form_submit_button("Add holding")
if add:
    ticker = symbol.strip().upper()
    if not ticker or not all(ch.isalnum() or ch in ".-^=" for ch in ticker):
        st.error("Enter a valid ticker, for example RELIANCE.NS.")
    else:
        current = st.session_state["equity_holdings"]
        old = next((h for h in current if h["Symbol"] == ticker), None)
        if old:
            new_qty = old["Quantity"] + float(qty)
            old["Average Cost"] = (old["Quantity"]*old["Average Cost"] + float(qty)*float(avg))/new_qty
            old["Quantity"] = new_qty
        else:
            current.append({"Symbol":ticker,"Quantity":float(qty),"Average Cost":float(avg)})
        st.session_state["equity_holdings"] = current
        st.rerun()

upload = st.file_uploader("Import equity holdings CSV or Excel", type=["csv","xlsx"], key="equity_upload")
if upload is not None and st.button("Load uploaded holdings"):
    try:
        imported = pd.read_csv(upload) if upload.name.lower().endswith(".csv") else pd.read_excel(upload)
        imported.columns = [str(c).strip() for c in imported.columns]
        required = {"Symbol","Quantity","Average Cost"}
        if not required.issubset(imported.columns):
            st.error("Required columns: Symbol, Quantity, Average Cost.")
        else:
            clean = imported[list(required)].copy()
            clean["Symbol"] = clean["Symbol"].astype(str).str.strip().str.upper()
            clean["Quantity"] = pd.to_numeric(clean["Quantity"], errors="coerce")
            clean["Average Cost"] = pd.to_numeric(clean["Average Cost"], errors="coerce")
            clean = clean.dropna()
            st.session_state["equity_holdings"] = clean.to_dict("records")
            st.success(f"Loaded {len(clean)} equity holdings.")
            st.rerun()
    except Exception as exc:
        st.error(f"Could not read holdings file: {exc}")

holdings = st.session_state["equity_holdings"]
if holdings:
    quotes = get_quotes(tuple(h["Symbol"] for h in holdings))
    rows = []
    for h in holdings:
        ltp = quotes.get(h["Symbol"])
        invested = float(h["Quantity"])*float(h["Average Cost"])
        value = float(h["Quantity"])*ltp if ltp is not None else np.nan
        pnl = value-invested if pd.notna(value) else np.nan
        rows.append({"Symbol":h["Symbol"],"Quantity":h["Quantity"],"Average Cost":h["Average Cost"],
                     "LTP":ltp,"Invested":invested,"Market Value":value,"Unrealised P&L":pnl})
    pf = pd.DataFrame(rows)
    total_invested = pf["Invested"].sum()
    total_value = pf["Market Value"].sum(min_count=1)
    total_pnl = total_value-total_invested if pd.notna(total_value) else np.nan
    m,n,o = st.columns(3)
    m.metric("Equity invested", f"₹{total_invested:,.2f}")
    n.metric("Equity market value", f"₹{total_value:,.2f}" if pd.notna(total_value) else "Unavailable")
    o.metric("Equity unrealised P&L", f"₹{total_pnl:+,.2f}" if pd.notna(total_pnl) else "Unavailable")
    st.dataframe(pf, use_container_width=True, hide_index=True)
    st.download_button("Download equity holdings backup", pd.DataFrame(holdings).to_csv(index=False),
                       "equity_holdings_backup.csv", "text/csv")
    remove = st.selectbox("Remove holding", ["Select"]+[h["Symbol"] for h in holdings])
    if st.button("Remove selected holding", disabled=remove=="Select"):
        st.session_state["equity_holdings"] = [h for h in holdings if h["Symbol"] != remove]
        st.rerun()
else:
    st.info("No equity holdings imported yet. Your F&O history is already loaded above.")

st.divider()
st.subheader("Portfolio P&L summary")
st.metric("Imported realised F&O P&L after charges", f"₹{fo_net:,.2f}", delta="Historical report only", delta_color="inverse")
st.caption("This is not yet a complete lifetime stock-market P&L. Equity realised trades, deposits/withdrawals, and current holdings were not included in the uploaded F&O report. Equity quotes are indicative Yahoo Finance data and may be delayed. Holdings entered in this page are kept in the current Streamlit session; download the backup to preserve them.")
