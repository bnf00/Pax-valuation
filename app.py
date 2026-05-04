import streamlit as st
import pandas as pd
import os
import yfinance as yf
import plotly.graph_objects as go
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import base64
from fpdf import FPDF

# ==========================================
# 1. PAGE CONFIG & PREMIUM CSS DESIGN
# ==========================================
st.set_page_config(page_title="Pax Valuation", layout="wide", initial_sidebar_state="expanded")

# Persistence Logic: Initialize Session State
if 'v_state' not in st.session_state:
    st.session_state.v_state = {
        'ddm_div': 2.0, 'ddm_g': 3.0, 'ddm_ke': 8.0,
        'dcf_fcf': 1000.0, 'dcf_g': 10.0, 'dcf_tg': 2.5, 'dcf_wacc': 9.0, 'dcf_shares': 500.0, 'dcf_debt': 2000.0,
        'rel_choice': "Earnings per Share (EPS)",
        'rel_eps': 5.0, 'rel_pe': 15.0,
        'rel_ebitda': 500.0, 'rel_eveb': 10.0, 'rel_sh1': 100.0, 'rel_nd1': 500.0,
        'rel_rev': 2000.0, 'rel_evs': 4.0, 'rel_sh2': 100.0, 'rel_nd2': 500.0
    }

# ==========================================
# BACKGROUND IMAGE INJECTION
# ==========================================
@st.cache_data
def get_base64_bg(file_path):
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

def add_bg_from_local():
    bg_file = "bg.jpg" if os.path.exists("bg.jpg") else ("bg.png" if os.path.exists("bg.png") else None)
    if bg_file:
        encoded_string = get_base64_bg(bg_file)
        ext = "jpg" if "jpg" in bg_file.lower() else "png"
        st.markdown(f"""<style>.stApp {{ background-image: url(data:image/{ext};base64,{encoded_string}); background-size: cover; background-position: center; background-attachment: fixed; }}</style>""", unsafe_allow_html=True)
    else:
        st.warning("Background image not found. Please save it as 'bg.jpg' or 'bg.png' in the same folder as app.py.")

add_bg_from_local()

# ==========================================
# CSS БЕЗ ПУСТЫХ СТРОК (ФИКС БАГА STREAMLIT)
# ==========================================
css_code = """
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
header[data-testid="stHeader"] { background-color: transparent !important; }
section[data-testid="stSidebar"] { background-color: rgba(10, 8, 5, 0.1) !important; backdrop-filter: blur(5px); border-right: 1px solid rgba(212, 175, 55, 0.1); }
section[data-testid="stSidebar"] > div { background-color: transparent !important; }
[data-testid="stSidebarNav"] { background-color: transparent !important; }
.stApp { color: #e0d8c8; font-family: 'Inter', sans-serif; }
.block-container { position: relative; padding-top: 3rem !important; max-width: 95% !important; }
.nav-header { text-align: left; border-bottom: 1px solid rgba(212, 175, 55, 0.3); padding-bottom: 8px; margin-bottom: 20px; }
.nav-header h3 { margin: 0; padding: 0; color: #ffffff; font-size: 1.2rem; font-weight: 600; font-family: 'Inter', sans-serif; letter-spacing: 0.5px; }
.stTabs [data-baseweb="tab-list"] { gap: 20px; border-bottom: 1px solid rgba(212, 175, 55, 0.2); padding-right: 180px !important; }
.stTabs [data-baseweb="tab"] { background-color: transparent !important; border: none !important; border-bottom: 3px solid transparent !important; border-radius: 0px !important; padding: 10px 4px !important; height: auto !important; }
.stTabs [data-baseweb="tab"] p { color: #a39b8a !important; font-weight: 500 !important; font-size: 15px !important; margin: 0 !important; font-family: 'Inter', sans-serif; }
.stTabs [aria-selected="true"] { background-color: transparent !important; border-bottom: 3px solid #d4af37 !important; }
.stTabs [aria-selected="true"] p { color: #ffffff !important; font-weight: 600 !important; text-shadow: 0 0 10px rgba(212, 175, 55, 0.3); }
div[data-baseweb="tab-highlight"] { display: none !important; }
div[data-testid="metric-container"] { background-color: rgba(15, 12, 8, 0.65); backdrop-filter: blur(10px); border: 1px solid rgba(212, 175, 55, 0.15); padding: 15px 20px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.4); }
div[data-testid="metric-container"] label { color: #c4bcae !important; font-weight: 500 !important; font-family: 'Inter', sans-serif; }
div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color: #ffffff !important; font-weight: 700 !important; font-family: 'JetBrains Mono', monospace !important; text-shadow: 0 0 15px rgba(212, 175, 55, 0.2); }
hr { border-color: rgba(212, 175, 55, 0.2) !important; margin-top: 2rem; margin-bottom: 2rem; }
.streamlit-expanderHeader { background-color: transparent !important; color: #d4af37 !important; font-weight: 600 !important; font-family: 'Inter', sans-serif; }
div[data-testid="stExpanderDetails"] { border-left: 2px solid rgba(212, 175, 55, 0.4); padding-left: 15px; }
div[role="radiogroup"] > label { padding-bottom: 10px; font-family: 'Inter', sans-serif; }
#active-company-anchor { display: none; }
div[data-testid="stVerticalBlock"]:has(> div > #active-company-anchor) { position: relative !important; }
div[data-testid="stVerticalBlock"]:has(> div > #active-company-anchor) > div[data-testid="stSelectbox"] { position: absolute !important; right: 0px !important; top: 2px !important; width: 170px !important; z-index: 999 !important; }
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div { background-color: rgba(15, 12, 8, 0.5) !important; border: 1px solid rgba(212, 175, 55, 0.2) !important; backdrop-filter: blur(5px); cursor: pointer !important; }
div[data-testid="stSelectbox"] div[data-baseweb="select"] span { color: #e0d8c8 !important; font-weight: 500 !important; font-size: 15px !important; text-align: right; font-family: 'Inter', sans-serif; }
div[data-testid="stSelectbox"] div[data-baseweb="select"] svg { fill: #d4af37 !important; }
div[data-testid="stSelectbox"]:hover div[data-baseweb="select"] span, div[data-testid="stSelectbox"]:hover div[data-baseweb="select"] svg { color: #ffffff !important; fill: #ffffff !important; }
div[data-testid="stDataFrame"] { background-color: transparent !important; }
.guide-box { background-color: rgba(15, 12, 8, 0.7); backdrop-filter: blur(10px); border-left: 4px solid #d4af37; padding: 15px; border-radius: 4px; margin-top: 30px; font-family: 'Inter', sans-serif; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
.guide-box h4 { color: #d4af37; margin-top: 0; }
</style>
"""
st.markdown(css_code, unsafe_allow_html=True)

# ==========================================
# CORE FUNCTIONS & PDF GENERATOR
# ==========================================
RATIO_EXPLANATIONS = {
    "Current Ratio": "Liquidity: Measures a company's ability to pay short-term obligations.",
    "ACID-Test Ratio": "Liquidity: Similar to Current Ratio, but excludes inventory.",
    "A/R Turnover": "Efficiency: Shows how effectively a company collects its debt.",
    "Inventory Turnover": "Efficiency: Shows how many times a company sold and replaced inventory.",
    "Profit Margin": "Profitability: The percentage of revenue remaining as profit.",
    "Asset Turnover": "Efficiency: Measures the value of sales relative to assets.",
    "ROA": "Profitability (Return on Assets): Profitable relative to total assets.",
    "ROE": "Profitability (Return on Equity): Profitable relative to shareholders equity.",
    "Debt to Assets": "Solvency: Proportion of assets financed by debt.",
    "Interest Earned": "Solvency: Ability to cover interest expenses.",
    "Net Working Capital (Live)": "Absolute liquidity measure: Current Assets minus Current Liabilities (Auto-fetched via Yahoo Finance)."
}

