import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Rakesh Market Analysis", page_icon="📈", layout="wide")
st_autorefresh(interval=30_000, key="market_refresh")
st.title("🇮🇳 Rakesh Market Analysis")
st.caption(f"India time: {datetime.now(ZoneInfo('Asia/Kolkata')):%d %b %Y, %I:%M:%S %p} IST · Auto-refreshes every 30 seconds")
st.warning("Market prices use Yahoo Finance intraday data where available. It is unofficial, may be delayed or unavailable, and is not guaranteed exchange real-time data. This dashboard is for research and paper trading, not investment advice.")

@st.cache_data(ttl=30, show_spinner=False)
def get_history(symbol, period="6mo", interval="1d"):
    try:
        data = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
        return data.dropna(how="all") if data is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=30, show_spinner=False)
def get_quote(symbol):
    # Prefer intraday bars; fall back to daily closes if intraday data is unavailable.
    d = get_history(symbol, "5d", "5m")
    if not d.empty and "Close" in d:
        c = d.Close.dropna()
        if len(c) >= 2:
            latest = float(c.iloc[-1])
            latest_day = c.index[-1].date()
            prior_day_closes = c[c.index.date < latest_day]
            if not prior_day_closes.empty:
                previous_close = float(prior_day_closes.iloc[-1])
                return latest, latest-previous_close, ((latest/previous_close)-1)*100 if previous_close else 0
            previous = float(c.iloc[-2])
            return latest, latest-previous, ((latest/previous)-1)*100 if previous else 0
    d = get_history(symbol, "5d", "1d")
    if d.empty or "Close" not in d:
        return None
    c = d.Close.dropna()
    if c.empty:
        return None
    last = float(c.iloc[-1])
    prev = float(c.iloc[-2]) if len(c) > 1 else last
    return last, last-prev, ((last/prev)-1)*100 if prev else 0

