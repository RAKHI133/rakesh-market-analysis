import json
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Rakesh Market Analysis", page_icon="📈", layout="wide")

# ---------- Temporary maintenance switch (controlled in Streamlit Cloud Secrets) ----------
try:
    maintenance_mode = st.secrets["app"]["maintenance_mode"]
except (KeyError, FileNotFoundError):
    maintenance_mode = False

if maintenance_mode:
    st.markdown("""
    <div style="max-width:760px;margin:12vh auto 0;padding:3rem 2rem;text-align:center;
                background:linear-gradient(145deg,#152744,#101b30);border:1px solid #2a4261;
                border-radius:20px;color:#f2f6fc;">
      <div style="font-size:3rem;">🛠️</div>
      <h1 style="margin:.6rem 0;">Temporarily under maintenance</h1>
      <p style="color:#b5c5d9;font-size:1.05rem;">
        Rakesh Market Analysis is being updated. Please check back soon.
      </p>
      <p style="color:#8fb8df;font-size:.85rem;">Thank you for your patience.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

st_autorefresh(interval=30_000, key="market_refresh")

# ---------- Theme switch: compact control at the top-right ----------
theme_spacer, theme_control = st.columns([8, 2])
with theme_control:
    is_day_theme = st.toggle("☀️ Day  /  🌙 Night", value=False, key="dashboard_theme")
PLOTLY_TEMPLATE = "plotly_white" if is_day_theme else "plotly_dark"
PLOT_BG = "#ffffff" if is_day_theme else "#101827"

# ---------- Full dashboard theme tokens ----------
if is_day_theme:
    app_bg, surface_bg, sidebar_bg = "#f4f7fb", "#ffffff", "#eaf0f7"
    border_color, text_color, muted_color = "#d6dfeb", "#172338", "#586a82"
    hero_bg = "linear-gradient(115deg,#e3edfb 0%,#f8fbff 58%,#e4f3ef 100%)"
    hero_border, hero_title, hero_sub, accent_color = "#c5d5e8", "#14243b", "#52657e", "#1769aa"
    metric_bg = "linear-gradient(145deg,#ffffff,#f4f7fc)"
    input_bg, hover_bg = "#ffffff", "#e8f0fa"
else:
    app_bg, surface_bg, sidebar_bg = "#0b1020", "#101827", "#10182b"
    border_color, text_color, muted_color = "#263650", "#d9e6f5", "#91a3bb"
    hero_bg = "linear-gradient(115deg,#152744 0%,#101b30 58%,#102a35 100%)"
    hero_border, hero_title, hero_sub, accent_color = "#2a4261", "#f2f6fc", "#b5c5d9", "#7dd3fc"
    metric_bg = "linear-gradient(145deg,#151f34,#111a2b)"
    input_bg, hover_bg = "#111c30", "#1b2a42"

st.markdown(f"""
<style>
  :root {{ color-scheme: {"light" if is_day_theme else "dark"}; --background-color: {app_bg}; --secondary-background-color: {surface_bg}; --text-color: {text_color}; --primary-color: {accent_color}; }}
  html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stMainBlockContainer"], [data-testid="stHeader"], [data-testid="stBottom"] {{ background: {app_bg} !important; color: {text_color} !important; }}
  .block-container {{ max-width: 1480px; padding-top: 1.1rem; padding-bottom: 2.5rem; }}
  [data-testid="stHeader"] {{ background: {app_bg} !important; }}
  [data-testid="stSidebar"], [data-testid="stSidebar"] > div {{ background: {sidebar_bg} !important; border-right: 1px solid {border_color}; }}
  [data-testid="stVerticalBlock"], [data-testid="stHorizontalBlock"] {{ color: {text_color}; }}
  h1, h2, h3, h4, h5, p, label, li, span, small, strong, em, [data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"] {{ color: {text_color}; }}
  h1 {{ font-size: clamp(1.7rem, 3vw, 2.35rem) !important; }}
  [data-testid="stCaptionContainer"], .section-note {{ color: {muted_color} !important; }}
  [data-testid="stMetric"] {{ background: {metric_bg} !important; border: 1px solid {border_color}; border-radius: 14px; padding: 14px 16px; min-height: 112px; }}
  [data-testid="stMetricLabel"] {{ color: {muted_color} !important; }}
  [data-testid="stMetricValue"] {{ color: {text_color} !important; }}
  [data-testid="stMetricDelta"] {{ font-size: .82rem; }}
  [data-testid="stTabs"] button[role="tab"] {{ color: {muted_color} !important; }}
  [data-testid="stTabs"] button[aria-selected="true"] {{ color: {accent_color} !important; }}
  [data-testid="stTabs"] [data-baseweb="tab-highlight"] {{ background: {accent_color} !important; }}
  .hero {{ background: {hero_bg}; border: 1px solid {hero_border}; border-radius: 18px; padding: 1.15rem 1.35rem; margin: .15rem 0 1.1rem; }}
  .hero-kicker {{ color:{accent_color}; text-transform:uppercase; letter-spacing:.13em; font-size:.72rem; font-weight:700; }}
  .hero-title {{ color:{hero_title}; font-size:1.55rem; font-weight:750; margin:.2rem 0; }}
  .hero-sub {{ color:{hero_sub}; font-size:.9rem; }}
  .market-heading {{ color:{text_color}; font-size:1rem; font-weight:700; margin:.85rem 0 .45rem; }}
  [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stDateInput"] input, [data-testid="stTimeInput"] input, [data-testid="stTextArea"] textarea, [data-testid="stSelectbox"] [data-baseweb="select"] > div, [data-testid="stMultiSelect"] [data-baseweb="select"] > div {{ background: {input_bg} !important; color: {text_color} !important; border-color: {border_color} !important; }}
  [data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"], [data-baseweb="select"] [role="option"] {{ background: {surface_bg} !important; color: {text_color} !important; }}
  [data-baseweb="select"] [role="option"]:hover {{ background: {hover_bg} !important; }}
  [data-testid="stExpander"], [data-testid="stForm"], [data-testid="stAlert"], [data-testid="stDataFrame"], [data-testid="stTable"] {{ background: {surface_bg}; border-color: {border_color} !important; }}
  [data-testid="stDataFrame"] {{ border:1px solid {border_color}; border-radius:12px; overflow:hidden; }}
  [data-testid="stButton"] button, [data-testid="stDownloadButton"] button {{ border-radius:10px; border-color:{border_color}; }}
  [data-testid="stToggle"] {{ justify-content:flex-end; }}
  hr {{ border-color:{border_color}; }}
  a {{ color:{accent_color} !important; }}
  [data-testid="stCode"], pre, code {{ background: {surface_bg}; color: {text_color}; }}
</style>
""", unsafe_allow_html=True)

# Live clock runs inside its own browser frame, so it updates every second
# without rerunning the dashboard or changing the 30-second market refresh.
components.html(f"""
<div class="hero">
  <div class="hero-kicker">Personal market terminal · India</div>
  <div class="hero-title">📈 Rakesh Market Analysis</div>
  <div class="hero-sub"><span id="india-live-clock">Loading India time…</span> IST &nbsp;|&nbsp; Market data refreshes every 30 seconds</div>
</div>
<style>
  html, body {{ margin:0; padding:0; background:transparent; }}
  .hero {{ background:{hero_bg}; border:1px solid {hero_border}; border-radius:18px;
           padding:1.15rem 1.35rem; margin:.15rem 0 1.1rem;
           font-family:Arial,sans-serif; box-sizing:border-box; }}
  .hero-kicker {{ color:{accent_color}; text-transform:uppercase; letter-spacing:.13em;
                  font-size:.72rem; font-weight:700; }}
  .hero-title {{ color:{hero_title}; font-size:1.55rem; font-weight:750; margin:.2rem 0; }}
  .hero-sub {{ color:{hero_sub}; font-size:.9rem; }}
</style>
<script>
(function () {{
  const clock = document.getElementById("india-live-clock");
  const dateFormatter = new Intl.DateTimeFormat("en-IN", {{
    timeZone:"Asia/Kolkata", weekday:"long", day:"2-digit", month:"short", year:"numeric"
  }});
  const timeFormatter = new Intl.DateTimeFormat("en-IN", {{
    timeZone:"Asia/Kolkata", hour:"2-digit", minute:"2-digit", second:"2-digit", hour12:true
  }});
  function updateIndiaClock() {{
    const now = new Date();
    clock.textContent = dateFormatter.format(now) + " · " + timeFormatter.format(now);
  }}
  updateIndiaClock();
  setInterval(updateIndiaClock, 1000);
}})();
</script>
""", height=145, scrolling=False)

with st.expander("About market data & important limitations", expanded=False):
    st.info("Market prices use Yahoo Finance intraday data where available. It is unofficial, may be delayed or unavailable, and is not guaranteed exchange real-time data. This dashboard is for research and paper trading, not investment advice.")

@st.cache_data(ttl=30, show_spinner=False)
def get_history(symbol, period="6mo", interval="1d"):
    try:
        data = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
        return data.dropna(how="all") if data is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

symbols = {
    "NIFTY 50":"^NSEI", "NIFTY BANK":"^NSEBANK", "SENSEX":"^BSESN",
    "INDIA VIX":"^INDIAVIX", "S&P 500":"^GSPC", "NASDAQ":"^IXIC", "DOW JONES":"^DJI",
    "Gold (India equivalent)":"GC=F", "Silver (India equivalent)":"SI=F", "USD/INR":"INR=X"
}
# Values are displayed in their native market convention. Index values are points, not currency.
QUOTE_FORMAT = {
    "NIFTY 50": ("", "pts"), "NIFTY BANK": ("", "pts"), "SENSEX": ("", "pts"),
    "INDIA VIX": ("", ""), "S&P 500": ("", "pts"), "NASDAQ": ("", "pts"), "DOW JONES": ("", "pts"),
    "Gold (India equivalent)": ("₹", "/gram"), "Silver (India equivalent)": ("₹", "/gram"),
    "USD/INR": ("₹", "per USD"),
}

@st.cache_data(ttl=25, show_spinner=False)
def get_market_quotes():
    """Fetch all overview instruments together, with a short timeout."""
    try:
        data = yf.download(
            tickers=list(symbols.values()),
            period="5d",
            interval="5m",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
            timeout=8,
        )
        quotes = {}
        for name, symbol in symbols.items():
            try:
                frame = data[symbol] if isinstance(data.columns, pd.MultiIndex) else data
                close = frame["Close"].dropna()
                if len(close) >= 2:
                    latest = float(close.iloc[-1])
                    latest_day = close.index[-1].date()
                    prior = close[close.index.date < latest_day]
                    previous = float(prior.iloc[-1]) if not prior.empty else float(close.iloc[-2])
                    quotes[name] = (latest, latest - previous, ((latest / previous) - 1) * 100 if previous else 0)
                else:
                    quotes[name] = None
            except Exception:
                quotes[name] = None
        # Convert COMEX USD/troy-ounce prices into indicative INR per gram.
        # This is an India-currency equivalent, not a domestic MCX/retail bullion quote.
        fx = quotes.get("USD/INR")
        if fx and fx[0] > 0:
            grams_per_troy_ounce = 31.1034768
            for metal in ("Gold (India equivalent)", "Silver (India equivalent)"):
                q = quotes.get(metal)
                if q:
                    latest_inr_g = q[0] * fx[0] / grams_per_troy_ounce
                    change_inr_g = q[1] * fx[0] / grams_per_troy_ounce
                    quotes[metal] = (latest_inr_g, change_inr_g, q[2])
        return quotes
    except Exception:
        return {name: None for name in symbols}

def rsi(series, n=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100/(1+rs)


@st.cache_data(ttl=25, show_spinner=False)
def get_watchlist_quotes(tickers):
    """Fetch watchlist quotes in one batch; results may be delayed or unavailable."""
    if not tickers:
        return {}
    try:
        data = yf.download(
            tickers=list(tickers),
            period="5d",
            interval="5m",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
            timeout=8,
        )
    except Exception:
        return {ticker: None for ticker in tickers}

    quotes = {}
    for ticker in tickers:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                level0 = data.columns.get_level_values(0)
                level1 = data.columns.get_level_values(1)
                if ticker in level0:
                    frame = data[ticker]
                elif ticker in level1:
                    frame = data.xs(ticker, axis=1, level=1)
                else:
                    quotes[ticker] = None
                    continue
            else:
                frame = data
            close = frame["Close"].dropna()
            if close.empty:
                quotes[ticker] = None
                continue
            latest = float(close.iloc[-1])
            latest_day = close.index[-1].date()
            prior = close[close.index.date < latest_day]
            if not prior.empty:
                previous = float(prior.iloc[-1])
            elif len(close) >= 2:
                previous = float(close.iloc[-2])
            else:
                previous = None
            if previous and previous != 0:
                quotes[ticker] = (latest, latest - previous, (latest / previous - 1) * 100)
            else:
                quotes[ticker] = (latest, None, None)
        except Exception:
            quotes[ticker] = None
    return quotes


def ticker_currency(ticker):
    """Return the native display currency for common Yahoo Finance ticker formats."""
    if ticker.endswith((".NS", ".BO")):
        return "₹"
    if ticker.startswith("^"):
        return ""
    return "$"

st.subheader("Market overview")
st.markdown('<div class="section-note">A quick snapshot of Indian indices, US benchmarks and key macro indicators.</div>', unsafe_allow_html=True)
with st.spinner("Updating market prices..."):
    quotes = get_market_quotes()

def render_market_group(title, names, columns=4):
    st.markdown(f'<div class="market-heading">{title}</div>', unsafe_allow_html=True)
    cols = st.columns(columns)
    for i, name in enumerate(names):
        q = quotes.get(name)
        prefix, suffix = QUOTE_FORMAT.get(name, ("", ""))
        with cols[i % columns]:
            if q:
                value = f"{prefix}{q[0]:,.2f}" + (f" {suffix}" if suffix else "")
                delta = f"{q[1]:+,.2f} ({q[2]:+.2f}%)"
                st.metric(name, value, delta)
            else:
                st.metric(name, "Unavailable")

render_market_group("🇮🇳 Indian markets", ["NIFTY 50", "NIFTY BANK", "SENSEX", "INDIA VIX"])
render_market_group("🇺🇸 US market indices", ["S&P 500", "NASDAQ", "DOW JONES"], columns=3)
render_market_group("🥇 Precious metals · India equivalent", ["Gold (India equivalent)", "Silver (India equivalent)"], columns=2)
render_market_group("💱 Currency", ["USD/INR"], columns=1)
st.caption("Gold and silver are converted to indicative Indian rupees per gram from COMEX USD/troy-ounce futures using the USD/INR rate. These are not verified domestic spot/MCX prices and exclude Indian local premiums, import duty, GST and jeweller making charges. Yahoo Finance data may be delayed, stale or unavailable.")
refresh_col, status_col = st.columns([1, 4])
with refresh_col:
    if st.button("↻ Refresh data now", key="clear_market_data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with status_col:
    st.caption(f"Last page refresh: {datetime.now(ZoneInfo('Asia/Kolkata')):%I:%M:%S %p IST} · Automatic refresh interval: 30 seconds")

tabs = st.tabs(["📊 Charts", "🔎 Stock scanner", "🧮 Options payoff", "🏦 FII / DII", "🛡️ Risk calculator", "📝 Paper journal", "🔗 Resources", "⭐ Watchlists", "🗺️ Market Heatmap", "💼 Portfolio"])

with tabs[0]:
    st.subheader("Price charts")
    st.markdown('<div class="section-note">Explore price history, moving averages, RSI and volume.</div>', unsafe_allow_html=True)
    chart_symbols = {
        # Indian indices
        "NIFTY 50":"^NSEI", "NIFTY BANK":"^NSEBANK", "SENSEX":"^BSESN",
        # Indian equities
        "RELIANCE · Reliance Industries":"RELIANCE.NS",
        "HDFCBANK · HDFC Bank":"HDFCBANK.NS",
        "ICICIBANK · ICICI Bank":"ICICIBANK.NS",
        "INFY · Infosys":"INFY.NS", "TCS · Tata Consultancy Services":"TCS.NS",
        "SBIN · State Bank of India":"SBIN.NS", "ITC · ITC Ltd":"ITC.NS",
        "LT · Larsen & Toubro":"LT.NS", "AXISBANK · Axis Bank":"AXISBANK.NS",
        "KOTAKBANK · Kotak Mahindra Bank":"KOTAKBANK.NS",
        "BAJFINANCE · Bajaj Finance":"BAJFINANCE.NS",
        "TATAMOTORS · Tata Motors":"TATAMOTORS.NS",
        "MARUTI · Maruti Suzuki":"MARUTI.NS",
        "SUNPHARMA · Sun Pharma":"SUNPHARMA.NS",
        "BHARTIARTL · Bharti Airtel":"BHARTIARTL.NS",
        "HINDUNILVR · Hindustan Unilever":"HINDUNILVR.NS",
        "ADANIENT · Adani Enterprises":"ADANIENT.NS",
        "ONGC · Oil & Natural Gas Corp":"ONGC.NS",
        "POWERGRID · Power Grid":"POWERGRID.NS",
        "TATASTEEL · Tata Steel":"TATASTEEL.NS",
        "WIPRO · Wipro":"WIPRO.NS", "HCLTECH · HCL Technologies":"HCLTECH.NS",
        "ASIANPAINT · Asian Paints":"ASIANPAINT.NS", "NTPC · NTPC":"NTPC.NS",
        "BEL · Bharat Electronics":"BEL.NS", "TRENT · Trent":"TRENT.NS",
        "ADANIPORTS · Adani Ports":"ADANIPORTS.NS",
        "ADANIGREEN · Adani Green Energy":"ADANIGREEN.NS",
        "AMBUJACEM · Ambuja Cements":"AMBUJACEM.NS",
        "APOLLOHOSP · Apollo Hospitals":"APOLLOHOSP.NS",
        "AUROPHARMA · Aurobindo Pharma":"AUROPHARMA.NS",
        "ABB · ABB India":"ABB.NS",
        "ABCAPITAL · Aditya Birla Capital":"ABCAPITAL.NS",
        "BANKBARODA · Bank of Baroda":"BANKBARODA.NS",
        "BHEL · Bharat Heavy Electricals":"BHEL.NS",
        "CANBK · Canara Bank":"CANBK.NS",
        "CHOLAFIN · Cholamandalam Finance":"CHOLAFIN.NS",
        "CIPLA · Cipla":"CIPLA.NS",
        "COALINDIA · Coal India":"COALINDIA.NS",
        "COLPAL · Colgate-Palmolive India":"COLPAL.NS",
        "DABUR · Dabur India":"DABUR.NS",
        "DIVISLAB · Divi's Laboratories":"DIVISLAB.NS",
        "DLF · DLF":"DLF.NS",
        "DMART · Avenue Supermarts":"DMART.NS",
        "EICHERMOT · Eicher Motors":"EICHERMOT.NS",
        "FEDERALBNK · Federal Bank":"FEDERALBNK.NS",
        "GODREJCP · Godrej Consumer Products":"GODREJCP.NS",
        "GRASIM · Grasim Industries":"GRASIM.NS",
        "HAL · Hindustan Aeronautics":"HAL.NS",
        "HEROMOTOCO · Hero MotoCorp":"HEROMOTOCO.NS",
        "INDHOTEL · Indian Hotels":"INDHOTEL.NS",
        "INDUSINDBK · IndusInd Bank":"INDUSINDBK.NS",
        "IOC · Indian Oil":"IOC.NS",
        "IRCTC · IRCTC":"IRCTC.NS",
        "JSWSTEEL · JSW Steel":"JSWSTEEL.NS",
        "JINDALSTEL · Jindal Steel & Power":"JINDALSTEL.NS",
        "LICI · Life Insurance Corporation":"LICI.NS",
        "M&M · Mahindra & Mahindra":"M&M.NS",
        "MOTHERSON · Samvardhana Motherson":"MOTHERSON.NS",
        "PIDILITIND · Pidilite Industries":"PIDILITIND.NS",
        "PNB · Punjab National Bank":"PNB.NS",
        "PERSISTENT · Persistent Systems":"PERSISTENT.NS",
        "POLYCAB · Polycab India":"POLYCAB.NS",
        "RECLTD · REC Limited":"RECLTD.NS",
        "SBILIFE · SBI Life Insurance":"SBILIFE.NS",
        "SHRIRAMFIN · Shriram Finance":"SHRIRAMFIN.NS",
        "TATACONSUM · Tata Consumer Products":"TATACONSUM.NS",
        "TECHM · Tech Mahindra":"TECHM.NS",
        "TITAN · Titan Company":"TITAN.NS",
        "ULTRACEMCO · UltraTech Cement":"ULTRACEMCO.NS",
        "UNIONBANK · Union Bank of India":"UNIONBANK.NS",
        "VEDL · Vedanta":"VEDL.NS",
        "ZOMATO · Eternal (formerly Zomato)":"ETERNAL.NS",
        "APLAPOLLO · APL Apollo Tubes":"APLAPOLLO.NS",
        "ATGL · Adani Total Gas":"ATGL.NS",
        "BALKRISIND · Balkrishna Industries":"BALKRISIND.NS",
        "BERGEPAINT · Berger Paints":"BERGEPAINT.NS",
        "BIOCON · Biocon":"BIOCON.NS",
        "BOSCHLTD · Bosch":"BOSCHLTD.NS",
        "BRITANNIA · Britannia Industries":"BRITANNIA.NS",
        "CUMMINSIND · Cummins India":"CUMMINSIND.NS",
        "ESCORTS · Escorts Kubota":"ESCORTS.NS",
        "EXIDEIND · Exide Industries":"EXIDEIND.NS",
        "GAIL · GAIL India":"GAIL.NS",
        "GLENMARK · Glenmark Pharmaceuticals":"GLENMARK.NS",
        "HAVELLS · Havells India":"HAVELLS.NS",
        "ICICIGI · ICICI Lombard":"ICICIGI.NS",
        "IDFCFIRSTB · IDFC First Bank":"IDFCFIRSTB.NS",
        "INDIGO · InterGlobe Aviation":"INDIGO.NS",
        "LUPIN · Lupin":"LUPIN.NS",
        "MANKIND · Mankind Pharma":"MANKIND.NS",
        "MAXHEALTH · Max Healthcare":"MAXHEALTH.NS",
        "MPHASIS · Mphasis":"MPHASIS.NS",
        "NAUKRI · Info Edge":"NAUKRI.NS",
        "NMDC · NMDC":"NMDC.NS",
        "PETRONET · Petronet LNG":"PETRONET.NS",
        "PFC · Power Finance Corporation":"PFC.NS",
        "PIIND · PI Industries":"PIIND.NS",
        "RBLBANK · RBL Bank":"RBLBANK.NS",
        "SAIL · Steel Authority of India":"SAIL.NS",
        "SUPREMEIND · Supreme Industries":"SUPREMEIND.NS",
        "TVSMOTOR · TVS Motor":"TVSMOTOR.NS",
        "VBL · Varun Beverages":"VBL.NS",
        "YESBANK · Yes Bank":"YESBANK.NS",
        # Precious metals only (Yahoo Finance continuous COMEX futures)
        "Gold Futures (COMEX)":"GC=F", "Silver Futures (COMEX)":"SI=F"
    }
    instrument = st.selectbox("Instrument", list(chart_symbols))
    chart_symbol = chart_symbols[instrument]
    if chart_symbol.endswith((".NS", ".BO")):
        chart_currency = "₹"
        currency_label = "INR (₹)"
    elif chart_symbol.startswith("^"):
        chart_currency = ""
        currency_label = "index points"
    else:
        chart_currency = "$"
        currency_label = "USD ($)"
    st.caption("Selected instrument: " + instrument + " · Display currency: " + currency_label)
    period = st.selectbox("Period", ["1d","5d","1mo","3mo","6mo","1y","2y"], index=2)
    interval = st.selectbox("Interval", ["1m","5m","15m","1d"], index=3)
    if period not in ["1d","5d"]:
        interval = "1d"
    chart_key = (chart_symbol, period, interval)
    if st.button("Load chart", key="load_chart"):
        with st.spinner("Loading chart data..."):
            chart_frame = get_history(*chart_key)
        st.session_state["chart_data"] = (chart_key, chart_frame)
    saved_chart = st.session_state.get("chart_data")
    if saved_chart and saved_chart[0] == chart_key:
        d = saved_chart[1].copy()
        if d.empty:
            st.info("No chart data returned. Try another instrument or period.")
        else:
            d["SMA20"] = d.Close.rolling(20).mean()
            d["SMA50"] = d.Close.rolling(50).mean()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=d.index, y=d.Close, mode="lines", name="Price", line=dict(width=2.5)))
            fig.add_trace(go.Scatter(x=d.index, y=d.SMA20, name="SMA 20"))
            fig.add_trace(go.Scatter(x=d.index, y=d.SMA50, name="SMA 50"))
            fig.update_layout(height=480, xaxis_rangeslider_visible=False, template=PLOTLY_TEMPLATE, paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG, yaxis_tickprefix=chart_currency, margin=dict(l=12,r=12,t=35,b=12), legend=dict(orientation="h", y=1.02))
            st.plotly_chart(fig, use_container_width=True)
            c1,c2 = st.columns(2)
            with c1: st.line_chart(rsi(d.Close).rename("RSI 14"))
            with c2:
                if "Volume" in d: st.bar_chart(d.Volume)
    else:
        st.info("Choose an instrument and click Load chart to retrieve its data.")

with tabs[1]:
    st.subheader("Technical scanner")
    st.markdown('<div class="section-note">Compare selected symbols using the existing SMA and RSI checks.</div>', unsafe_allow_html=True)
    scanner_presets = {
        "Indian large caps": "RELIANCE.NS,HDFCBANK.NS,ICICIBANK.NS,INFY.NS,TCS.NS,SBIN.NS,ITC.NS,LT.NS",
        "Custom symbols": ""
    }
    scanner_preset = st.radio("Watchlist preset", list(scanner_presets), horizontal=True)
    raw = st.text_input("Yahoo symbols, comma-separated", scanner_presets[scanner_preset], key="scanner_symbols_" + scanner_preset)
    st.caption("Use Yahoo Finance ticker format. Indian equities usually end in .NS or .BO; US stocks use tickers such as AAPL and NVDA.")
    if st.button("Run scanner"):
        rows = []
        for symbol in [x.strip().upper() for x in raw.split(",") if x.strip()]:
            d = get_history(symbol, "6mo")
            if len(d) >= 20:
                c = d.Close.dropna()
                s20 = c.rolling(20).mean().iloc[-1]
                s50 = c.rolling(50).mean().iloc[-1] if len(c) >= 50 else np.nan
                last_close = float(c.iloc[-1])
                if symbol.endswith((".NS", ".BO")):
                    currency = "₹"
                elif symbol.startswith("^"):
                    currency = ""
                else:
                    currency = "$"
                if pd.notna(s50) and last_close > s20 > s50:
                    trend = "Bullish trend"
                elif pd.notna(s50) and last_close < s20 < s50:
                    trend = "Bearish trend"
                else:
                    trend = "Mixed / neutral"
                rows.append({"Symbol":symbol,"Price":f"{currency}{last_close:,.2f}","SMA20":f"{currency}{float(s20):,.2f}","SMA50":f"{currency}{float(s50):,.2f}" if pd.notna(s50) else "—","RSI14":round(float(rsi(c).iloc[-1]),1),"Trend":trend})
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
        fig.update_layout(height=350,xaxis_title="Underlying at expiry",yaxis_title="Estimated P/L (₹)",template=PLOTLY_TEMPLATE,paper_bgcolor=PLOT_BG,plot_bgcolor=PLOT_BG)
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
    session.get("https://www.nseindia.com/", timeout=4)
    response = session.get("https://www.nseindia.com/api/fiidiiTradeReact", timeout=6)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict):
        payload = payload.get("data", payload.get("records", []))
    if not isinstance(payload, list) or not payload:
        raise ValueError("NSE returned no FII/DII records.")

    rows = {}
    def number(value):
        try:
            return float(str(value).replace(",", "").replace("₹", "").strip())
        except (TypeError, ValueError):
            return None

    for item in payload:
        if not isinstance(item, dict):
            continue
        normalized = {re.sub(r"[^a-z0-9]", "", str(k).lower()): v for k, v in item.items()}
        date_value = next((normalized[k] for k in ("date", "tradingdate", "tradedate") if normalized.get(k)), None)
        if not date_value:
            continue
        dt = pd.to_datetime(date_value, errors="coerce", dayfirst=True)
        if pd.isna(dt):
            continue
        key = dt.strftime("%Y-%m-%d")

        # NSE's combined response contains FII and DII fields in each daily record.
        combined_aliases = {
            "fii_buy": ("fiibuy", "fiibuyvalue", "fiigrossbuy"),
            "fii_sell": ("fiisell", "fiisellvalue", "fiigrosssell"),
            "fii_net": ("fiinet", "fiinetvalue"),
            "dii_buy": ("diibuy", "diibuyvalue", "diigrossbuy"),
            "dii_sell": ("diisell", "diisellvalue", "diigrosssell"),
            "dii_net": ("diinet", "diinetvalue"),
        }
        combined = {
            target: number(next((normalized[name] for name in aliases if normalized.get(name) is not None), None))
            for target, aliases in combined_aliases.items()
        }
        if all(value is not None for value in combined.values()):
            rows[key] = {"date": dt.strftime("%d-%b-%Y"), "date_sort": dt, **combined}
            continue

        # Backward-compatible parsing for NSE responses split into FII and DII category rows.
        category = str(normalized.get("category", normalized.get("investor", normalized.get("clienttype", "")))).lower()
        buy = next((normalized[k] for k in ("buyvalue", "grossbuy", "buy", "purchasevalue") if k in normalized), None)
        sell = next((normalized[k] for k in ("sellvalue", "grosssell", "sell", "salevalue") if k in normalized), None)
        net = next((normalized[k] for k in ("netvalue", "net", "netpurchase") if k in normalized), None)
        values = [number(v) for v in (buy, sell, net)]
        if any(value is None for value in values):
            continue
        row = rows.setdefault(key, {"date": dt.strftime("%d-%b-%Y"), "date_sort": dt})
        if "fii" in category or "fpi" in category:
            row.update({"fii_buy": values[0], "fii_sell": values[1], "fii_net": values[2]})
        elif "dii" in category:
            row.update({"dii_buy": values[0], "dii_sell": values[1], "dii_net": values[2]})

    required = ("fii_buy", "fii_sell", "fii_net", "dii_buy", "dii_sell", "dii_net")
    records = [row for row in rows.values() if all(row.get(field) is not None for field in required)]
    df = pd.DataFrame(records)
    if df.empty:
        raise ValueError("NSE response did not contain complete daily FII and DII records.")
    return df.sort_values("date_sort", ascending=False).drop_duplicates("date_sort").reset_index(drop=True)

@st.cache_data(ttl=900, show_spinner=False)
def fetch_fii_dii():
    try:
        return fetch_nse_fii_dii(), None
    except Exception as e:
        return pd.DataFrame(), str(e)

with tabs[3]:
    st.subheader("FII / DII tracker · NSE")
    st.markdown("[Open NSE official FII/DII report](https://www.nseindia.com/reports/fii-dii)")
    st.caption("NSE-only daily cash-market data. This is separate from live intraday prices and is generally published after market close.")
    if "fii_dii_data" not in st.session_state:
        st.info("Load FII/DII history when you need it. Keeping this request on-demand helps the dashboard open faster.")
    if st.button("Load / refresh NSE FII/DII data"):
        with st.spinner("Requesting the latest available NSE FII/DII report..."):
            data, error = fetch_fii_dii()
        st.session_state["fii_dii_data"] = data
        st.session_state["fii_dii_error"] = error
    if "fii_dii_data" in st.session_state:
        data = st.session_state["fii_dii_data"]
        error = st.session_state.get("fii_dii_error")
        if data.empty:
            st.error("NSE FII/DII data is currently unavailable.")
            st.caption(f"NSE error: {error}")
            st.info("Open the official NSE report link above to check the latest published figures. No values are fabricated.")
        else:
            # Show the latest five trading sessions (one trading week), one row per day.
            history = data.head(5).copy().sort_values("date_sort")
            latest = data.iloc[0]
            a,b = st.columns(2)
            a.metric("Latest FII/FPI net (₹ crore)", f"{latest.fii_net:,.2f}")
            b.metric("Latest DII net (₹ crore)", f"{latest.dii_net:,.2f}")
            st.caption(f"Source: NSE · Latest available date: {latest.date_sort:%d %b %Y} · Showing the latest {len(history)} trading sessions (one week)")
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
            st.caption("Each row represents one trading day. Values are in ₹ crore; weekends and market holidays are excluded. Showing the latest five available trading sessions.")

with tabs[4]:
    st.subheader("Position sizing and risk")
    st.markdown('<div class="section-note">Estimate position size from capital, stop distance and chosen risk.</div>', unsafe_allow_html=True)
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
with tabs[7]:
    st.subheader("⭐ Favourite stocks & watchlists")
    st.markdown('<div class="section-note">Keep your preferred Indian and US symbols together and review their latest available quotes.</div>', unsafe_allow_html=True)

    starter_watchlists = {
        "India starter": ["RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "TCS.NS"],
    }
    if "personal_watchlists" not in st.session_state:
        st.session_state["personal_watchlists"] = {name: tickers.copy() for name, tickers in starter_watchlists.items()}

    watchlists = st.session_state["personal_watchlists"]
    if not watchlists:
        watchlists["My Watchlist"] = []

    top_left, top_right = st.columns([3, 2])
    with top_left:
        active_watchlist = st.selectbox("Select watchlist", list(watchlists.keys()), key="active_watchlist")
    with top_right:
        st.metric("Saved symbols in this list", len(watchlists.get(active_watchlist, [])))

    with st.form("create_watchlist_form", clear_on_submit=True):
        new_name_col, create_col = st.columns([3, 1])
        with new_name_col:
            new_watchlist_name = st.text_input("Create a watchlist", placeholder="Example: Swing trades")
        with create_col:
            st.markdown("<div style='height: 1.85rem'></div>", unsafe_allow_html=True)
            create_submitted = st.form_submit_button("＋ Create", use_container_width=True)
        if create_submitted:
            clean_name = new_watchlist_name.strip()
            if not clean_name:
                st.warning("Enter a name for the new watchlist.")
            elif clean_name in watchlists:
                st.warning("A watchlist with that name already exists.")
            elif len(clean_name) > 32:
                st.warning("Keep watchlist names within 32 characters.")
            else:
                watchlists[clean_name] = []
                st.session_state["personal_watchlists"] = watchlists
                st.success(f"Created {clean_name}.")
                st.rerun()

    with st.form("add_watchlist_symbol_form", clear_on_submit=True):
        add_symbol_col, add_button_col = st.columns([3, 1])
        with add_symbol_col:
            new_ticker = st.text_input("Add a stock symbol", placeholder="RELIANCE.NS, AAPL, MSFT")
        with add_button_col:
            st.markdown("<div style='height: 1.85rem'></div>", unsafe_allow_html=True)
            add_submitted = st.form_submit_button("＋ Add stock", use_container_width=True)
        if add_submitted:
            ticker = new_ticker.strip().upper()
            valid_ticker = bool(ticker) and len(ticker) <= 24 and all(ch.isalnum() or ch in ".-^=" for ch in ticker)
            if not valid_ticker:
                st.warning("Enter one valid Yahoo Finance ticker, for example RELIANCE.NS or AAPL.")
            elif ticker in watchlists[active_watchlist]:
                st.info(f"{ticker} is already in {active_watchlist}.")
            else:
                watchlists[active_watchlist].append(ticker)
                st.session_state["personal_watchlists"] = watchlists
                st.success(f"Added {ticker} to {active_watchlist}.")
                st.rerun()

    current_tickers = watchlists.get(active_watchlist, [])
    manage_left, manage_right = st.columns([3, 1])
    with manage_left:
        remove_ticker = st.selectbox("Remove a symbol", ["Select a symbol"] + current_tickers, key="remove_watchlist_ticker")
    with manage_right:
        st.markdown("<div style='height: 1.85rem'></div>", unsafe_allow_html=True)
        if st.button("Remove", use_container_width=True, disabled=remove_ticker == "Select a symbol"):
            watchlists[active_watchlist].remove(remove_ticker)
            st.session_state["personal_watchlists"] = watchlists
            st.session_state.pop("remove_watchlist_ticker", None)
            st.rerun()

    st.markdown("#### Live watchlist snapshot")
    if current_tickers:
        with st.spinner("Loading watchlist quotes..."):
            watchlist_quotes = get_watchlist_quotes(tuple(current_tickers))
        watchlist_rows = []
        for ticker in current_tickers:
            quote = watchlist_quotes.get(ticker)
            currency = ticker_currency(ticker)
            if quote:
                price = f"{currency}{quote[0]:,.2f}"
                change = f"{currency}{quote[1]:+,.2f}" if quote[1] is not None else "—"
                change_pct = f"{quote[2]:+.2f}%" if quote[2] is not None else "—"
                status = "Quote available"
            else:
                price, change, change_pct, status = "Unavailable", "—", "—", "No quote returned"
            market = "India" if ticker.endswith((".NS", ".BO")) else ("Index" if ticker.startswith("^") else "US / international")
            watchlist_rows.append({
                "Symbol": ticker,
                "Market": market,
                "Last price": price,
                "Change": change,
                "Change %": change_pct,
                "Data status": status,
            })
        st.dataframe(pd.DataFrame(watchlist_rows), use_container_width=True, hide_index=True)
        st.caption("Watchlist quotes use the existing Yahoo Finance source and may be delayed, stale or unavailable. The dashboard refreshes every 30 seconds; watchlist quotes are cached for up to 25 seconds.")
    else:
        st.info("This watchlist is empty. Add a ticker above to start tracking it.")

    with st.expander("Backup and restore watchlists"):
        st.caption("Watchlists are held in this active Streamlit session. Download a JSON backup to keep them, then upload that file to restore them in a later session.")
        watchlist_json = json.dumps(watchlists, indent=2)
        st.download_button(
            "Download watchlists backup",
            data=watchlist_json,
            file_name="rakesh_market_watchlists.json",
            mime="application/json",
            use_container_width=True,
        )
        uploaded_watchlists = st.file_uploader("Restore watchlists from JSON", type=["json"], key="watchlist_restore_upload")
        if uploaded_watchlists is not None and st.button("Restore uploaded watchlists", key="restore_watchlists_button"):
            try:
                restored = json.loads(uploaded_watchlists.getvalue().decode("utf-8"))
                if not isinstance(restored, dict) or not restored:
                    raise ValueError("The file must contain a non-empty object of watchlist names and ticker lists.")
                cleaned = {}
                for name, tickers in restored.items():
                    if not isinstance(name, str) or not name.strip() or not isinstance(tickers, list):
                        raise ValueError("Each watchlist must have a name and a list of ticker symbols.")
                    clean_tickers = []
                    for item in tickers:
                        ticker = str(item).strip().upper()
                        if ticker and len(ticker) <= 24 and all(ch.isalnum() or ch in ".-^=" for ch in ticker) and ticker not in clean_tickers:
                            clean_tickers.append(ticker)
                    cleaned[name.strip()[:32]] = clean_tickers
                if not cleaned:
                    raise ValueError("No valid watchlists were found.")
                st.session_state["personal_watchlists"] = cleaned
                st.success("Watchlists restored successfully.")
                st.rerun()
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
                st.error(f"Could not restore this backup: {error}")

    with st.expander("Delete a watchlist"):
        deletable_lists = list(watchlists.keys())
        if len(deletable_lists) > 1:
            list_to_delete = st.selectbox("Choose a watchlist to delete", deletable_lists, key="delete_watchlist_choice")
            if st.button("Delete selected watchlist", key="delete_watchlist_button"):
                del watchlists[list_to_delete]
                st.session_state["personal_watchlists"] = watchlists
                st.session_state.pop("active_watchlist", None)
                st.session_state.pop("remove_watchlist_ticker", None)
                st.session_state.pop("delete_watchlist_choice", None)
                st.rerun()
        else:
            st.caption("Keep at least one watchlist. You can remove all its symbols instead.")

# ---------- Market heatmap: free Yahoo Finance quotes ----------
with tabs[8]:
    st.subheader("Market heatmap")
    st.caption("Equal-sized tiles coloured by latest percentage move. Yahoo Finance quotes may be delayed.")
    groups = {
        "Banking": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS"],
        "IT": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"],
        "Energy": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS"],
        "Auto": ["MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS"],
        "FMCG": ["ITC.NS", "HINDUNILVR.NS", "TATACONSUM.NS", "NESTLEIND.NS"],
        "Pharma": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS"],
    }
    heat_symbols = [s for values in groups.values() for s in values]
    if st.button("Load / refresh market heatmap", key="load_market_heatmap"):
        with st.spinner("Loading market moves..."):
            st.session_state["heatmap_quotes"] = get_watchlist_quotes(tuple(heat_symbols))
    if "heatmap_quotes" in st.session_state:
        qmap = st.session_state["heatmap_quotes"]
        rows = []
        for sector, names in groups.items():
            for symbol in names:
                q = qmap.get(symbol)
                if q and q[2] is not None:
                    rows.append({"Sector": sector, "Symbol": symbol.replace(".NS", ""), "Change %": float(q[2]), "Price": float(q[0])})
        if rows:
            heat = pd.DataFrame(rows)
            fig_heat = go.Figure(go.Treemap(
                labels=heat["Symbol"], parents=heat["Sector"],
                ids=heat["Sector"] + "/" + heat["Symbol"], values=np.ones(len(heat)),
                marker=dict(colors=heat["Change %"], colorscale=[[0, "#b91c1c"], [0.5, "#263650"], [1, "#047857"]], cmid=0, colorbar=dict(title="Change %")),
                customdata=heat[["Change %", "Price"]].to_numpy(),
                hovertemplate="<b>%{label}</b><br>Change: %{customdata[0]:+.2f}%<br>Price: %{customdata[1]:,.2f}<extra></extra>"
            ))
            fig_heat.update_layout(height=500, template=PLOTLY_TEMPLATE, paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG, margin=dict(l=8,r=8,t=20,b=8))
            st.plotly_chart(fig_heat, use_container_width=True)
            st.dataframe(heat.sort_values("Change %", ascending=False), use_container_width=True, hide_index=True)
            st.caption("Tile sizes are equal; colour represents percentage change. Only symbols with available quotes are shown.")
        else:
            st.warning("No usable quotes returned. Try refreshing later.")
    else:
        st.info("Load the heatmap when needed. Data is fetched on demand to keep startup fast.")


# ---------- Portfolio analytics: session holdings and CSV backup ----------
with tabs[9]:
    st.subheader("Portfolio analytics")
    st.caption("Manually entered holdings valued using available Yahoo Finance quotes. Not connected to a broker.")
    columns = ["Symbol", "Quantity", "Average Cost"]
    if "portfolio_holdings" not in st.session_state:
        st.session_state["portfolio_holdings"] = []
    with st.form("portfolio_add_holding", clear_on_submit=True):
        a, b, d = st.columns([2, 1, 1])
        symbol = a.text_input("Yahoo Finance symbol", placeholder="RELIANCE.NS or AAPL")
        quantity = b.number_input("Quantity", min_value=0.0001, value=1.0, step=1.0)
        avg_cost = d.number_input("Average buy price", min_value=0.01, value=100.0, step=1.0)
        submitted = st.form_submit_button("Add holding")
        if submitted:
            ticker = symbol.strip().upper()
            valid = bool(ticker) and len(ticker) <= 24 and all(ch.isalnum() or ch in ".-^=" for ch in ticker)
            if not valid:
                st.warning("Enter a valid symbol such as RELIANCE.NS or AAPL.")
            else:
                holdings = st.session_state["portfolio_holdings"]
                old = next((x for x in holdings if x["Symbol"] == ticker), None)
                if old:
                    total_qty = float(old["Quantity"]) + float(quantity)
                    old["Average Cost"] = (float(old["Quantity"]) * float(old["Average Cost"]) + float(quantity) * float(avg_cost)) / total_qty
                    old["Quantity"] = total_qty
                else:
                    holdings.append({"Symbol": ticker, "Quantity": float(quantity), "Average Cost": float(avg_cost)})
                st.session_state["portfolio_holdings"] = holdings
                st.rerun()
    holdings = st.session_state["portfolio_holdings"]
    if holdings:
        quote_map = get_watchlist_quotes(tuple(x["Symbol"] for x in holdings))
        rows = []
        for holding in holdings:
            quote = quote_map.get(holding["Symbol"])
            price = float(quote[0]) if quote else np.nan
            invested = float(holding["Quantity"]) * float(holding["Average Cost"])
            value = float(holding["Quantity"]) * price if pd.notna(price) else np.nan
            pnl = value - invested if pd.notna(value) else np.nan
            rows.append({"Symbol": holding["Symbol"], "Quantity": holding["Quantity"], "Average Cost": holding["Average Cost"],
                         "Latest Price": price, "Invested": invested, "Market Value": value, "Unrealized P/L": pnl,
                         "Return %": pnl / invested * 100 if pd.notna(pnl) and invested else np.nan})
        pf = pd.DataFrame(rows)
        invested_total = pf["Invested"].sum()
        value_total = pf["Market Value"].sum(min_count=1)
        pnl_total = value_total - invested_total if pd.notna(value_total) else np.nan
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Invested", f"₹{invested_total:,.2f}")
        m2.metric("Quoted value", f"₹{value_total:,.2f}" if pd.notna(value_total) else "Unavailable")
        m3.metric("Unrealized P/L", f"₹{pnl_total:+,.2f}" if pd.notna(pnl_total) else "Unavailable")
        m4.metric("Return", f"{pnl_total / invested_total * 100:+.2f}%" if pd.notna(pnl_total) and invested_total else "Unavailable")
        st.dataframe(pf, use_container_width=True, hide_index=True)
        alloc = pf.dropna(subset=["Market Value"])
        if not alloc.empty and alloc["Market Value"].sum() > 0:
            fig_alloc = go.Figure(go.Pie(labels=alloc["Symbol"], values=alloc["Market Value"], hole=0.62))
            fig_alloc.update_layout(title="Portfolio allocation", height=350, template=PLOTLY_TEMPLATE, paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG)
            st.plotly_chart(fig_alloc, use_container_width=True)
        remove = st.selectbox("Remove holding", ["Select"] + [x["Symbol"] for x in holdings], key="portfolio_remove")
        if st.button("Remove selected holding", key="portfolio_remove_btn", disabled=remove == "Select"):
            st.session_state["portfolio_holdings"] = [x for x in holdings if x["Symbol"] != remove]
            st.rerun()
        st.download_button("Download portfolio CSV backup", pd.DataFrame(holdings, columns=columns).to_csv(index=False), "rakesh_portfolio_backup.csv", "text/csv")
    else:
        st.info("Your portfolio is empty. Add a holding above to begin tracking.")
    st.caption("Holdings are stored in this Streamlit session and may reset after a restart. Download a CSV backup regularly. Quotes may be delayed or unavailable.")

st.divider()
st.caption("Rakesh Market Analysis · Educational research and paper trading only · Not investment advice")