FILES_DIR = "analyses"
NOTES_DIR = "notes" 
if not os.path.exists(FILES_DIR): os.makedirs(FILES_DIR)
if not os.path.exists(NOTES_DIR): os.makedirs(NOTES_DIR)

def generate_pdf_report(ticker, current_price, intrinsic_value, notes):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(212, 175, 55) 
    pdf.cell(0, 15, f"Pax Investment Report: {ticker}", 0, 1, 'C')
    pdf.line(10, 25, 200, 25)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "Valuation Summary", 0, 1)
    pdf.set_font("Arial", '', 12)
    pdf.cell(50, 10, "Market Price:", 0, 0)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, str(current_price), 0, 1)
    pdf.set_font("Arial", '', 12)
    pdf.cell(50, 10, "Intrinsic Value:", 0, 0)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"${intrinsic_value:,.2f}" if isinstance(intrinsic_value, (int, float)) else str(intrinsic_value), 0, 1)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Analyst Notes & Thesis", 0, 1)
    pdf.set_font("Arial", '', 11)
    clean_notes = notes.encode('latin-1', 'replace').decode('latin-1') if notes else "No notes provided."
    pdf.multi_cell(0, 8, clean_notes)
    return pdf.output(dest='S').encode('latin-1')

@st.cache_data(ttl=3600)
def search_company(query):
    query = str(query).strip()
    if not query: return "", ""
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query)}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            quotes = data.get('quotes', [])
            for q in quotes:
                if q.get('quoteType') in ['EQUITY', 'ETF']: return q.get('symbol', query.upper()), q.get('shortname', query)
            if quotes: return quotes[0].get('symbol', query.upper()), quotes[0].get('shortname', query)
    except Exception: pass
    return query.upper(), query

@st.cache_data(ttl=900)
def get_current_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        return round(stock.fast_info['last_price'], 2)
    except: return "Error"

def safe_float(val):
    try: return float(str(val).replace('$', '').replace(',', '').strip())
    except: return 0.0

def calculate_potential(current_price_str, fair_value):
    try:
        c = safe_float(current_price_str)
        f = float(fair_value)
        if c > 0 and f > 0:
            pot = ((f - c) / c) * 100
            return f"+{pot:.2f}%" if pot > 0 else f"{pot:.2f}%"
    except: pass
    return "N/A"

@st.cache_data(ttl=3600)
def fetch_robust_news(ticker):
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    articles = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            for item in root.findall('./channel/item')[:5]:
                title = item.find('title').text if item.find('title') is not None else "No Title"
                link = item.find('link').text if item.find('link') is not None else "#"
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                if pub_date: pub_date = pub_date.replace(" +0000", "").replace(" GMT", "")
                articles.append({'title': title, 'link': link, 'date': pub_date})
    except Exception: pass
    return articles

@st.cache_data(ttl=86400)
def fetch_live_financials(ticker):
    try:
        stock = yf.Ticker(ticker)
        bs = stock.balance_sheet
        if bs.empty: return None, None
        latest_bs_col = bs.columns[0]
        
        def get_metric(df, col_name, date_col):
            try: return float(df.loc[col_name, date_col])
            except: return 0.0

        current_assets = get_metric(bs, 'Current Assets', latest_bs_col)
        current_liabilities = get_metric(bs, 'Current Liabilities', latest_bs_col)
        nwc = current_assets - current_liabilities
        
        formatted = {
            "Net Working Capital": f"${nwc:,.0f}" if nwc != 0 else "N/A"
        }
        return formatted, str(latest_bs_col.year)
    except Exception: return None, None

def clean_excel_data(df):
    def format_cell(x):
        if pd.isna(x) or str(x).strip() in ['#DIV/0!', '#VALUE!', '#N/A', 'None', '#REF!', '']: return '-'
        try:
            num = float(x)
            if abs(num) >= 1000: return f"{num:,.0f}".replace(',', ' ')
            if abs(num) > 0: return f"{num:.4f}"
            return "0"
        except: return str(x)
    return df.map(format_cell) if hasattr(df, 'map') else df.applymap(format_cell)

def find_intrinsic_values(df, is_relative=False):
    target_keywords = ["intrinsic value", "fair value", "target price", "value per share", "implied price"]
    if is_relative: target_keywords.extend(["average", "implied value"])
    results = {}
    for r in range(len(df)):
        for c in range(len(df.columns)):
            cell_text_raw = str(df.iloc[r, c]).strip()
            if any(k in cell_text_raw.lower() for k in target_keywords):
                row_vals = []
                for scan_c in range(c + 1, len(df.columns)):
                    val = df.iloc[r, scan_c]
                    try:
                        if pd.notna(val):
                            num = float(str(val).replace('$', '').replace(',', '').replace(' ', '').strip())
                            if num > 0: row_vals.append(num)
                    except ValueError: pass
                if row_vals:
                    if is_relative and len(row_vals) > 0:
                        final_val = sum(row_vals) / len(row_vals)
                        label = "Consensus Target" if cell_text_raw.lower() == "average" else (cell_text_raw if cell_text_raw else "Calculated Value")
                    else:
                        final_val = row_vals[0]
                        label = cell_text_raw if cell_text_raw else "Calculated Value"
                    base_label = label
                    counter = 2
                    while label in results and results[label] != round(final_val, 2):
                        label = f"{base_label} ({counter})"
                        counter += 1
                    results[label] = round(final_val, 2)
                    break 
    return results

def extract_relative_valuation_data(df):
    headers = [str(c) for c in df.columns]
    valid_cols = [c for c in headers if not c.lower().startswith('unnamed') and len(c.strip()) > 1]
    if len(valid_cols) < 3:
        for r in range(min(5, len(df))):
            row_vals = [str(x) for x in df.iloc[r]]
            valid_vals = [x for x in row_vals if x.lower() not in ['nan', 'item', ''] and not x.lower().startswith('fy ') and len(x)>1]
            if len(valid_vals) >= 2: headers = row_vals; break
    results = []
    target_keywords = ["intrinsic value based on", "average", "implied value"]
    for r in range(len(df)):
        cell_text = str(df.iloc[r, 0]).strip()
        if any(k in cell_text.lower() for k in target_keywords):
            row_data = {"Metric": cell_text, "Peers": {}}
            for c in range(1, len(df.columns)):
                val = df.iloc[r, c]
                try:
                    if pd.notna(val):
                        num = float(str(val).replace('$', '').replace(',', '').strip())
                        if num > 0:
                            peer_name = headers[c].strip() if c < len(headers) else f"Competitor {c}"
                            if peer_name.lower() not in ['nan', 'fy 2025', 'item', '']:
                                row_data["Peers"][peer_name] = num
                except ValueError: pass
            if row_data["Peers"]: results.append(row_data)
    return results

