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
import datetime

# ==========================================
# 1. PAGE CONFIG & PREMIUM CSS DESIGN
# ==========================================
st.set_page_config(page_title="Pax Valuation", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* Global Background and Text */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Container Padding */
    .block-container { 
        padding-top: 3rem !important; 
        max-width: 95% !important;
    }

    /* Sleek Professional Tabs */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 20px;
        border-bottom: 1px solid #30363d;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent !important;
        border: none !important;
        border-bottom: 3px solid transparent !important;
        border-radius: 0px !important;
        padding: 10px 4px !important; 
        height: auto !important;
    }
    .stTabs [data-baseweb="tab"] p { 
        color: #8b949e !important; 
        font-weight: 500 !important; 
        font-size: 15px !important; 
        margin: 0 !important; 
    }
    .stTabs [aria-selected="true"] { 
        background-color: transparent !important; 
        border-bottom: 3px solid #58a6ff !important; 
    }
    .stTabs [aria-selected="true"] p { 
        color: #ffffff !important; 
        font-weight: 600 !important;
    }
    div[data-baseweb="tab-highlight"] { display: none !important; }

    /* Elevated Metric Cards */
    div[data-testid="metric-container"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    div[data-testid="metric-container"] label {
        color: #8b949e !important;
        font-weight: 500 !important;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* Clean Dividers */
    hr {
        border-color: #30363d !important;
        margin-top: 2rem;
        margin-bottom: 2rem;
    }
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        background-color: transparent !important;
        color: #58a6ff !important;
        font-weight: 600 !important;
    }
    div[data-testid="stExpanderDetails"] {
        border-left: 2px solid #30363d;
        padding-left: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# RATIO EXPLANATIONS
# ==========================================
RATIO_EXPLANATIONS = {
    "Current Ratio": "Liquidity: Measures a company's ability to pay short-term obligations. A ratio > 1 indicates good financial health.",
    "ACID-Test Ratio": "Liquidity: Similar to Current Ratio, but excludes inventory. A stricter measure of a company's ability to pay off current liabilities.",
    "A/R Turnover": "Efficiency: Shows how effectively a company collects its debt. Higher turnover means faster collection from customers.",
    "Inventory Turnover": "Efficiency: Shows how many times a company sold and replaced inventory over a period. Higher generally means strong sales.",
    "Profit Margin": "Profitability: The percentage of revenue remaining as profit after all expenses, taxes, and costs are deducted.",
    "Asset Turnover": "Efficiency: Measures the value of a company's sales or revenues relative to the value of its assets. Higher is better.",
    "ROA": "Profitability (Return on Assets): Shows how profitable a company is relative to its total assets. Indicates management efficiency.",
    "ROE": "Profitability (Return on Equity): Measures a corporation's profitability by revealing how much profit a company generates with the money shareholders have invested.",
    "Debt to Assets": "Solvency: The proportion of a company's assets that are financed by debt. High ratio indicates higher financial risk.",
    "Interest Earned": "Solvency (Times Interest Earned): Measures proportionate amount of income that can be used to cover interest expenses in the future. > 2.5 is usually safe."
}

# ==========================================
# 2. CORE FUNCTIONS & DIRS
# ==========================================
DB_FILE = "watchlist.csv"
FILES_DIR = "analyses"
NOTES_DIR = "notes" 
if not os.path.exists(FILES_DIR): os.makedirs(FILES_DIR)
if not os.path.exists(NOTES_DIR): os.makedirs(NOTES_DIR)

def search_company(query):
    query = str(query).strip()
    if not query: return "", ""
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query)}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            quotes = data.get('quotes', [])
            for q in quotes:
                if q.get('quoteType') in ['EQUITY', 'ETF']:
                    return q.get('symbol', query.upper()), q.get('shortname', query)
            if quotes:
                return quotes[0].get('symbol', query.upper()), quotes[0].get('shortname', query)
    except Exception:
        pass
    return query.upper(), query

def get_current_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        return round(stock.fast_info['last_price'], 2)
    except: return "Error"

def calculate_potential(current_price_str, fair_value):
    try:
        c = float(str(current_price_str).replace('$', '').replace(',', ''))
        f = float(fair_value)
        if c > 0 and f > 0:
            pot = ((f - c) / c) * 100
            return f"+{pot:.2f}%" if pot > 0 else f"{pot:.2f}%"
    except: pass
    return "N/A"

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