def rsi(series, n=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100/(1+rs)

symbols = {
    "NIFTY 50":"^NSEI", "NIFTY BANK":"^NSEBANK", "SENSEX":"^BSESN",
    "INDIA VIX":"^INDIAVIX", "S&P 500":"^GSPC", "NASDAQ":"^IXIC",
    "WTI Crude":"CL=F", "USD/INR":"INR=X"
}
st.subheader("Market overview")
cols = st.columns(4)
for i, (name, symbol) in enumerate(symbols.items()):
    q = get_quote(symbol)
    with cols[i % 4]:
        if q:
            st.metric(name, f"{q[0]:,.2f}", f"{q[1]:+,.2f} ({q[2]:+.2f}%)")
        else:
            st.metric(name, "Unavailable")
if st.button("Refresh data"):
    st.cache_data.clear()
    st.rerun()

tabs = st.tabs(["Charts", "Stock scanner", "Options payoff", "FII / DII", "Risk calculator", "Paper journal", "Resources"])

with tabs[0]:
    chart_symbols = {"NIFTY 50":"^NSEI","NIFTY BANK":"^NSEBANK","SENSEX":"^BSESN","RELIANCE":"RELIANCE.NS","HDFCBANK":"HDFCBANK.NS","ICICIBANK":"ICICIBANK.NS","INFY":"INFY.NS","TCS":"TCS.NS","SBIN":"SBIN.NS"}
    instrument = st.selectbox("Instrument", list(chart_symbols))
    period = st.selectbox("Period", ["1d","5d","1mo","3mo","6mo","1y","2y"], index=2)
    interval = st.selectbox("Interval", ["1m","5m","15m","1d"], index=3)
    if period not in ["1d","5d"]:
        interval = "1d"
    d = get_history(chart_symbols[instrument], period, interval)
    if d.empty:
        st.info("No chart data returned. Try another instrument or period.")
    else:
        d["SMA20"] = d.Close.rolling(20).mean()
        d["SMA50"] = d.Close.rolling(50).mean()
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=d.index, open=d.Open, high=d.High, low=d.Low, close=d.Close, name="Price"))
        fig.add_trace(go.Scatter(x=d.index, y=d.SMA20, name="SMA 20"))
        fig.add_trace(go.Scatter(x=d.index, y=d.SMA50, name="SMA 50"))
        fig.update_layout(height=480, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        c1,c2 = st.columns(2)
        with c1: st.line_chart(rsi(d.Close).rename("RSI 14"))
        with c2:
            if "Volume" in d: st.bar_chart(d.Volume)

with tabs[1]:
    st.subheader("Technical scanner")
    raw = st.text_input("Yahoo symbols, comma-separated", "RELIANCE.NS,HDFCBANK.NS,ICICIBANK.NS,INFY.NS,TCS.NS,SBIN.NS,ITC.NS,LT.NS")
    if st.button("Run scanner"):
        rows = []
        for symbol in [x.strip().upper() for x in raw.split(",") if x.strip()]:
            d = get_history(symbol, "6mo")
            if len(d) >= 20:
                c = d.Close.dropna()
                s20 = c.rolling(20).mean().iloc[-1]
                s50 = c.rolling(50).mean().iloc[-1] if len(c) >= 50 else np.nan
                rows.append({"Symbol":symbol,"Close":round(float(c.iloc[-1]),2),"SMA20":round(float(s20),2),"SMA50":round(float(s50),2) if pd.notna(s50) else None,"RSI14":round(float(rsi(c).iloc[-1]),1)})
        if rows:
            result = pd.DataFrame(rows)
            st.dataframe(result, use_container_width=True, hide_index=True)
            st.download_button("Download scanner CSV", result.to_csv(index=False), "scanner.csv", "text/csv")
        else: st.warning("No scanner data returned.")

with tabs[2]:
    st.subheader("Manual options expiry payoff")
    st.caption("Manual estimate only; no live option-chain, premium, Greeks, or IV feed.")
    a,b,c = st.columns(3)
    with a:
        option = st.selectbox("Option type", ["CE (Call)","PE (Put)"])
        strike = st.number_input("Strike", min_value=0.0, value=25000.0, step=50.0)
        premium = st.number_input("Premium per unit (₹)", min_value=0.0, value=150.0)
    with b:
        qty = st.number_input("Quantity / units", min_value=1, value=75)
        low = st.number_input("Scenario low", min_value=0.0, value=24000.0)
        high = st.number_input("Scenario high", min_value=0.0, value=26000.0)
    with c:
        costs = st.number_input("Estimated costs (₹)", min_value=0.0, value=0.0)
    if high > low:
        prices = np.linspace(low, high, 101)
        intrinsic = np.maximum(prices-strike,0) if option.startswith("CE") else np.maximum(strike-prices,0)
        pnl = (intrinsic-premium)*qty-costs
        fig = go.Figure(go.Scatter(x=prices,y=pnl,mode="lines",name="Expiry P/L"))
        fig.add_hline(y=0,line_dash="dash")
        fig.update_layout(height=350,xaxis_title="Underlying at expiry",yaxis_title="Estimated P/L (₹)")
        st.plotly_chart(fig,use_container_width=True)
        st.write(f"Break-even: ₹{(strike+premium if option.startswith('CE') else strike-premium):,.2f}")
        st.write(f"Maximum long-option loss: ₹{premium*qty+costs:,.2f}")
    else: st.error("Scenario high must exceed scenario low.")


@st.cache_data(ttl=900, show_spinner=False)
def fetch_nse_fii_dii():
    import requests
    import re
    session = requests.Session()
    session.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36",
        "Accept":"application/json, text/plain, */*","Referer":"https://www.nseindia.com/reports/fii-dii"})
    session.get("https://www.nseindia.com/", timeout=15)
    response = session.get("https://www.nseindia.com/api/fiidiiTradeReact", timeout=20)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict):
        payload = payload.get("data", payload.get("records", []))
    if not isinstance(payload, list) or not payload:
        raise ValueError("NSE returned no FII/DII records.")
    rows = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        normalized = {re.sub(r"[^a-z0-9]", "", str(k).lower()): v for k, v in item.items()}
        date_value = next((normalized[k] for k in ("date","tradingdate","tradedate") if normalized.get(k)), None)
        if not date_value:
            continue
        dt = pd.to_datetime(date_value, errors="coerce", dayfirst=True)
        if pd.isna(dt):
            continue
        category = str(normalized.get("category", normalized.get("investor", normalized.get("clienttype", "")))).lower()
        buy = next((normalized[k] for k in ("buyvalue","grossbuy","buy","purchasevalue") if k in normalized), None)
        sell = next((normalized[k] for k in ("sellvalue","grosssell","sell","salevalue") if k in normalized), None)
        net = next((normalized[k] for k in ("netvalue","net","netpurchase") if k in normalized), None)
        if buy is None or sell is None or net is None:
            continue
        try:
            values = [float(str(v).replace(",","")) for v in (buy, sell, net)]
        except (TypeError, ValueError):
            continue
        key = dt.strftime("%Y-%m-%d")
        row = rows.setdefault(key, {"date":dt.strftime("%d-%b-%Y"),"date_sort":dt})
        if "fii" in category or "fpi" in category:
            row.update({"fii_buy":values[0],"fii_sell":values[1],"fii_net":values[2]})
        elif "dii" in category:
            row.update({"dii_buy":values[0],"dii_sell":values[1],"dii_net":values[2]})
    records = []
    for row in rows.values():
        if all(k in row for k in ("fii_buy","fii_sell","fii_net","dii_buy","dii_sell","dii_net")):
            records.append(row)
    df = pd.DataFrame(records)
    if df.empty:
        raise ValueError("NSE response format did not contain matching FII and DII rows.")
    return df.sort_values("date_sort", ascending=False).drop_duplicates("date_sort")

