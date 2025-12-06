import streamlit as st
import requests
import concurrent.futures
import time
import re
import pandas as pd
import json

# --- FAILSAFE IMPORT ---
try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Proxy Master Pro",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="auto"
)

# --- CSS FOR RESPONSIVENESS ---
st.markdown("""
    <style>
    .stApp {background-color: #0e1117;}
    .footer {
        width: 100%;
        background-color: #262730;
        color: #bababa;
        text-align: center;
        padding: 15px;
        margin-top: 50px;
        border-radius: 10px;
        border: 1px solid #464b5c;
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE ---
if 'proxy_text' not in st.session_state: st.session_state.proxy_text = ""
if 'results' not in st.session_state: st.session_state.results = []
if 'check_done' not in st.session_state: st.session_state.check_done = False
if 'ftp_results' not in st.session_state: st.session_state.ftp_results = []

# --- CONSTANTS ---
DEFAULT_TARGETS = """http://10.16.100.244/
http://172.16.50.4/
http://new.circleftp.net/"""

# --- FUNCTIONS ---
def get_real_ip():
    try: return requests.get("https://api.ipify.org", timeout=3).text
    except: return "Unknown"

def fetch_from_url(url):
    try:
        resp = requests.get(url, timeout=10)
        return resp.text if resp.status_code == 200 else None
    except: return None

# 1. General Connectivity Check (Internet)
def check_proxy_basic(proxy_data, timeout, real_ip):
    ip, port, protocol = proxy_data['ip'], proxy_data['port'], proxy_data['protocol']
    proxy_conf = {
        "http": f"{protocol}://{ip}:{port}",
        "https": f"{protocol}://{ip}:{port}",
    }
    result = {
        "IP": ip, "Port": port, "Protocol": protocol.upper(),
        "Country": "-", "Latency": 99999, "Status": "Dead", 
        "Full_Address": f"{ip}:{port}"
    }
    try:
        start = time.time()
        # Check against Google/Httpbin for general internet
        resp = requests.get("http://httpbin.org/get", proxies=proxy_conf, timeout=timeout)
        latency = round((time.time() - start) * 1000)
        
        if resp.status_code == 200:
            result['Latency'] = latency
            result['Status'] = "Working"
            try:
                geo = requests.get(f"http://ip-api.com/json/{ip}", timeout=2).json()
                if geo['status'] == 'success': result['Country'] = geo['countryCode']
            except: pass
    except: pass
    return result

# 2. Specific Target Check (FTP/BDIX)
def check_specific_target(proxy_data, target_urls, timeout):
    # Note: Phase 1 might return different keys, ensuring compatibility
    ip = proxy_data.get('IP') or proxy_data.get('ip')
    port = proxy_data.get('Port') or proxy_data.get('port')
    protocol = proxy_data.get('Protocol') or proxy_data.get('protocol')
    protocol = protocol.lower()

    proxy_conf = {
        "http": f"{protocol}://{ip}:{port}",
        "https": f"{protocol}://{ip}:{port}",
    }
    
    # Store results for this specific proxy
    proxy_result = {"Proxy": f"{ip}:{port}"}
    
    for url in target_urls:
        url = url.strip()
        if not url: continue
        try:
            # Short timeout (5s) because internal IPs usually connect fast or fail fast
            resp = requests.get(url, proxies=proxy_conf, timeout=5) 
            if resp.status_code == 200:
                proxy_result[url] = "✅ OPEN"
            else:
                proxy_result[url] = f"⚠️ ({resp.status_code})"
        except:
            proxy_result[url] = "❌"
            
    return proxy_result

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Proxy Master")
    st.caption("Created by **RAKIB**")
    st.divider()
    
    st.markdown("### ⚙️ General Settings")
    threads = st.slider("Threads", 5, 50, 25)
    timeout = st.slider("General Timeout", 1, 15, 5)
    force_proto = st.selectbox("Protocol", ["AUTO", "http", "socks4", "socks5"])
    
    st.info("Note: Phase 2 now checks ALL proxies (including dead ones) against your target list.")

# --- MAIN UI ---
st.title("🚀 Proxy & FTP/BDIX Checker")
st.markdown(f"**Created by RAKIB**")

# INPUT SECTION
tab1, tab2 = st.tabs(["📋 Proxies", "🎯 FTP/Target List"])

with tab1:
    st.session_state.proxy_text = st.text_area(
        "Paste Proxies", value=st.session_state.proxy_text, height=150, 
        placeholder="103.141.67.50 9090", label_visibility="collapsed"
    )
    c1, c2 = st.columns(2)
    if c1.button("🗑️ Clear", use_container_width=True):
        st.session_state.proxy_text = ""
        st.session_state.results = []
        st.session_state.ftp_results = []
        st.session_state.check_done = False
        st.rerun()
    if c2.button("🧹 Remove Dupes", use_container_width=True):
        raw = st.session_state.proxy_text.strip().split('\n')
        unique = sorted(list(set([l.strip() for l in raw if l.strip()])))
        st.session_state.proxy_text = "\n".join(unique)
        st.rerun()

with tab2:
    st.info("Enter IPs (like 10.16...) or Websites. All proxies will try to open these.")
    target_text = st.text_area("Target URLs (One per line)", value=DEFAULT_TARGETS, height=150)

# START BUTTON
if st.button("▶ START CHECKING PROCESS", type="primary", use_container_width=True):
    # 1. RESET
    st.session_state.results = []
    st.session_state.ftp_results = []
    st.session_state.check_done = False
    
    # 2. PARSE PROXIES
    lines = st.session_state.proxy_text.strip().split('\n')
    proxies_to_check = []
    seen = set()
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
        # 3. PHASE 1: CHECK INTERNET CONNECTIVITY
        st.subheader("Phase 1: Checking Internet Connectivity...")
        real_ip = get_real_ip()
        results_temp = []
        bar = st.progress(0)
        status = st.empty()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_proxy = {executor.submit(check_proxy_basic, p, timeout, real_ip): p for p in proxies_to_check}
            completed = 0
            for future in concurrent.futures.as_completed(future_to_proxy):
                results_temp.append(future.result())
                completed += 1
                bar.progress(completed / len(proxies_to_check))
                status.caption(f"Phase 1: {completed}/{len(proxies_to_check)}")
        
        st.session_state.results = results_temp
        
        # 4. PHASE 2: CHECK FTP/TARGETS (ALL PROXIES)
        # UPDATED: We now take ALL results, regardless of status
        st.subheader(f"Phase 2: Testing ALL {len(results_temp)} Proxies against Targets...")
        target_list = target_text.strip().split('\n')
        ftp_temp = []
        
        bar.progress(0)
        completed = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            # We pass ALL results_temp (even dead ones)
            future_to_ftp = {executor.submit(check_specific_target, p, target_list, 5): p for p in results_temp}
            
            for future in concurrent.futures.as_completed(future_to_ftp):
                ftp_temp.append(future.result())
                completed += 1
                bar.progress(completed / len(results_temp))
                status.caption(f"Phase 2: Checking FTPs {completed}/{len(results_temp)}")
        
        st.session_state.ftp_results = ftp_temp
        
        st.session_state.check_done = True
        status.empty()
        bar.empty()
        st.rerun()

# --- RESULTS DISPLAY ---
if st.session_state.check_done:
    df = pd.DataFrame(st.session_state.results)
    df_working = df[df['Status'] == "Working"]
    df_dead = df[df['Status'] == "Dead"]
    
    st.divider()
    
    # METRICS
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Checked", len(df))
    m2.metric("✅ Internet Alive", len(df_working))
    m3.metric("🎯 Target Checks", len(st.session_state.ftp_results))

    # TABS
    res_tab1, res_tab2, res_tab3 = st.tabs(["🎯 Target Access Matrix (All)", "✅ Internet Working", "❌ Internet Dead"])

    # TAB 1: FTP MATRIX (The new feature)
    with res_tab1:
        if st.session_state.ftp_results:
            st.markdown("This matrix shows results for **ALL** proxies (Alive & Dead) against your targets.")
            df_ftp = pd.DataFrame(st.session_state.ftp_results)
            
            # Highlight cells containing "OPEN"
            def highlight_open(val):
                if 'OPEN' in str(val): return 'background-color: #d4edda; color: black; font-weight: bold'
                if '⚠️' in str(val): return 'background-color: #fff3cd; color: black'
                return ''

            st.dataframe(df_ftp.style.applymap(highlight_open), use_container_width=True)
            
            # Export Matrix
            csv_ftp = df_ftp.to_csv(index=False).encode('utf-8')
            st.download_button("📊 Download FTP Matrix (CSV)", csv_ftp, "rakib_ftp_check.csv", "text/csv", use_container_width=True)
        else:
            st.info("No results.")

    # TAB 2: GENERAL WORKING
    with res_tab2:
        if not df_working.empty:
            sel_w = st.dataframe(
                df_working,
                column_config={"Latency": st.column_config.NumberColumn(format="%d ms"), "Full_Address": None},
                use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row"
            )
            rows = sel_w.selection.rows
            if rows:
                txt = "\n".join(df_working.iloc[rows]['Full_Address'].tolist())
                st.code(txt, language="text")
            else:
                with st.expander("Copy All Working IPs"):
                    st.code("\n".join(df_working['Full_Address'].tolist()))
        else:
            st.warning("No proxies have general internet access.")

    # TAB 3: DEAD
    with res_tab3:
        if not df_dead.empty:
            st.info("These proxies failed the Internet check, but check the 'Target Access Matrix' tab—they might work for FTPs!")
            st.dataframe(df_dead[['IP', 'Port', 'Status']], use_container_width=True, hide_index=True)

# --- FOOTER ---
st.markdown("""
<div class="footer">
    Developed with ❤️ by <b>RAKIB</b><br>
    <small>BDIX & FTP Checker Supported</small>
</div>
""", unsafe_allow_html=True)