def extract_key_ratios(df):
    target_ratios = {
        "Current Ratio": ["current ratio"], "ACID-Test Ratio": ["acid-test", "quick ratio"],
        "A/R Turnover": ["receivable turnover"], "Inventory Turnover": ["inventory turnover"],
        "Profit Margin": ["profit margin"], "Asset Turnover": ["asset turnover"],
        "ROA": ["return on assets", "roa"], "ROE": ["return on ordinary shareholders", "roe"],
        "Debt to Assets": ["debt to total assets"], "Interest Earned": ["times interest earned"]
    }
    latest_year_col = None; max_year = -1
    for col in df.columns:
        match = re.search(r'(20\d{2})', str(col).strip())
        if match:
            year = int(match.group(1))
            if year > max_year: max_year = year; latest_year_col = col
    if latest_year_col is None: latest_year_col = df.columns[-1]
    results = {"_latest_year": str(max_year) if max_year != -1 else str(latest_year_col)}
    excel_errors = ['-', '', '#DIV/0!', '#VALUE!', '#N/A', '#REF!', 'None', 'nan']
    for r in range(len(df)):
        row_name = str(df.iloc[r, 0]).strip().lower()
        for key, aliases in target_ratios.items():
            if key not in results and any(alias in row_name for alias in aliases):
                val = df.loc[r, latest_year_col]
                if pd.isna(val) or str(val).strip() in excel_errors: results[key] = "N/A"
                else:
                    try:
                        val_str = str(val).replace(',', '').replace('%', '').strip()
                        num = float(val_str)
                        is_percentage = any(word in key.lower() for word in ['margin', 'roa', 'roe', 'debt'])
                        results[key] = f"{num*100:.2f}%" if ('%' in str(val) or is_percentage) and num < 2 and '%' not in str(val) else (f"{num:.2f}%" if '%' in str(val) or is_percentage else f"{num:.2f}")
                    except ValueError: results[key] = str(val) if str(val).strip() not in excel_errors else "N/A"
    return results

# ==========================================
# ЧИСТАЯ ЛОКАЛЬНАЯ БАЗА ДАННЫХ
# ==========================================
DB_FILE = "watchlist.csv"

if os.path.exists(DB_FILE):
    df_watchlist = pd.read_csv(DB_FILE)
    for col in ["Stock", "Company name", "Interest", "Market price", "Potential"]:
        if col in df_watchlist.columns:
            df_watchlist[col] = df_watchlist[col].astype('object')
    if 'Shares' not in df_watchlist.columns: df_watchlist['Shares'] = 0.0
    if 'Avg Cost' not in df_watchlist.columns: df_watchlist['Avg Cost'] = 0.0
    if 'In Portfolio' not in df_watchlist.columns: df_watchlist['In Portfolio'] = False
else:
    df_watchlist = pd.DataFrame(columns=["Stock", "Company name", "Interest", "Market price", "Intrinsic value", "Potential", "In Portfolio", "Shares", "Avg Cost"])
    for col in ["Stock", "Company name", "Interest", "Market price", "Potential"]:
        df_watchlist[col] = df_watchlist[col].astype('object')

def save_db(df):
    df.to_csv(DB_FILE, index=False)

# ==========================================
# SIDEBAR NAVIGATION
# ==========================================
st.sidebar.markdown("""
    <div class="nav-header">
        <h3>Navigation</h3>
    </div>
""", unsafe_allow_html=True)

app_mode = st.sidebar.radio("Select View:", ["Terminal (Analysis)", "Macro Dashboard", "My Portfolio", "Valuation Lab"], label_visibility="collapsed")

def render_header():
    st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 30px;">
            <div style="background: linear-gradient(135deg, #f5c518 0%, #aa8c2c 100%); width: 45px; height: 45px; border-radius: 10px; display: flex; align-items: center; justify-content: center; margin-right: 15px; box-shadow: 0 4px 20px rgba(212, 175, 55, 0.4);">
                <span style="color: #1a160d; font-size: 24px; font-weight: 800; font-family: 'Inter', sans-serif;">P</span>
            </div>
            <div>
                <h1 style="margin: 0; padding: 0; font-size: 2.2rem; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; line-height: 1; font-family: 'Inter', sans-serif; text-shadow: 0 2px 10px rgba(0,0,0,0.5);">Pax</h1>
                <p style="margin: 4px 0 0 0; padding: 0; color: #d4af37; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px; font-family: 'Inter', sans-serif;">Fundamental Analysis</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# APP ROUTING
# ==========================================