@st.cache_data(ttl=900, show_spinner=False)
def fetch_fii_dii():
    try:
        return fetch_nse_fii_dii(), None
    except Exception as e:
        return pd.DataFrame(), str(e)

with tabs[3]:
    st.subheader("FII / DII tracker · NSE")
    st.markdown("[Open NSE official FII/DII report](https://www.nseindia.com/reports/fii-dii)")
    st.caption("Data is fetched only from the NSE FII/DII report API. Daily cash-market data is generally published after market close and may be revised.")
    data, error = fetch_fii_dii()
    if data.empty:
        st.error("NSE FII/DII data is currently unavailable.")
        st.caption(f"NSE error: {error}")
        st.info("Open the official NSE report link above to check the latest published figures. No values are fabricated.")
    else:
        sessions = st.selectbox("History to display", [5, 10, 20], index=0, format_func=lambda x: f"Last {x} trading sessions")
        history = data.head(sessions).copy().sort_values("date_sort")
        latest = data.iloc[0]
        a,b = st.columns(2)
        a.metric("Latest FII/FPI net (₹ crore)", f"{latest.fii_net:,.2f}")
        b.metric("Latest DII net (₹ crore)", f"{latest.dii_net:,.2f}")
        st.caption(f"Source: NSE · Latest available date: {latest.date_sort:%d %b %Y} · {len(history)} trading sessions displayed")
        totals = history[["fii_buy","fii_sell","fii_net","dii_buy","dii_sell","dii_net"]].sum()
        c1,c2,c3 = st.columns(3)
        c1.metric(f"FII net · {len(history)} sessions", f"₹{totals.fii_net:,.2f} Cr")
        c2.metric(f"DII net · {len(history)} sessions", f"₹{totals.dii_net:,.2f} Cr")
        c3.metric("Combined net", f"₹{totals.fii_net + totals.dii_net:,.2f} Cr")
        trend = history.set_index("date_sort")[["fii_net","dii_net"]].rename(columns={"fii_net":"FII/FPI net","dii_net":"DII net"})
        st.line_chart(trend, use_container_width=True)
        table = history[["date","fii_buy","fii_sell","fii_net","dii_buy","dii_sell","dii_net"]].rename(columns={
            "date":"Date","fii_buy":"FII Buy (₹ Cr)","fii_sell":"FII Sell (₹ Cr)","fii_net":"FII Net (₹ Cr)",
            "dii_buy":"DII Buy (₹ Cr)","dii_sell":"DII Sell (₹ Cr)","dii_net":"DII Net (₹ Cr)"
        })
        st.dataframe(table.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)
        st.download_button("Download FII/DII CSV", table.to_csv(index=False), "fii_dii_history.csv", "text/csv")
        if len(history) < sessions:
            st.info(f"NSE returned {len(history)} daily records. No missing sessions are invented.")