def fetch_robust_news(ticker):
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    articles = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            for item in root.findall('./channel/item')[:5]:
                title = item.find('title').text if item.find('title') is not None else "No Title"
                link = item.find('link').text if item.find('link') is not None else "#"
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                if pub_date:
                    pub_date = pub_date.replace(" +0000", "").replace(" GMT", "")
                articles.append({'title': title, 'link': link, 'date': pub_date})
    except Exception:
        pass
    return articles

def find_intrinsic_values(df, is_relative=False):
    target_keywords = ["intrinsic value", "fair value", "target price", "value per share", "implied price", "estimated value"]
    if is_relative: target_keywords.extend(["average", "implied value", "relative value"])
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
                        label = "Consensus Target (Peer Average)" if cell_text_raw.lower() == "average" else (cell_text_raw if cell_text_raw else "Calculated Value")
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
            if len(valid_vals) >= 2:
                headers = row_vals; break
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
                            if peer_name.lower() not in ['nan', 'fy 2025', 'fy 2026', 'item', 'overvalued/undervalued by', '']:
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

if os.path.exists(DB_FILE):
    df_watchlist = pd.read_csv(DB_FILE)
    df_watchlist.rename(columns={"Тикер": "Stock", "Название": "Company name", "Важность": "Interest", "Текущая цена": "Market price", "Справедливая цена": "Intrinsic value", "Потенциал": "Potential", "Файл": "File"}, inplace=True, errors='ignore')
    cols_to_drop = [c for c in ["Status", "Shares", "Avg Cost"] if c in df_watchlist.columns]
    if cols_to_drop: df_watchlist.drop(columns=cols_to_drop, inplace=True)
    df_watchlist.replace({"✅ Yes": "Yes", "❌ No": "No", "✅ Есть": "Yes", "❌ Нет": "No"}, inplace=True)
    if 'Potential' in df_watchlist.columns: df_watchlist['Potential'] = df_watchlist['Potential'].astype(str).str.replace('🟢 ', '').str.replace('🔴 ', '')
else:
    df_watchlist = pd.DataFrame(columns=["Stock", "Company name", "Interest", "Market price", "Intrinsic value", "Potential", "File"])

selected_ticker = st.sidebar.selectbox("Active Company:", df_watchlist['Stock'].tolist()) if not df_watchlist.empty else None
st.sidebar.markdown("---")