if app_mode == "Terminal (Analysis)":
    
    render_header()
    
    nav_container = st.container()
    
    with nav_container:
        st.markdown('<div id="active-company-anchor"></div>', unsafe_allow_html=True)
        
        selected_ticker = st.selectbox(
            "Active Company", 
            df_watchlist['Stock'].tolist() if not df_watchlist.empty else [""], 
            label_visibility="collapsed"
        )
        
        tab_watchlist, tab_profile, tab_ratios, tab_val_models, tab_compare, tab_notes = st.tabs([
            "Watchlist", "Company Profile", "Financial Ratios", "Valuation Models", "Compare", "Notes"
        ])

    # --- PAGE 1: WATCHLIST ---
    with tab_watchlist:
        col_add, col_upload, col_del = st.columns(3)
        
        with col_add:
            with st.expander("➕ Add New Company"):
                with st.form("add_form", clear_on_submit=True):
                    nt = st.text_input("Company Name or Ticker (e.g., TSLA)")
                    ni = st.selectbox("Interest", ["5 - Critical", "4 - High", "3 - Medium", "2 - Low", "1 - Watch"])
                    if st.form_submit_button("Add") and nt:
                        real_ticker, real_name = search_company(nt)
                        price = get_current_price(real_ticker)
                        new_row = pd.DataFrame([{"Stock": real_ticker, "Company name": real_name, "Interest": ni, "Market price": f"${price}", "Intrinsic value": 0.0, "Potential": "N/A", "In Portfolio": False, "Shares": 0.0, "Avg Cost": 0.0}])
                        for col in ["Stock", "Company name", "Interest", "Market price", "Potential"]: new_row[col] = new_row[col].astype('object')
                        df_watchlist = pd.concat([df_watchlist, new_row], ignore_index=True)
                        save_db(df_watchlist)
                        st.rerun()

        with col_upload:
            with st.expander("📂 Upload Excel Analysis"):
                if not df_watchlist.empty:
                    upload_target = st.selectbox("Assign file to:", df_watchlist['Stock'].tolist())
                    up_file = st.file_uploader("Select .xlsx file", type="xlsx", label_visibility="collapsed")
                    if up_file:
                        path = os.path.join(FILES_DIR, f"{upload_target}.xlsx")
                        with open(path, "wb") as f: f.write(up_file.getbuffer())
                        st.success(f"File attached to {upload_target}!")

        with col_del:
            with st.expander("❌ Remove Company"):
                with st.form("delete_form"):
                    if not df_watchlist.empty:
                        ticker_to_delete = st.selectbox("Select ticker to remove", df_watchlist['Stock'].tolist())
                        if st.form_submit_button("Delete"):
                            df_watchlist = df_watchlist[df_watchlist['Stock'] != ticker_to_delete]
                            save_db(df_watchlist)
                            file_to_delete = os.path.join(FILES_DIR, f"{ticker_to_delete}.xlsx")
                            if os.path.exists(file_to_delete): os.remove(file_to_delete)
                            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        
        col_btn, col_search = st.columns([1, 4])
        with col_btn:
            if st.button("🔄 Update Market Data", use_container_width=True):
                with st.spinner('Fetching live prices...'):
                    get_current_price.clear()
                    tickers_list = df_watchlist['Stock'].tolist()
                    if tickers_list:
                        try:
                            data = yf.download(tickers_list, period="1d", progress=False)
                            if not data.empty and 'Close' in data:
                                close_data = data['Close']
                                for i, r in df_watchlist.iterrows():
                                    ticker = r['Stock']
                                    p = "Error"
                                    try:
                                        if isinstance(close_data, pd.DataFrame) and ticker in close_data.columns:
                                            p = round(float(close_data[ticker].dropna().iloc[-1]), 2)
                                        elif isinstance(close_data, pd.Series): 
                                            p = round(float(close_data.dropna().iloc[-1]), 2)
                                    except:
                                        p = get_current_price(ticker)
                                        
                                    if isinstance(p, (float, int)):
                                        df_watchlist.at[i, 'Market price'] = f"${p}"
                                        df_watchlist.at[i, 'Potential'] = calculate_potential(f"${p}", r['Intrinsic value'])
                        except:
                            for i, r in df_watchlist.iterrows():
                                p = get_current_price(r['Stock'])
                                if isinstance(p, float):
                                    df_watchlist.at[i, 'Market price'] = f"${p}"
                                    df_watchlist.at[i, 'Potential'] = calculate_potential(f"${p}", r['Intrinsic value'])
                                    
                    save_db(df_watchlist)
                    st.rerun()
                    
        with col_search: search_query = st.text_input("Search", label_visibility="collapsed", placeholder="🔍 Search company or ticker...")

        display_df = df_watchlist.copy()
        if search_query:
            mask = display_df['Stock'].str.contains(search_query, case=False, na=False) | display_df['Company name'].str.contains(search_query, case=False, na=False)
            display_df = display_df[mask]
        
        edited_df = st.data_editor(
            display_df,
            use_container_width=True, hide_index=True,
            column_config={
                "Interest": st.column_config.SelectboxColumn("Interest", options=["5 - Critical", "4 - High", "3 - Medium", "2 - Low", "1 - Watch"], required=True),
                "In Portfolio": st.column_config.CheckboxColumn("Portfolio", default=False),
                "Shares": None,
                "Avg Cost": None
            },
            disabled=["Stock", "Company name", "Market price", "Intrinsic value", "Potential"]
        )
        
        if not edited_df.equals(display_df):
            df_watchlist.update(edited_df)
            save_db(df_watchlist)
            st.rerun()

    # --- PAGE 2: PROFILE ---
    with tab_profile:
        if selected_ticker and selected_ticker != "":
            st.subheader(f"Market Chart: {selected_ticker}")
            col_tf, col_int, _ = st.columns([1, 1, 2])
            with col_tf: period_ui = st.selectbox("Period", ["1 Month", "6 Months", "1 Year", "5 Years", "10 Years"], index=2)
            with col_int: interval_ui = st.selectbox("Interval", ["Daily", "Weekly", "Monthly"], index=0)
            period_map = {"1 Month": "1mo", "6 Months": "6mo", "1 Year": "1y", "5 Years": "5y", "10 Years": "10y"}
            interval_map = {"Daily": "1d", "Weekly": "1wk", "Monthly": "1mo"}

            try:
                stock_obj = yf.Ticker(selected_ticker)
                df_h = stock_obj.history(period=period_map[period_ui], interval=interval_map[interval_ui])
                if not df_h.empty:
                    fig = go.Figure(data=[go.Candlestick(x=df_h.index, open=df_h['Open'], high=df_h['High'], low=df_h['Low'], close=df_h['Close'], increasing_line_color='#d4af37', decreasing_line_color='#8a7122')])
                    iv_raw = df_watchlist.loc[df_watchlist['Stock']==selected_ticker, 'Intrinsic value'].values[0]
                    try:
                        iv_float = float(str(iv_raw).replace('$', '').replace(',', ''))
                        if iv_float > 0:
                            fig.add_hline(y=iv_float, line_dash="dash", line_color="#d4af37", annotation_text=f"Intrinsic Value: ${iv_float:,.2f}", annotation_position="bottom right", annotation_font_color="#d4af37")
                    except: pass
                    fig.update_layout(height=500, margin=dict(l=0,r=0,t=10,b=0), xaxis_rangeslider_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e0d8c8'))
                    st.plotly_chart(fig, use_container_width=True)
            except: st.error("Error fetching chart data.")
            
            st.markdown("<hr>", unsafe_allow_html=True)
            st.subheader(f"📰 Recent News for {selected_ticker}")
            news_data = fetch_robust_news(selected_ticker)
            if news_data:
                for article in news_data:
                    st.markdown(f"**[{article['title']}]({article['link']})**")
                    st.caption(f"Yahoo Finance RSS • {article['date']}")
                    st.markdown("<br>", unsafe_allow_html=True)
            else: st.info("No recent news found for this ticker.")
        else: st.warning("Your watchlist is empty.")

    # --- PAGE 3: RATIOS (Возвращение к Excel + Живой NWC) ---
    with tab_ratios:
        if selected_ticker and selected_ticker != "":
            st.subheader(f"Financial Ratios: {selected_ticker}")
            path = os.path.join(FILES_DIR, f"{selected_ticker}.xlsx")
            if os.path.exists(path):
                xls = pd.ExcelFile(path)
                if 'Ratios' in xls.sheet_names:
                    df = pd.read_excel(path, sheet_name='Ratios')
                    key_metrics = extract_key_ratios(df)
                    
                    if key_metrics:
                        latest_year = key_metrics.pop("_latest_year", "Latest")
                        
                        # Добавляем Net Working Capital из живых данных yfinance
                        live_ratios, _ = fetch_live_financials(selected_ticker)
                        if live_ratios and "Net Working Capital" in live_ratios:
                            key_metrics["Net Working Capital (Live)"] = live_ratios["Net Working Capital"]
                        
                        st.write(f"**Key Performance Indicators ({latest_year})**")
                        cols = st.columns(5)
                        for i, (name, val) in enumerate(key_metrics.items()):
                            tooltip_text = RATIO_EXPLANATIONS.get(name, "Financial Metric")
                            with cols[i % 5]: st.metric(label=name, value=val, help=tooltip_text)
                            if (i + 1) % 5 == 0: st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("<hr>", unsafe_allow_html=True)
                    with st.expander("View Full Raw Data", expanded=not bool(key_metrics)): st.dataframe(clean_excel_data(df), use_container_width=True, height=(len(df)*35)+40)
                else: st.error("Sheet 'Ratios' not found.")
            else: st.info("No file attached for this company. Please upload an Excel file.")
            
    # --- PAGE 4: VALUATION MODELS (From Excel) ---
    with tab_val_models:
        if selected_ticker and selected_ticker != "":
            st.subheader(f"Valuation Overview: {selected_ticker}")
            path = os.path.join(FILES_DIR, f"{selected_ticker}.xlsx")
            if os.path.exists(path):
                xls = pd.ExcelFile(path)
                display_to_original = {}
                for m in xls.sheet_names:
                    m_str = str(m).strip()
                    if m_str.startswith("In.Val -") or "relative valuation" in m_str.lower() or "multiples" in m_str.lower():
                        display_to_original[m_str.replace("In.Val - ", "").strip()] = m_str
                if display_to_original:
                    selected_model_display = st.radio("Select Model Setup:", list(display_to_original.keys()), horizontal=True)
                    df = pd.read_excel(path, sheet_name=display_to_original[selected_model_display])
                    current_p = get_current_price(selected_ticker)
                    is_relative = "relative" in selected_model_display.lower() or "multiples" in selected_model_display.lower()
                    
                    if is_relative:
                        rel_data = extract_relative_valuation_data(df)
                        if rel_data:
                            st.write(f"**Comparative Analysis from {selected_model_display}:**")
                            for item in rel_data:
                                st.markdown(f"#### {item['Metric']}")
                                cols = st.columns(len(item["Peers"]))
                                avg_val = sum(item["Peers"].values()) / len(item["Peers"])
                                for i, (peer, val) in enumerate(item["Peers"].items()):
                                    clean_peer = peer.replace('.1', '').replace('.2', '')
                                    if clean_peer.lower().startswith('unnamed'): clean_peer = f"Competitor {i+1}"
                                    with cols[i]:
                                        if isinstance(current_p, (int, float)) and current_p > 0: st.metric(label=f"Implied by {clean_peer}", value=f"${val:,.2f}", delta=f"{((val - current_p) / current_p) * 100:.2f}%")
                                        else: st.metric(label=f"Implied by {clean_peer}", value=f"${val:,.2f}")
                                if st.button(f"Sync Average ({item['Metric']}): ${avg_val:,.2f}", key=f"sync_xl_{selected_ticker}_{item['Metric']}"):
                                    df_watchlist.loc[df_watchlist['Stock']==selected_ticker, 'Intrinsic value'] = avg_val
                                    df_watchlist.loc[df_watchlist['Stock']==selected_ticker, 'Potential'] = calculate_potential(str(current_p), avg_val)
                                    save_db(df_watchlist)
                                    st.success(f"Watchlist updated!")
                                st.markdown("<hr>", unsafe_allow_html=True)
                        else: st.info("Could not extract Relative Valuation data.")
                    else:
                        found_values = find_intrinsic_values(df)
                        if found_values:
                            st.write(f"**Calculated targets found in {selected_model_display}:**")
                            for label, val in found_values.items():
                                mc1, mc2, mc3 = st.columns(3)
                                with mc1: st.metric(label=label, value=f"${val:,.2f}")
                                with mc2: st.metric(label="Market Price", value=f"${current_p}")
                                with mc3:
                                    if isinstance(current_p, (int, float)) and current_p > 0: st.metric(label="Upside / Downside", value=f"{abs(((val - current_p) / current_p) * 100):.2f}%", delta=f"{((val - current_p) / current_p) * 100:.2f}%")
                                if st.button(f"Sync '{label}' (${val:,.2f}) to Watchlist", key=f"sync_xl_{selected_ticker}_{label}_{val}"):
                                    df_watchlist.loc[df_watchlist['Stock']==selected_ticker, 'Intrinsic value'] = val
                                    df_watchlist.loc[df_watchlist['Stock']==selected_ticker, 'Potential'] = calculate_potential(str(current_p), val)
                                    save_db(df_watchlist)
                                    st.success(f"Watchlist updated!")
                                st.markdown("<br>", unsafe_allow_html=True)
                        else: st.info("Could not auto-detect final values in this sheet.")
                    st.markdown("<hr>", unsafe_allow_html=True)
                    with st.expander("View Raw Calculation Data (Full Spreadsheet)"): st.dataframe(clean_excel_data(df), use_container_width=True, height=500)
                else: st.warning("No Valuation models found in this file.")
            else: st.info("No file attached.")

    # --- PAGE 5: COMPARE ---
    with tab_compare:
        st.subheader("Peer Comparison Dashboard")
        if not df_watchlist.empty:
            all_tickers = df_watchlist['Stock'].tolist()
            tickers_to_compare = st.multiselect("Select companies to compare:", options=all_tickers, default=all_tickers[:3] if len(all_tickers) >= 3 else all_tickers)
            if len(tickers_to_compare) > 0:
                compare_data = {}
                with st.spinner('Compiling fundamental data...'):
                    for t in tickers_to_compare:
                        row = df_watchlist[df_watchlist['Stock'] == t]
                        iv_val = row['Intrinsic value'].values[0] if not row.empty else "N/A"
                        try: formatted_iv = f"${float(iv_val):,.2f}" if pd.notna(iv_val) and iv_val != "" else "N/A"
                        except: formatted_iv = "N/A"
                            
                        comp_info = {
                            "Market Price": str(row['Market price'].values[0]) if not row.empty else "N/A", 
                            "Intrinsic Value": formatted_iv, 
                            "Potential": str(row['Potential'].values[0]) if not row.empty else "N/A"
                        }
                        
                        path = os.path.join(FILES_DIR, f"{t}.xlsx")
                        if os.path.exists(path):
                            try:
                                xls = pd.ExcelFile(path)
                                if 'Ratios' in xls.sheet_names:
                                    df_r = pd.read_excel(path, sheet_name='Ratios')
                                    ratios = extract_key_ratios(df_r)
                                    ratios.pop("_latest_year", None)
                                    comp_info.update(ratios)
                            except: pass
                            
                        live_ratios, _ = fetch_live_financials(t)
                        if live_ratios and "Net Working Capital" in live_ratios:
                            comp_info["Net Working Capital (Live)"] = live_ratios["Net Working Capital"]
                            
                        compare_data[t] = comp_info
                df_compare = pd.DataFrame(compare_data); df_compare.fillna("N/A", inplace=True)
                st.markdown("<br>", unsafe_allow_html=True)
                st.dataframe(df_compare, use_container_width=True, height=(len(df_compare) * 36) + 43)
            else: st.info("Select at least one company to see the comparison.")
        else: st.info("Your watchlist is empty. Add companies first.")

    # --- PAGE 6: NOTES & PDF EXPORT ---
    with tab_notes:
        if selected_ticker and selected_ticker != "":
            st.subheader(f"📝 Investment Thesis & Notes: {selected_ticker}")
            note_path = os.path.join(NOTES_DIR, f"{selected_ticker}_notes.txt")
            existing_note = ""
            if os.path.exists(note_path):
                with open(note_path, "r", encoding="utf-8") as f: existing_note = f.read()
                
            new_note = st.text_area("Editor", value=existing_note, height=400, label_visibility="collapsed", key=f"note_editor_{selected_ticker}")
            
            col_save, col_pdf = st.columns([1, 1])
            with col_save:
                if st.button("💾 Save Notes", type="primary", use_container_width=True, key=f"save_btn_{selected_ticker}"):
                    with open(note_path, "w", encoding="utf-8") as f: f.write(new_note)
                    st.success("Investment notes saved securely!")
            
            with col_pdf:
                current_p = df_watchlist.loc[df_watchlist['Stock'] == selected_ticker, 'Market price'].values[0]
                int_val = df_watchlist.loc[df_watchlist['Stock'] == selected_ticker, 'Intrinsic value'].values[0]
                
                pdf_bytes = generate_pdf_report(selected_ticker, current_p, int_val, new_note)
                
                st.download_button(
                    label="📥 Export PDF Report",
                    data=pdf_bytes,
                    file_name=f"{selected_ticker}_Pax_Report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.warning("Your watchlist is empty.")

# ==========================================
# НОВЫЙ РОУТИНГ: МАКРОЭКОНОМИЧЕСКИЙ ДАШБОРД С НАСТРОЙКОЙ
# ==========================================
elif app_mode == "Macro Dashboard":
    render_header()
    st.subheader("🌍 Macroeconomic & Market Overview")
    
    # Селекторы периода и интервала для макро-дашборда
    col_macro_period, col_macro_interval, _ = st.columns([1, 1, 3])
    with col_macro_period: 
        m_period_ui = st.selectbox("Timeframe", ["1 Month", "6 Months", "1 Year", "5 Years", "10 Years", "Max"], index=4, key="macro_period")
    with col_macro_interval: 
        m_interval_ui = st.selectbox("Interval", ["Daily", "Weekly", "Monthly"], index=2, key="macro_interval")
        
    m_period_map = {"1 Month": "1mo", "6 Months": "6mo", "1 Year": "1y", "5 Years": "5y", "10 Years": "10y", "Max": "max"}
    m_interval_map = {"Daily": "1d", "Weekly": "1wk", "Monthly": "1mo"}
    
    macro_symbols = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "Volatility (VIX)": "^VIX",
        "10-Yr Treasury Yield": "^TNX"
    }
    
    @st.cache_data(ttl=3600)
    def fetch_macro_data(period, interval):
        hist_data = {}
        current_data = {}
        for name, symbol in macro_symbols.items():
            try:
                tk = yf.Ticker(symbol)
                hist = tk.history(period=period, interval=interval)
                if not hist.empty and len(hist) > 1:
                    hist = hist.dropna(subset=['Close']) # Очистка от пустых строк
                    hist_data[name] = hist['Close']
                    
                    # Дельта (разница) рассчитывается между двумя последними точками на графике
                    current_price = hist['Close'].iloc[-1]
                    prev_price = hist['Close'].iloc[-2]
                    pct_change = ((current_price - prev_price) / prev_price) * 100
                    
                    if symbol == "^TNX":
                        current_data[name] = {"val": f"{current_price:.2f}%", "change": f"{pct_change:+.2f}%"}
                    else:
                        current_data[name] = {"val": f"{current_price:,.2f}", "change": f"{pct_change:+.2f}%"}
            except:
                pass
        return hist_data, current_data

    with st.spinner("Fetching global market data..."):
        macro_hist, macro_current = fetch_macro_data(m_period_map[m_period_ui], m_interval_map[m_interval_ui])
        
    if macro_current:
        cols = st.columns(4)
        for i, (name, data) in enumerate(macro_current.items()):
            delta_col = "inverse" if name == "Volatility (VIX)" else "normal"
            cols[i].metric(name, data['val'], data['change'], delta_color=delta_col)
            
        st.markdown("<hr>", unsafe_allow_html=True)
        st.write(f"### {m_period_ui} Market Trends")
        c1, c2 = st.columns(2)
        
        def plot_sparkline(series, title, color):
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=series.index, y=series.values, mode='lines', line=dict(color=color, width=2)))
            fig.update_layout(title=title, height=250, margin=dict(l=0,r=0,t=30,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e0d8c8'), xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='rgba(212,175,55,0.1)'))
            return fig

        if "S&P 500" in macro_hist: c1.plotly_chart(plot_sparkline(macro_hist["S&P 500"], "S&P 500 Index", "#d4af37"), use_container_width=True)
        if "NASDAQ" in macro_hist: c2.plotly_chart(plot_sparkline(macro_hist["NASDAQ"], "NASDAQ Composite", "#00d2ff"), use_container_width=True)
        if "Volatility (VIX)" in macro_hist: c1.plotly_chart(plot_sparkline(macro_hist["Volatility (VIX)"], "VIX (Fear Index)", "#ff4b4b"), use_container_width=True)
        if "10-Yr Treasury Yield" in macro_hist: c2.plotly_chart(plot_sparkline(macro_hist["10-Yr Treasury Yield"], "10-Yr Treasury Yield (%)", "#28a745"), use_container_width=True)
    else:
        st.error("Failed to fetch macroeconomic data.")


# ==========================================
# РОУТИНГ: РЕЖИМ ПОРТФЕЛЯ
# ==========================================
elif app_mode == "My Portfolio":
    render_header()
    st.subheader("💼 My Portfolio Dashboard")
    
    portfolio_df = df_watchlist[df_watchlist['In Portfolio'] == True].copy()
    
    if not portfolio_df.empty:
        display_port = portfolio_df[['Stock', 'Company name', 'Shares', 'Avg Cost']].copy()
        display_port['Market price'] = portfolio_df['Market price'].apply(safe_float)
        display_port['Total Value'] = display_port['Shares'] * display_port['Market price']
        display_port['Total Cost'] = display_port['Shares'] * display_port['Avg Cost']
        display_port['P&L ($)'] = display_port['Total Value'] - display_port['Total Cost']
        display_port['P&L (%)'] = display_port.apply(lambda row: (row['P&L ($)'] / row['Total Cost'] * 100) if row['Total Cost'] > 0 else 0.0, axis=1)
        
        total_value = display_port['Total Value'].sum()
        total_cost = display_port['Total Cost'].sum()
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Value", f"${total_value:,.2f}")
        m2.metric("Total Cost Basis", f"${total_cost:,.2f}")
        m3.metric("Total Return (P&L)", f"${total_pnl:,.2f}", f"{total_pnl_pct:.2f}%")
        
        st.markdown("<hr>", unsafe_allow_html=True)
        st.write("📝 **Edit your positions below:** (Update 'Shares' and 'Avg Cost')")
        
        edit_df = display_port[['Stock', 'Company name', 'Market price', 'Shares', 'Avg Cost', 'Total Value', 'P&L ($)', 'P&L (%)']]
        
        edited_port = st.data_editor(
            edit_df,
            use_container_width=True,
            hide_index=True,
            disabled=["Stock", "Company name", "Market price", "Total Value", "P&L ($)", "P&L (%)"],
            column_config={
                "Market price": st.column_config.NumberColumn(format="$%.2f"),
                "Total Value": st.column_config.NumberColumn(format="$%.2f"),
                "P&L ($)": st.column_config.NumberColumn(format="$%.2f"),
                "P&L (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Shares": st.column_config.NumberColumn(min_value=0.0, step=1.0),
                "Avg Cost": st.column_config.NumberColumn("Avg Cost ($)", min_value=0.0, step=1.0, format="%.2f"),
            }
        )
        
        if not edited_port[['Shares', 'Avg Cost']].equals(edit_df[['Shares', 'Avg Cost']]):
            for index, row in edited_port.iterrows():
                stock = row['Stock']
                df_watchlist.loc[df_watchlist['Stock'] == stock, 'Shares'] = row['Shares']
                df_watchlist.loc[df_watchlist['Stock'] == stock, 'Avg Cost'] = row['Avg Cost']
            save_db(df_watchlist)
            st.rerun()
            
    else:
        st.info("Your portfolio is empty. Go to 'Terminal (Analysis)' -> 'Watchlist' and tick the 'Portfolio' checkbox next to a company to add it here.")

# ==========================================
# РОУТИНГ: VALUATION LAB 
# ==========================================
elif app_mode == "Valuation Lab":
    render_header()
    st.subheader("🔬 Valuation Laboratory")
    
    if not df_watchlist.empty:
        selected_ticker = st.selectbox("Select Company for Analysis", df_watchlist['Stock'].tolist())
        st.write(f"Dynamic valuation models for **{selected_ticker}**.")
        
        current_price_str = df_watchlist.loc[df_watchlist['Stock'] == selected_ticker, 'Market price'].values[0]
        current_p = safe_float(current_price_str)

        tab_ddm, tab_dcf, tab_rel = st.tabs([
            "1. Gordon Growth Model (DDM)", 
            "2. Multi-Stage Discounted Cash Flow (DCF)", 
            "3. Relative Valuation (Multiples)"
        ])
        
        # ------------------------------------------
        # МЕТОД 1: GORDON GROWTH MODEL (DDM)
        # ------------------------------------------
        with tab_ddm:
            col_inputs, col_results = st.columns([1, 2], gap="large")
            with col_inputs:
                st.markdown("#### ⚙️ DDM Assumptions")
                st.session_state.v_state['ddm_div'] = st.number_input("Current Annual Dividend per Share ($)", value=float(st.session_state.v_state['ddm_div']), step=0.1)
                st.session_state.v_state['ddm_g'] = st.slider("Expected Dividend Growth Rate", min_value=0.0, max_value=15.0, value=float(st.session_state.v_state['ddm_g']), step=0.1, format="%f%%")
                st.session_state.v_state['ddm_ke'] = st.slider("Cost of Equity (Expected Return)", min_value=1.0, max_value=25.0, value=float(st.session_state.v_state['ddm_ke']), step=0.5, format="%f%%")
                
                div_0 = st.session_state.v_state['ddm_div']
                g_div = st.session_state.v_state['ddm_g'] / 100
                ke = st.session_state.v_state['ddm_ke'] / 100
            
            with col_results:
                st.markdown("#### 📊 DDM Valuation")
                if ke <= g_div:
                    st.error("Error: Cost of Equity must be strictly greater than the Dividend Growth Rate for the Gordon model to work.")
                    intrinsic_value = 0.0
                else:
                    intrinsic_value = div_0 * (1 + g_div) / (ke - g_div)
                    m1, m2 = st.columns(2)
                    m1.metric("Projected Next Dividend (D1)", f"${div_0 * (1 + g_div):.2f}")
                    
                    if current_p > 0:
                        upside = ((intrinsic_value - current_p) / current_p) * 100
                        m2.metric("Intrinsic Value per Share", f"${intrinsic_value:,.2f}", f"{upside:+.2f}% Upside", delta_color="normal")
                    else:
                        m2.metric("Intrinsic Value per Share", f"${intrinsic_value:,.2f}")
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 Sync DDM Value to Watchlist", type="primary", use_container_width=True, disabled=(intrinsic_value==0), key=f"sync_ddm_{selected_ticker}"):
                    df_watchlist.loc[df_watchlist['Stock']==selected_ticker, 'Intrinsic value'] = intrinsic_value
                    df_watchlist.loc[df_watchlist['Stock']==selected_ticker, 'Potential'] = calculate_potential(str(current_p), intrinsic_value)
                    save_db(df_watchlist)
                    st.success(f"Watchlist updated!")
            
            st.markdown("""
                <div class="guide-box">
                    <h4>💡 Шпаргалка аналитика: Gordon Growth Model (DDM)</h4>
                    <ul>
                        <li><b>Когда использовать:</b> Для зрелых компаний, которые стабильно платят дивиденды и имеют четкую дивидендную политику. Предполагается, что дивиденды будут расти постоянным темпом вечно.</li>
                        <li><b>Идеальные кандидаты:</b> Коммунальные предприятия (Utilities), телекоммуникации (AT&T, Verizon), крупные банки (JPMorgan), устоявшиеся потребительские бренды (Coca-Cola, P&G).</li>
                        <li><b>Когда НЕ использовать:</b> Для компаний, которые не платят дивиденды (Amazon, Meta) или для быстрорастущих стартапов.</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

        # ------------------------------------------
        # МЕТОД 2: MULTI-STAGE DCF (FCFF)
        # ------------------------------------------
        with tab_dcf:
            col_inputs, col_results = st.columns([1, 2], gap="large")
            with col_inputs:
                st.markdown("#### ⚙️ DCF Assumptions")
                st.session_state.v_state['dcf_fcf'] = st.number_input("Base Free Cash Flow (FCF) $M", value=float(st.session_state.v_state['dcf_fcf']), step=100.0)
                st.session_state.v_state['dcf_g'] = st.slider("FCF Growth Rate (Years 1-5)", min_value=-20.0, max_value=50.0, value=float(st.session_state.v_state['dcf_g']), step=1.0, format="%f%%")
                st.session_state.v_state['dcf_tg'] = st.slider("Terminal Growth Rate (Perpetual)", min_value=0.0, max_value=10.0, value=float(st.session_state.v_state['dcf_tg']), step=0.1, format="%f%%")
                st.session_state.v_state['dcf_wacc'] = st.slider("Discount Rate (WACC)", min_value=1.0, max_value=25.0, value=float(st.session_state.v_state['dcf_wacc']), step=0.5, format="%f%%")
                
                st.markdown("#### 🏢 Capital Structure")
                st.session_state.v_state['dcf_shares'] = st.number_input("Shares Outstanding (Millions)", value=float(st.session_state.v_state['dcf_shares']), step=10.0)
                st.session_state.v_state['dcf_debt'] = st.number_input("Net Debt $M (Total Debt - Cash)", value=float(st.session_state.v_state['dcf_debt']), step=100.0)
                
                fcf_base = st.session_state.v_state['dcf_fcf']
                growth_rate = st.session_state.v_state['dcf_g'] / 100
                terminal_growth = st.session_state.v_state['dcf_tg'] / 100
                wacc = st.session_state.v_state['dcf_wacc'] / 100
                shares_out_dcf = st.session_state.v_state['dcf_shares']
                net_debt_dcf = st.session_state.v_state['dcf_debt']
                
            with col_results:
                st.markdown("#### 📊 DCF Projections & Valuation")
                fcfs, pvs = [], []
                years = ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"]
                
                for year in range(1, 6):
                    fcf = fcf_base * ((1 + growth_rate) ** year)
                    pv = fcf / ((1 + wacc) ** year)
                    fcfs.append(fcf); pvs.append(pv)
                    
                terminal_value = (fcfs[-1] * (1 + terminal_growth)) / (wacc - terminal_growth) if wacc > terminal_growth else 0
                pv_tv = terminal_value / ((1 + wacc) ** 5)
                
                enterprise_val = sum(pvs) + pv_tv
                equity_val = enterprise_val - net_debt_dcf
                intrinsic_value = equity_val / shares_out_dcf if shares_out_dcf > 0 else 0
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Enterprise Value", f"${enterprise_val:,.1f} M")
                m2.metric("Equity Value", f"${equity_val:,.1f} M")
                
                if current_p > 0:
                    upside = ((intrinsic_value - current_p) / current_p) * 100
                    m3.metric("Intrinsic Value per Share", f"${intrinsic_value:,.2f}", f"{upside:+.2f}% Upside", delta_color="normal")
                else:
                    m3.metric("Intrinsic Value per Share", f"${intrinsic_value:,.2f}")
                
                st.markdown("<br>", unsafe_allow_html=True)
                fig_dcf = go.Figure()
                fig_dcf.add_trace(go.Bar(x=years, y=fcfs, name='Projected FCF', marker_color='#b38200'))
                fig_dcf.add_trace(go.Bar(x=years, y=pvs, name='Present Value (Discounted)', marker_color='#d4af37'))
                fig_dcf.update_layout(title="Cash Flow Projections (Next 5 Years)", barmode='group', height=350, margin=dict(l=0, r=0, t=40, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), font=dict(color='#e0d8c8'))
                st.plotly_chart(fig_dcf, use_container_width=True)
                
                if st.button("💾 Sync DCF Value to Watchlist", type="primary", use_container_width=True, key=f"sync_dcf_{selected_ticker}"):
                    df_watchlist.loc[df_watchlist['Stock']==selected_ticker, 'Intrinsic value'] = intrinsic_value
                    df_watchlist.loc[df_watchlist['Stock']==selected_ticker, 'Potential'] = calculate_potential(str(current_p), intrinsic_value)
                    save_db(df_watchlist)
                    st.success(f"Watchlist updated!")
                    
            st.markdown("""
                <div class="guide-box">
                    <h4>💡 Шпаргалка аналитика: Discounted Cash Flow (DCF)</h4>
                    <ul>
                        <li><b>Когда использовать:</b> Золотой стандарт оценки. Используется, когда компания генерирует стабильный и прогнозируемый свободный денежный поток (Free Cash Flow).</li>
                        <li><b>Идеальные кандидаты:</b> Технологические гиганты (Apple, Microsoft), производственные компании, крупные ритейлеры (Walmart).</li>
                        <li><b>Когда НЕ использовать:</b> Для банков и страховых компаний, а также для сверх-рискованных стартапов без денежного потока.</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

        # ------------------------------------------
        # МЕТОД 3: RELATIVE VALUATION
        # ------------------------------------------
        with tab_rel:
            col_inputs, col_results = st.columns([1, 2], gap="large")
            with col_inputs:
                st.markdown("#### ⚙️ Comparable Assumptions")
                opts = ["Earnings per Share (EPS)", "EBITDA $M", "Revenue $M"]
                idx = opts.index(st.session_state.v_state['rel_choice']) if st.session_state.v_state['rel_choice'] in opts else 0
                st.session_state.v_state['rel_choice'] = st.selectbox("Choose Key Metric", opts, index=idx)
                metric_choice = st.session_state.v_state['rel_choice']
                
                if metric_choice == "Earnings per Share (EPS)":
                    st.session_state.v_state['rel_eps'] = st.number_input("Company EPS ($)", value=float(st.session_state.v_state['rel_eps']), step=0.5)
                    st.session_state.v_state['rel_pe'] = st.number_input("Target P/E Multiple (Industry Avg)", value=float(st.session_state.v_state['rel_pe']), step=1.0)
                    base_metric = st.session_state.v_state['rel_eps']
                    target_multiple = st.session_state.v_state['rel_pe']
                elif metric_choice == "EBITDA $M":
                    st.session_state.v_state['rel_ebitda'] = st.number_input("Company EBITDA $M", value=float(st.session_state.v_state['rel_ebitda']), step=50.0)
                    st.session_state.v_state['rel_eveb'] = st.number_input("Target EV/EBITDA Multiple", value=float(st.session_state.v_state['rel_eveb']), step=1.0)
                    st.markdown("#### 🏢 Capital Structure")
                    st.session_state.v_state['rel_sh1'] = st.number_input("Shares Outstanding (Millions)", value=float(st.session_state.v_state['rel_sh1']), step=10.0)
                    st.session_state.v_state['rel_nd1'] = st.number_input("Net Debt $M (Total Debt - Cash)", value=float(st.session_state.v_state['rel_nd1']), step=50.0)
                    base_metric = st.session_state.v_state['rel_ebitda']
                    target_multiple = st.session_state.v_state['rel_eveb']
                    shares_out_rel = st.session_state.v_state['rel_sh1']
                    net_debt_rel = st.session_state.v_state['rel_nd1']
                else: # Revenue
                    st.session_state.v_state['rel_rev'] = st.number_input("Company Revenue $M", value=float(st.session_state.v_state['rel_rev']), step=100.0)
                    st.session_state.v_state['rel_evs'] = st.number_input("Target EV/Sales Multiple", value=float(st.session_state.v_state['rel_evs']), step=0.5)
                    st.markdown("#### 🏢 Capital Structure")
                    st.session_state.v_state['rel_sh2'] = st.number_input("Shares Outstanding (Millions)", value=float(st.session_state.v_state['rel_sh2']), step=10.0)
                    st.session_state.v_state['rel_nd2'] = st.number_input("Net Debt $M", value=float(st.session_state.v_state['rel_nd2']), step=50.0)
                    base_metric = st.session_state.v_state['rel_rev']
                    target_multiple = st.session_state.v_state['rel_evs']
                    shares_out_rel = st.session_state.v_state['rel_sh2']
                    net_debt_rel = st.session_state.v_state['rel_nd2']

            with col_results:
                st.markdown("#### 📊 Relative Valuation")
                
                if metric_choice == "Earnings per Share (EPS)":
                    intrinsic_value = base_metric * target_multiple
                    st.info(f"**Formula:** Implied Share Price = EPS ({base_metric}) × Target P/E ({target_multiple})")
                
                elif metric_choice == "EBITDA $M":
                    implied_ev = base_metric * target_multiple
                    implied_equity = implied_ev - net_debt_rel
                    intrinsic_value = implied_equity / shares_out_rel if shares_out_rel > 0 else 0
                    st.info(f"**Formula:** Implied EV = EBITDA ({base_metric}) × EV/EBITDA ({target_multiple}) = {implied_ev} M<br>Equity Value = EV ({implied_ev}) - Net Debt ({net_debt_rel}) = {implied_equity} M")
                    
                elif metric_choice == "Revenue $M":
                    implied_ev = base_metric * target_multiple
                    implied_equity = implied_ev - net_debt_rel
                    intrinsic_value = implied_equity / shares_out_rel if shares_out_rel > 0 else 0
                    st.info(f"**Formula:** Implied EV = Revenue ({base_metric}) × EV/Sales ({target_multiple}) = {implied_ev} M<br>Equity Value = EV ({implied_ev}) - Net Debt ({net_debt_rel}) = {implied_equity} M")

                m1, m2 = st.columns(2)
                if current_p > 0:
                    upside = ((intrinsic_value - current_p) / current_p) * 100
                    m1.metric("Implied Value per Share", f"${intrinsic_value:,.2f}", f"{upside:+.2f}% Upside", delta_color="normal")
                else:
                    m1.metric("Implied Value per Share", f"${intrinsic_value:,.2f}")
                
                st.markdown("<br><br>", unsafe_allow_html=True)
                if st.button("💾 Sync Relative Value to Watchlist", type="primary", use_container_width=True, disabled=(intrinsic_value<=0), key=f"sync_rel_{selected_ticker}"):
                    df_watchlist.loc[df_watchlist['Stock']==selected_ticker, 'Intrinsic value'] = intrinsic_value
                    df_watchlist.loc[df_watchlist['Stock']==selected_ticker, 'Potential'] = calculate_potential(str(current_p), intrinsic_value)
                    save_db(df_watchlist)
                    st.success(f"Watchlist updated!")

            st.markdown("""
                <div class="guide-box">
                    <h4>💡 Шпаргалка аналитика: Relative Valuation (Мультипликаторы)</h4>
                    <ul>
                        <li><b>P/E (Price to Earnings):</b> Подходит для стабильно прибыльных компаний. Не применять, если прибыль искажена разовыми факторами.</li>
                        <li><b>EV/EBITDA:</b> Отличный универсальный показатель. Нивелирует разницу в долгах и налогах. Идеален для заводов и телекомов.</li>
                        <li><b>EV/Sales:</b> Используется для SaaS, стартапов и компаний, которые активно реинвестируют всё в рост и пока не имеют чистой прибыли.</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

    else:
        st.warning("Your watchlist is empty. Add a company in the Terminal first.")