with tabs[4]:
    st.subheader("Position sizing and risk")
    a,b = st.columns(2)
    with a:
        capital = st.number_input("Trading capital (₹)", min_value=0.0, value=100000.0, step=5000.0)
        risk_pct = st.slider("Risk per trade (%)", 0.1, 5.0, 1.0, 0.1)
        entry = st.number_input("Entry price (₹)", min_value=0.0, value=500.0)
        stop = st.number_input("Stop-loss price (₹)", min_value=0.0, value=490.0)
    with b:
        target = st.number_input("Target price (₹)", min_value=0.0, value=530.0)
        lot = st.number_input("Quantity step / lot size", min_value=1, value=1)
    if entry > 0 and stop > 0 and entry != stop:
        risk_budget = capital*risk_pct/100
        unit_risk = abs(entry-stop)
        quantity = int(risk_budget/unit_risk)//int(lot)*int(lot)
        st.metric("Risk budget", f"₹{risk_budget:,.2f}")
        st.metric("Indicative quantity", f"{quantity:,}")
        st.metric("Risk at stop", f"₹{quantity*unit_risk:,.2f}")
        st.metric("Reward / risk", f"1 : {abs(target-entry)/unit_risk:.2f}")
    else: st.warning("Enter a positive entry and a different positive stop.")

with tabs[5]:
    st.subheader("Paper trading journal")
    st.caption("Journal is saved on the hosting server's local disk and may not persist reliably across app restarts or redeployments. Download backups.")
    file = Path("paper_trades.csv")
    columns = ["Date","Symbol","Side","Entry","Exit","Quantity","Stop Loss","Notes"]
    try: trades = pd.read_csv(file) if file.exists() else pd.DataFrame(columns=columns)
    except Exception: trades = pd.DataFrame(columns=columns)
    with st.form("paper_trade"):
        a,b,c = st.columns(3)
        with a:
            trade_date = st.date_input("Trade date", date.today())
            symbol = st.text_input("Symbol", "RELIANCE")
            side = st.selectbox("Side", ["BUY","SELL"])
        with b:
            buy = st.number_input("Entry", min_value=0.0, value=0.0)
            sell = st.number_input("Exit (0 if open)", min_value=0.0, value=0.0)
            quantity = st.number_input("Quantity", min_value=1, value=1)
        with c:
            sl = st.number_input("Stop loss", min_value=0.0, value=0.0)
            notes = st.text_input("Notes")
        submitted = st.form_submit_button("Save paper trade")
        if submitted:
            new = pd.DataFrame([{"Date":str(trade_date),"Symbol":symbol.upper(),"Side":side,"Entry":buy,"Exit":sell,"Quantity":quantity,"Stop Loss":sl,"Notes":notes}])
            pd.concat([trades,new], ignore_index=True).to_csv(file,index=False)
            st.success("Paper trade saved on this app instance.")
            st.rerun()
    if not trades.empty:
        view = trades.copy()
        view["P/L before costs"] = np.where(view.Exit>0,(view.Exit-view.Entry)*view.Quantity*np.where(view.Side=="BUY",1,-1),np.nan)
        st.dataframe(view,use_container_width=True,hide_index=True)
        st.download_button("Download paper journal CSV",view.to_csv(index=False),"paper_trades_backup.csv","text/csv")

