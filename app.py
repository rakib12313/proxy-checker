import streamlit as st
import requests
import concurrent.futures
import time
import re
import pandas as pd
import json
import plotly.express as px

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Proxy Master by RAKIB",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp {background-color: #0e1117;}
    .metric-card {
        background-color: #262730;
        border: 1px solid #464b5c;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #262730;
        color: white;
        text-align: center;
        padding: 10px;
        border-top: 1px solid #464b5c;
        font-size: 14px;
        z-index: 100;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE ---
if 'proxy_text' not in st.session_state: st.session_state.proxy_text = ""
if 'results' not in st.session_state: st.session_state.results = []
if 'check_done' not in st.session_state: st.session_state.check_done = False

# --- CONSTANTS ---
GEO_URL = "http://ip-api.com/json/"

# --- FUNCTIONS ---
def get_real_ip():
    try:
        return requests.get("https://api.ipify.org", timeout=3).text
    except:
        return "Unknown"

def fetch_from_url(url):
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200: return resp.text
        return None
    except:
        return None

def check_proxy(proxy_data, timeout, target_url, real_ip):
    ip = proxy_data['ip']
    port = proxy_data['port']
    protocol = proxy_data['protocol']
    
    proxy_conf = {
        "http": f"{protocol}://{ip}:{port}",
        "https": f"{protocol}://{ip}:{port}",
    }

    result = {
        "IP": ip, "Port": port, "Protocol": protocol.upper(),
        "Country": "-", "Anonymity": "-", "Latency": 99999,
        "Status": "Dead", "Full_Address": f"{ip}:{port}"
    }

    try:
        start = time.time()
        # Custom Target Check
        resp = requests.get(target_url, proxies=proxy_conf, timeout=timeout)
        latency = round((time.time() - start) * 1000)
        
        if resp.status_code == 200:
            result['Latency'] = latency
            result['Status'] = "Working"
            
            # Metadata Checks (Only run if target is the judge, OR run separately)
            # To keep it fast/compatible with custom targets, we do a lightweight Geo check
            try:
                geo_resp = requests.get(f"{GEO_URL}{ip}", timeout=2).json()
                if geo_resp['status'] == 'success':
                    result['Country'] = geo_resp['countryCode']
            except:
                pass

            # Simple Anonymity Guess (If headers present)
            try:
                # If target is httpbin, we can be accurate
                if "httpbin" in target_url:
                    json_resp = resp.json()
                    origin = json_resp.get('origin', '')
                    if real_ip in origin: result['Anonymity'] = "Transparent"
                    else: result['Anonymity'] = "Elite/Anon"
                else:
                    result['Anonymity'] = "N/A" # Can't judge anon on Google
            except:
                result['Anonymity'] = "-"
    except:
        pass
    
    return result

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Proxy Master")
    st.caption("Created by **RAKIB**")
    st.divider()
    
    st.header("⚙️ Configuration")
    target_option = st.selectbox("Test Target", 
                                 ["http://httpbin.org/get (Default)", "https://www.google.com", "https://www.bing.com", "Custom URL"])
    
    if target_option == "Custom URL":
        target_url = st.text_input("Enter URL", "https://example.com")
    elif "httpbin" in target_option:
        target_url = "http://httpbin.org/get"
    elif "google" in target_option:
        target_url = "https://www.google.com"
    else:
        target_url = "https://www.bing.com"

    st.write(f"**Target:** `{target_url}`")
    
    threads = st.slider("Threads", 5, 50, 25)
    timeout = st.number_input("Timeout (sec)", value=10, min_value=1)
    force_proto = st.selectbox("Force Protocol", ["AUTO", "http", "socks4", "socks5"])
    
    st.markdown("---")
    st.info("Tip: 'httpbin' is best for detecting Anonymity levels. 'Google' is best for SEO checks.")

# --- MAIN UI ---
st.title("🚀 Proxy Checker & Organizer")
st.markdown(f"**Created by RAKIB** | *Professional Edition*")

# INPUT SECTION
tab_in1, tab_in2 = st.tabs(["📋 Paste List", "🌐 Load from URL"])

with tab_in1:
    st.session_state.proxy_text = st.text_area(
        "Paste Proxies", value=st.session_state.proxy_text, height=150, 
        placeholder="103.141.67.50 9090\n113.212.109.40 1080 socks5", label_visibility="collapsed"
    )
    c1, c2 = st.columns([1, 4])
    if c1.button("🗑️ Clear", use_container_width=True):
        st.session_state.proxy_text = ""
        st.session_state.results = []
        st.session_state.check_done = False
        st.rerun()
    if c2.button("🧹 Remove Duplicates", use_container_width=True):
        raw = st.session_state.proxy_text.strip().split('\n')
        unique = sorted(list(set([l.strip() for l in raw if l.strip()])))
        st.session_state.proxy_text = "\n".join(unique)
        st.toast(f"Removed duplicates. Total: {len(unique)}")
        st.rerun()

with tab_in2:
    url_input = st.text_input("Enter URL")
    if st.button("📥 Load URL"):
        with st.spinner("Downloading..."):
            data = fetch_from_url(url_input)
            if data:
                st.session_state.proxy_text = data
                st.success("Loaded!")
                st.rerun()
            else:
                st.error("Failed to load URL.")

# START BUTTON
if st.button("▶ START CHECK", type="primary", use_container_width=True):
    st.session_state.results = []
    st.session_state.check_done = False
    
    lines = st.session_state.proxy_text.strip().split('\n')
    proxies_to_check = []
    seen = set()
    
    # Parse
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            ip, port = parts[0], parts[1]
            if f"{ip}:{port}" not in seen:
                seen.add(f"{ip}:{port}")
                proto = force_proto if force_proto != "AUTO" else "http"
                if force_proto == "AUTO":
                    if "socks5" in line.lower(): proto = "socks5"
                    elif "socks4" in line.lower(): proto = "socks4"
                    elif "https" in line.lower(): proto = "https"
                
                if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
                    proxies_to_check.append({"ip": ip, "port": port, "protocol": proto})

    if not proxies_to_check:
        st.warning("No valid proxies found.")
    else:
        real_ip = get_real_ip()
        results_temp = []
        bar = st.progress(0)
        status_txt = st.empty()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_proxy = {executor.submit(check_proxy, p, timeout, target_url, real_ip): p for p in proxies_to_check}
            completed = 0
            for future in concurrent.futures.as_completed(future_to_proxy):
                data = future.result()
                results_temp.append(data)
                completed += 1
                bar.progress(completed / len(proxies_to_check))
                status_txt.caption(f"Checking {completed}/{len(proxies_to_check)}")
        
        st.session_state.results = results_temp
        st.session_state.check_done = True
        bar.empty()
        status_txt.empty()
        st.rerun()

# --- DASHBOARD & RESULTS ---
if st.session_state.check_done:
    df = pd.DataFrame(st.session_state.results)
    
    # Segregate
    df_working = df[df['Status'] == "Working"].copy()
    df_dead = df[df['Status'] == "Dead"].copy()
    
    st.divider()
    
    # --- 1. ANALYTICS DASHBOARD ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Checked", len(df))
    m2.metric("✅ Working", len(df_working), delta_color="normal")
    m3.metric("❌ Failed", len(df_dead), delta_color="inverse")
    
    avg_speed = int(df_working['Latency'].mean()) if not df_working.empty else 0
    m4.metric("Avg Speed", f"{avg_speed} ms")

    # --- 2. ADVANCED FILTERS (Only shows if there are working proxies) ---
    if not df_working.empty:
        st.subheader("🔍 Filter Results")
        col_f1, col_f2 = st.columns(2)
        
        # Country Filter
        available_countries = sorted(df_working['Country'].unique().tolist())
        selected_countries = col_f1.multiselect("Filter by Country", available_countries, default=available_countries)
        
        # Speed Filter
        max_speed = int(df_working['Latency'].max())
        latency_filter = col_f2.slider("Max Latency (ms)", 0, max_speed, max_speed)
        
        # Apply Filters
        df_display = df_working[
            (df_working['Country'].isin(selected_countries)) & 
            (df_working['Latency'] <= latency_filter)
        ].sort_values(by="Latency")
    else:
        df_display = df_working # Empty

    # --- 3. CHARTS ---
    if not df_display.empty:
        with st.expander("📊 Show Visualizations", expanded=False):
            c_chart1, c_chart2 = st.columns(2)
            # Pie Chart: Country
            fig_pie = px.pie(df_display, names='Country', title='Country Distribution', hole=0.3)
            c_chart1.plotly_chart(fig_pie, use_container_width=True)
            # Bar Chart: Protocol
            fig_bar = px.bar(df_display['Protocol'].value_counts(), title="Protocol Count")
            c_chart2.plotly_chart(fig_bar, use_container_width=True)

    # --- 4. DATA TABLES & COPY ---
    st.subheader("📋 Detailed Lists")
    res_tab1, res_tab2, res_tab3 = st.tabs([
        f"✅ Working ({len(df_display)})", 
        f"❌ Failed ({len(df_dead)})",
        "📂 Export All"
    ])
    
    # Working Tab
    with res_tab1:
        if not df_display.empty:
            col_tbl, col_act = st.columns([3, 1])
            with col_tbl:
                sel_w = st.dataframe(
                    df_display,
                    column_config={
                        "Latency": st.column_config.NumberColumn(format="%d ms"),
                        "Status": st.column_config.TextColumn(width="small"),
                        "Full_Address": None
                    },
                    use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row"
                )
            with col_act:
                # Dynamic Copy
                rows = sel_w.selection.rows
                if rows:
                    txt = "\n".join(df_display.iloc[rows]['Full_Address'].tolist())
                    st.info(f"{len(rows)} Selected")
                    st.code(txt, language="text")
                else:
                    st.caption("Select rows to copy specific proxies, or use button below.")
                    full_txt = "\n".join(df_display['Full_Address'].tolist())
                    st.download_button("Download Filtered List", full_txt, "filtered_proxies.txt")
        else:
            st.warning("No proxies match your filters.")

    # Dead Tab
    with res_tab2:
        if not df_dead.empty:
            st.dataframe(df_dead[['IP', 'Port', 'Protocol', 'Status']], use_container_width=True, hide_index=True)
            dead_txt = "\n".join(df_dead['Full_Address'].tolist())
            with st.expander("Copy Dead List"):
                st.code(dead_txt, language="text")
        else:
            st.success("Zero failures! Amazing list.")

    # Export Tab
    with res_tab3:
        st.write("Download Full Report (Filtered + Dead)")
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button("📊 Download Complete CSV", csv_data, "rakib_proxy_full.csv", "text/csv")

# --- FOOTER ---
st.markdown("""
<div class="footer">
    Developed with ❤️ by <b>RAKIB</b> | Ultimate Proxy Tool v2.0
</div>
""", unsafe_allow_html=True)