# --- ИЗМЕНЕНО: Строгий типографический заголовок без эмблемы ---
def render_header():
    st.markdown("""
        <div style="margin-bottom: 20px;">
            <h1 style="margin: 0; padding: 0; font-size: 2.8rem; font-weight: 800; color: #ffffff; letter-spacing: -1px; line-height: 1;">PAX</h1>
            <p style="margin: 5px 0 0 0; padding: 0; color: #8b949e; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px;">Fundamental Analysis System</p>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. TOP MENU TABS
# ==========================================
tab_watchlist, tab_profile, tab_ratios, tab_val_models, tab_compare, tab_notes = st.tabs([
    "Watchlist", "Company Profile", "Financial Ratios", "Valuation Models", "Compare", "Notes"
])

# --- PAGE 1: WATCHLIST ---
with tab_watchlist:
    render_header()
    col_add, col_upload, col_del = st.columns(3)
    
    with col_add:
        with st.expander("➕ Add New Company"):
            with st.form("add_form", clear_on_submit=True):
                nt = st.text_input("Company Name or Ticker (e.g., Tesla or TSLA)")
                ni = st.selectbox("Interest", ["5 - Critical", "4 - High", "3 - Medium", "2 - Low", "1 - Watch"])
                
                if st.form_submit_button("Add") and nt:
                    with st.spinner(f"Searching database for '{nt}'..."):
                        real_ticker, real_name = search_company(nt)
                        price = get_current_price(real_ticker)
                        new_row = pd.DataFrame([{"Stock": real_ticker, "Company name": real_name, "Interest": ni, "Market price": f"${price}", "Intrinsic value": 0.0, "Potential": "N/A", "File": "No"}])
                        df_watchlist = pd.concat([df_watchlist, new_row], ignore_index=True)
                        df_watchlist.to_csv(DB_FILE, index=False)
                        st.rerun()

    with col_upload:
        with st.expander("📂 Upload Excel Analysis"):
            if not df_watchlist.empty:
                upload_target = st.selectbox("Assign file to:", df_watchlist['Stock'].tolist())
                up_file = st.file_uploader("Select .xlsx file", type="xlsx", label_visibility="collapsed")
                if up_file:
                    path = os.path.join(FILES_DIR, f"{upload_target}.xlsx")
                    with open(path, "wb") as f: f.write(up_file.getbuffer())
                    df_watchlist.loc[df_watchlist['Stock']==upload_target, 'File'] = "Yes"
                    df_watchlist.to_csv(DB_FILE, index=False)
                    st.success(f"File attached to {upload_target}!")
                    st.rerun()

    with col_del:
        with st.expander("❌ Remove Company"):
            with st.form("delete_form"):
                if not df_watchlist.empty:
                    ticker_to_delete = st.selectbox("Select ticker to remove", df_watchlist['Stock'].tolist())
                    if st.form_submit_button("Delete"):
                        df_watchlist = df_watchlist[df_watchlist['Stock'] != ticker_to_delete]
                        df_watchlist.to_csv(DB_FILE, index=False)
                        file_to_delete = os.path.join(FILES_DIR, f"{ticker_to_delete}.xlsx")
                        if os.path.exists(file_to_delete): os.remove(file_to_delete)
                        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.expander("⚙️ Advanced Screener"):
        sc1, sc2 = st.columns(2)
        with sc1:
            filter_interest = st.multiselect("Filter by Interest:", options=["5 - Critical", "4 - High", "3 - Medium", "2 - Low", "1 - Watch"], default=[])
        with sc2:
            use_pot_filter = st.checkbox("Enable Minimum Potential Upside Filter")
            filter_potential = st.number_input("Minimum Upside (%)", value=0.0, step=5.0, disabled=not use_pot_filter)

    col_btn, col_search = st.columns([1, 4])
    with col_btn:
        if st.button("🔄 Update Market Data", use_container_width=True):
            with st.spinner('Fetching prices...'):
                for i, r in df_watchlist.iterrows():
                    p = get_current_price(r['Stock'])
                    if isinstance(p, float):
                        df_watchlist.at[i, 'Market price'] = f"${p}"
                        df_watchlist.at[i, 'Potential'] = calculate_potential(f"${p}", r['Intrinsic value'])
                df_watchlist.to_csv(DB_FILE, index=False)
                st.rerun()
    with col_search:
        search_query = st.text_input("Search", label_visibility="collapsed", placeholder="🔍 Search company or ticker...")

    display_df = df_watchlist.copy()
    
    if search_query:
        mask = display_df['Stock'].str.contains(search_query, case=False, na=False) | display_df['Company name'].str.contains(search_query, case=False, na=False)
        display_df = display_df[mask]

    if filter_interest:
        display_df = display_df[display_df['Interest'].isin(filter_interest)]
        
    if use_pot_filter:
        def parse_potential(val):
            if pd.isna(val) or val in ["N/A", "None", ""]: return -9999.0
            try: return float(str(val).replace('+', '').replace('%', '').strip())
            except: return -9999.0
        display_df['Num_Potential'] = display_df['Potential'].apply(parse_potential)
        display_df = display_df[display_df['Num_Potential'] >= filter_potential]
        display_df.drop(columns=['Num_Potential'], inplace=True)
    
    edited_df = st.data_editor(
        display_df,
        use_container_width=True, hide_index=True,
        column_config={"Interest": st.column_config.SelectboxColumn("Interest", options=["5 - Critical", "4 - High", "3 - Medium", "2 - Low", "1 - Watch"], required=True)},
        disabled=["Stock", "Company name", "Market price", "Intrinsic value", "Potential", "File"]
    )
    
    if not edited_df.equals(display_df):
        df_watchlist.update(edited_df)
        df_watchlist.to_csv(DB_FILE, index=False)
        st.rerun()

# --- PAGE 2: PROFILE ---
with tab_profile:
    render_header()
    if selected_ticker:
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
                fig = go.Figure(data=[go.Candlestick(x=df_h.index, open=df_h['Open'], high=df_h['High'], low=df_h['Low'], close=df_h['Close'])])
                iv_raw = df_watchlist.loc[df_watchlist['Stock']==selected_ticker, 'Intrinsic value'].values[0]
                try:
                    iv_float = float(str(iv_raw).replace('$', '').replace(',', ''))
                    if iv_float > 0:
                        fig.add_hline(
                            y=iv_float, line_dash="dash", line_color="#E04F5F", 
                            annotation_text=f"Intrinsic Value: ${iv_float:,.2f}", 
                            annotation_position="bottom right", annotation_font_color="#E04F5F", annotation_font_size=12
                        )
                except: pass
                fig.update_layout(height=500, margin=dict(l=0,r=0,t=10,b=0), xaxis_rangeslider_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
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
        else:
            st.info("No recent news found for this ticker.")
            
    else: st.warning("Select a company in the sidebar.")

# --- PAGE 3: RATIOS ---
with tab_ratios:
    render_header()
    if selected_ticker:
        st.subheader(f"Financial Ratios: {selected_ticker}")
        path = os.path.join(FILES_DIR, f"{selected_ticker}.xlsx")
        if os.path.exists(path):
            xls = pd.ExcelFile(path)
            if 'Ratios' in xls.sheet_names:
                df = pd.read_excel(path, sheet_name='Ratios')
                key_metrics = extract_key_ratios(df)
                if key_metrics:
                    latest_year = key_metrics.pop("_latest_year", "Latest")
                    st.write(f"**Key Performance Indicators ({latest_year})**")
                    cols = st.columns(5)
                    for i, (name, val) in enumerate(key_metrics.items()):
                        tooltip_text = RATIO_EXPLANATIONS.get(name, "Financial Metric")
                        with cols[i % 5]: st.metric(label=name, value=val, help=tooltip_text)
                        if (i + 1) % 5 == 0: st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("<hr>", unsafe_allow_html=True)
                
                st.subheader("Fundamental Trends Visualization")
                year_cols = [c for c in df.columns if re.search(r'(20\d{2})', str(c))]
                if year_cols:
                    valid_rows = df[df.iloc[:, 0].notna()]
                    raw_metrics_list = valid_rows.iloc[:, 0].astype(str).tolist()
                    metrics_list = []
                    ignore_words = ["name", "item", "ratios", "metric", "metrics", "-", "unnamed"]
                    for m in raw_metrics_list:
                        m_clean = m.strip()
                        if m_clean and not m_clean.lower().startswith('unnamed') and m_clean.lower() not in ignore_words and m_clean not in metrics_list:
                            metrics_list.append(m_clean)
                    if metrics_list:
                        selected_metric = st.selectbox("Select Metric to Visualize over Time:", metrics_list)
                        if selected_metric:
                            row_data = df[df.iloc[:, 0].astype(str).str.strip() == selected_metric].iloc[0]
                            y_values, x_years = [], []
                            for yc in year_cols:
                                try:
                                    num = float(str(row_data[yc]).replace(',', '').replace('%', '').strip())
                                    y_values.append(num); x_years.append(str(yc))
                                except: pass
                            if y_values:
                                fig_bar = go.Figure(data=[go.Bar(x=x_years, y=y_values, marker_color="#58a6ff", textposition="auto")])
                                fig_bar.update_layout(title=f"{selected_metric} Trend", height=400, margin=dict(l=0, r=0, t=40, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                                st.plotly_chart(fig_bar, use_container_width=True)
                st.markdown("<hr>", unsafe_allow_html=True)
                with st.expander("View Full Raw Data", expanded=not bool(key_metrics)): st.dataframe(clean_excel_data(df), use_container_width=True, height=(len(df)*35)+40)
            else: st.error("Sheet 'Ratios' not found.")
        else: st.info("No file attached for this company.")

# --- PAGE 4: VALUATION MODELS ---
with tab_val_models:
    render_header()
    if selected_ticker:
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
                                    if isinstance(current_p, (int, float)) and current_p > 0:
                                        st.metric(label=f"Implied by {clean_peer}", value=f"${val:,.2f}", delta=f"{((val - current_p) / current_p) * 100:.2f}%")
                                    else: st.metric(label=f"Implied by {clean_peer}", value=f"${val:,.2f}")
                            if st.button(f"Sync Average ({item['Metric']}): ${avg_val:,.2f}", key=f"sync_{selected_ticker}_{item['Metric']}"):
                                df_watchlist.loc[df_watchlist['Stock']==selected_ticker, 'Intrinsic value'] = avg_val
                                df_watchlist.loc[df_watchlist['Stock']==selected_ticker, 'Potential'] = calculate_potential(df_watchlist.loc[df_watchlist['Stock']==selected_ticker, 'Market price'].values[0], avg_val)
                                df_watchlist.to_csv(DB_FILE, index=False); st.success(f"Watchlist updated!")
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
                                if isinstance(current_p, (int, float)) and current_p > 0:
                                    st.metric(label="Upside / Downside", value=f"{abs(((val - current_p) / current_p) * 100):.2f}%", delta=f"{((val - current_p) / current_p) * 100:.2f}%")
                            if st.button(f"Sync '{label}' (${val:,.2f}) to Watchlist", key=f"sync_{selected_ticker}_{label}_{val}"):
                                df_watchlist.loc[df_watchlist['Stock']==selected_ticker, 'Intrinsic value'] = val
                                df_watchlist.loc[df_watchlist['Stock']==selected_ticker, 'Potential'] = calculate_potential(df_watchlist.loc[df_watchlist['Stock']==selected_ticker, 'Market price'].values[0], val)
                                df_watchlist.to_csv(DB_FILE, index=False); st.success(f"Watchlist updated!")
                            st.markdown("<br>", unsafe_allow_html=True)
                    else: st.info("Could not auto-detect final values in this sheet.")
                st.markdown("<hr>", unsafe_allow_html=True)
                with st.expander("View Raw Calculation Data (Full Spreadsheet)"): st.dataframe(clean_excel_data(df), use_container_width=True, height=500)
            else: st.warning("No Valuation models found in this file.")
        else: st.info("No file attached.")

# --- PAGE 5: COMPARE ---
with tab_compare:
    render_header()
    st.subheader("Peer Comparison Dashboard")
    if not df_watchlist.empty:
        all_tickers = df_watchlist['Stock'].tolist()
        tickers_to_compare = st.multiselect("Select companies to compare:", options=all_tickers, default=all_tickers[:3] if len(all_tickers) >= 3 else all_tickers)
        if len(tickers_to_compare) > 0:
            compare_data = {}
            with st.spinner('Compiling fundamental data...'):
                for t in tickers_to_compare:
                    row = df_watchlist[df_watchlist['Stock'] == t]
                    comp_info = {"Market Price": str(row['Market price'].values[0]) if not row.empty else "N/A", "Intrinsic Value": str(row['Intrinsic value'].values[0]) if not row.empty else "N/A", "Potential": str(row['Potential'].values[0]) if not row.empty else "N/A"}
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
                    compare_data[t] = comp_info
            df_compare = pd.DataFrame(compare_data); df_compare.fillna("N/A", inplace=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.dataframe(df_compare, use_container_width=True, height=(len(df_compare) * 36) + 43)
        else: st.info("Select at least one company to see the comparison.")
    else: st.info("Your watchlist is empty. Add companies first.")

# --- PAGE 6: NOTES ---
with tab_notes:
    render_header()
    if selected_ticker:
        st.subheader(f"📝 Investment Thesis & Notes: {selected_ticker}")
        st.write(f"Document your fundamental analysis, key risks, and buying rationale for **{selected_ticker}** below.")
        
        note_path = os.path.join(NOTES_DIR, f"{selected_ticker}_notes.txt")
        existing_note = ""
        if os.path.exists(note_path):
            with open(note_path, "r", encoding="utf-8") as f: existing_note = f.read()
            
        new_note = st.text_area(
            "Editor (Markdown supported)", 
            value=existing_note, 
            height=500, 
            label_visibility="collapsed",
            placeholder="Example:\n\n### Bull Case\n* Strong moat in cloud computing.\n* Consistent 20%+ ROE over the last 5 years.\n\n### Bear Case\n* High valuation (P/E > 30).\n* Regulatory risks in Europe.\n\n**Action Plan:** Will initiate position if price drops below $120.",
            key=f"note_editor_{selected_ticker}" 
        )
        
        if st.button("💾 Save Notes", type="primary", key=f"save_btn_{selected_ticker}"):
            with open(note_path, "w", encoding="utf-8") as f: f.write(new_note)
            st.success("Investment notes saved securely!")
    else:
        st.warning("Select a company in the sidebar to start writing notes.")