with tabs[6]:
    st.subheader("Official resources")
    st.caption("Curated links to Indian exchanges, regulators, government departments and financial-market institutions. These links open official websites; they do not automatically provide live data to this dashboard.")
    resource_groups = {
        "Stock Exchanges": {
            "NSE India":"https://www.nseindia.com/",
            "NSE Market Data":"https://www.nseindia.com/market-data",
            "BSE India":"https://www.bseindia.com/",
            "NSE India VIX":"https://www.nseindia.com/market-data/live-market-indices",
        },
        "F&O and Derivatives": {
            "NSE Equity Derivatives":"https://www.nseindia.com/market-data/equity-derivatives",
            "NSE Contract Information":"https://www.nseindia.com/market-data/securities-available-for-trading",
            "NSE Clearing":"https://www.nscclindia.com/",
            "BSE Derivatives":"https://www.bseindia.com/markets/Derivatives/DeriReports/deriReports.aspx",
            "India Clearing Corporation":"https://www.icclindia.com/",
        },
        "Commodities": {
            "Multi Commodity Exchange (MCX)":"https://www.mcxindia.com/",
            "National Commodity & Derivatives Exchange (NCDEX)":"https://www.ncdex.com/",
        },
        "FII/FPI and DII": {
            "NSE FII/DII Activity":"https://www.nseindia.com/reports/fii-dii",
            "NSDL FPI Reports":"https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx",
            "CDSL":"https://www.cdslindia.com/",
            "NSDL":"https://nsdl.co.in/",
        },
        "Corporate Filings and IPOs": {
            "NSE Corporate Filings":"https://www.nseindia.com/companies-listing/corporate-filings-announcements",
            "BSE Corporate Announcements":"https://www.bseindia.com/corporates/ann.html",
            "Ministry of Corporate Affairs":"https://www.mca.gov.in/",
            "SEBI Public Issues and Disclosures":"https://www.sebi.gov.in/",
        },
        "Regulators and Investor Protection": {
            "SEBI":"https://www.sebi.gov.in/",
            "SEBI Investor Portal":"https://investor.sebi.gov.in/",
            "SEBI SCORES Complaints":"https://scores.sebi.gov.in/",
            "SMART ODR":"https://smartodr.in/",
            "IFSCA":"https://www.ifsca.gov.in/",
            "PFRDA":"https://www.pfrda.org.in/",
            "IRDAI":"https://irdai.gov.in/",
            "IEPFA":"https://www.iepf.gov.in/",
        },
        "Banking and Forex": {
            "Reserve Bank of India":"https://www.rbi.org.in/",
            "RBI Database on Indian Economy":"https://data.rbi.org.in/",
            "CCIL":"https://www.ccilindia.com/",
            "Financial Benchmarks India (FBIL)":"https://www.fbil.org.in/",
            "FEDAI":"https://www.fedai.org.in/",
        },
        "Economic Indicators and Government Data": {
            "Ministry of Statistics and Programme Implementation":"https://www.mospi.gov.in/",
            "Ministry of Finance":"https://finmin.gov.in/",
            "Union Budget of India":"https://www.indiabudget.gov.in/",
            "Press Information Bureau":"https://pib.gov.in/",
            "Open Government Data Platform":"https://www.data.gov.in/",
        },
        "Mutual Funds and Depositories": {
            "Association of Mutual Funds in India (AMFI)":"https://www.amfiindia.com/",
            "AMFI NAV":"https://www.amfiindia.com/net-asset-value/nav",
            "National Institute of Securities Markets (NISM)":"https://www.nism.ac.in/",
        },
    }
    search_resource = st.text_input("Search official resources", placeholder="Search NSE, FII, RBI, IPO, mutual funds...")
    for category, resources in resource_groups.items():
        filtered = {name:url for name,url in resources.items() if search_resource.lower() in name.lower() or search_resource.lower() in category.lower()}
        if filtered:
            with st.expander(f"{category} ({len(filtered)})", expanded=bool(search_resource)):
                for label, url in filtered.items():
                    st.markdown(f"- **[{label}]({url})**")
    st.caption(f"{sum(len(items) for items in resource_groups.values())} official resource links across {len(resource_groups)} categories.")
    st.markdown("**Important:** These are links to official institutional websites, not guaranteed live-data feeds or APIs. No broker connection, credentials, or order execution. Options payoff uses manual inputs. Verify prices, expiry dates, lot sizes, and charges with official exchange/broker sources before trading.")
st.divider()
st.caption("Rakesh Market Analysis · Educational research and paper trading only · Not investment advice")
