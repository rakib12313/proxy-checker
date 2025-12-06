import streamlit as st
import requests
import concurrent.futures
import time
import re
import pandas as pd
from datetime import datetime

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
    initial_sidebar_state="collapsed"
)

# --- APPLE GLASS UI THEME (CSS) ---
st.markdown("""
    <style>
    /* 1. ANIMATED BACKGROUND */
    .stApp {
        background: linear-gradient(-45deg, #000428, #004e92, #0f0c29, #302b63, #24243e);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    }
    @keyframes gradient {
        0% {background-position: 0% 50%;}
        50% {background-position: 100% 50%;}
        100% {background-position: 0% 50%;}
    }

    /* 2. GLASSMORPHISM CARD STYLE */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }

    /* 3. INPUT AREAS */
    .stTextArea textarea, .stTextInput input {
        background-color: rgba(0, 0, 0, 0.3) !important;
        color: #e0e0e0 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
    }
    .stTextArea textarea:focus {
        border-color: #007aff !important;
        box-shadow: 0 0 10px rgba(0, 122, 255, 0.3);
    }

    /* 4. BUTTONS (Apple Style Pills) */
    div.stButton > button {
        background: linear-gradient(135deg, #007aff 0%, #005ecb 100%);
        color: white;
        border: none;
        border-radius: 20px;
        padding: 10px 24px;
        font-weight: 500;
        transition: transform 0.2s, box-shadow 0.2s;
        box-shadow: 0 4px 15px rgba(0, 122, 255, 0.3);
    }
    div.stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 20px rgba(0, 122, 255, 0.5);
    }
    /* Secondary Button (Clear/Remove) style tweak via CSS selectors is hard in streamlit, 
       so we stick to the primary style for consistency */

    /* 5. METRICS */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.05);
        padding: 15px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
    }
    [data-testid="stMetricValue"] {
        font-size: 24px;
        color: #ffffff;
    }
    [data-testid="stMetricLabel"] {
        color: #a1a1aa;
    }

    /* 6. TERMINAL LOG */
    .terminal-container {
        background: rgba(0, 0, 0, 0.6);
        border-radius: 12px;
        border: 1px solid #333;
        padding: 15px;
        font-family: 'SF Mono', 'Menlo', 'Monaco', 'Courier New', monospace;
        font-size: 12px;
        color: #00ff9d;
        height: 200px;
        overflow-y: auto;
        box-shadow: inset 0 0 20px rgba(0,0,0,0.5);
    }

    /* 7. DATAFRAME / TABLES */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        overflow: hidden;
    }

    /* 8. FOOTER */
    .glass-footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background: rgba(22, 22, 22, 0.8);
        backdrop-filter: blur(10px);
        color: #888;
        text-align: center;
        padding: 10px;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        z-index: 100;
    }
    
    /* HIDE STREAMLIT BRANDING */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* CUSTOM HEADERS */
    h1, h2, h3 {
        color: #ffffff;
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE ---
if 'proxy_text' not in st.session_state: st.session_state.proxy_text = ""
if 'results' not in st.session_state: st.session_state.results = []
if 'check_done' not in st.session_state: st.session_state.check_done = False
if 'ftp_results' not in st.session_state: st.session_state.ftp_results = []
if 'logs' not in st.session_state: st.session_state.logs = []

# --- CONSTANTS ---
DEFAULT_TARGETS = """http://10.16.100.244/
http://172.16.50.4/
http://new.circleftp.net/
http://ftp.samonline.net/"""

# --- FUNCTIONS ---
def log_event(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {message}")
    if len(st.session_state.logs) > 60:
        st.session_state.logs.pop(0)

def get_real_ip():
    try: return requests.get("https://api.ipify.org", timeout=3).text
    except: return "Unknown"

def fetch_from_url(url):
    try:
        resp = requests.get(url, timeout=10)
        return resp.text if resp.status_code == 200 else None
    except: return None

# 1. General Check
def check_proxy_basic(proxy_data, timeout, real_ip):
    ip, port, protocol = proxy_data['ip'], proxy_data['port'], proxy_data['protocol']
    proxy_conf = {
        "http": f"{protocol}://{ip}:{port}",
        "https": f"{protocol}://{ip}:{port}",
    }
    result = {
        "IP": ip, "Port": port, "Protocol": protocol.upper(),
        "Country": "-", "ISP": "Unknown", "Latency": 99999, "Status": "Dead", 
        "Full_Address": f"{ip}:{port}"
    }
    try:
        start = time.time()
        resp = requests.get("http://httpbin.org/get", proxies=proxy_conf, timeout=timeout)
        latency = round((time.time() - start) * 1000)
        
        if resp.status_code == 200:
            result['Latency'] = latency
            result['Status'] = "Working"
            try:
                geo = requests.get(f"http://ip-api.com/json/{ip}", timeout=2).json()
                if geo['status'] == 'success': 
                    result['Country'] = geo['countryCode']
                    result['ISP'] = geo['isp']
            except: pass
    except: pass
    return result

# 2. Target Check
def check_specific_target(proxy_data, target_urls, timeout):
    ip = proxy_data.get('IP') or proxy_data.get('ip')
    port = proxy_data.get('Port') or proxy_data.get('port')
    protocol = proxy_data.get('Protocol') or proxy_data.get('protocol')
    protocol_lower = protocol.lower()

    proxy_conf = {
        "http": f"{protocol_lower}://{ip}:{port}",
        "https": f"{protocol_lower}://{ip}:{port}",
    }
    
    isp_info = proxy_data.get('ISP', 'Unknown')
    proxy_label = f"{ip}:{port}"
    if isp_info != 'Unknown':
        proxy_label += f" ({isp_info})"

    proxy_result = {
        "Proxy": proxy_label, 
        "Type": protocol.upper(), 
        "Raw_IP": f"{ip}:{port}"
    }
    
    for url in target_urls:
        url = url.strip()
        if not url: continue
        try:
            resp = requests.get(url, proxies=proxy_conf, timeout=5) 
            if resp.status_code == 200:
                proxy_result[url] = "✅ 200 OK"
            elif resp.status_code == 403:
                proxy_result[url] = "⛔ 403"
            elif resp.status_code == 404:
                proxy_result[url] = "⚠️ 404"
            else:
                proxy_result[url] = f"⚠️ {resp.status_code}"
        except:
            proxy_result[url] = "❌"
            
    return proxy_result

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## 🛡️ Proxy Master")
    st.caption("Created by **RAKIB**")
    st.divider()
    
    st.markdown("### ⚙️ Engine Config")
    threads = st.slider("Threads", 5, 50, 25)
    timeout = st.slider("Timeout", 1, 15, 6)
    force_proto = st.selectbox("Force Protocol", ["AUTO", "http", "socks4", "socks5"])
    
    st.divider()
    st.markdown("""
    <div style='background: rgba(255,255,255,0.1); padding: 10px; border-radius: 10px; font-size: 12px;'>
    <b>Pro Tip:</b><br>
    The Matrix tab detects which specific BDIX server works for each proxy.
    </div>
    """, unsafe_allow_html=True)

# --- HEADER AREA ---
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.title("Proxy Master Pro")
    st.markdown("<span style='color: #007aff; font-weight: bold;'>BDIX INTELLIGENCE SYSTEM</span>", unsafe_allow_html=True)
with col_h2:
    if st.button("🔄 Refresh App", use_container_width=True):
        st.rerun()

st.write("") # Spacer

# --- INPUT SECTION (GLASS CARD) ---
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
tab1, tab2 = st.tabs(["📋 **Proxy Input**", "🎯 **Target List**"])

with tab1:
    st.session_state.proxy_text = st.text_area(
        "Input", 
        value=st.session_state.proxy_text, 
        height=150, 
        placeholder="socks5://103.141.67.50:9090\n113.212.109.40:1080", 
        label_visibility="collapsed"
    )
    
    c1, c2, c3 = st.columns([1, 1, 3])
    with c1:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.proxy_text = ""
            st.session_state.results = []
            st.session_state.ftp_results = []
            st.session_state.check_done = False
            st.session_state.logs = []
            st.rerun()
    with c2:
        if st.button("🧹 Dedupe", use_container_width=True):
            raw = st.session_state.proxy_text.strip().split('\n')
            unique = sorted(list(set([l.strip() for l in raw if l.strip()])))
            st.session_state.proxy_text = "\n".join(unique)
            st.rerun()

with tab2:
    st.info("Proxies will be tested against these URLs (BDIX/FTP):")
    target_text = st.text_area("Targets", value=DEFAULT_TARGETS, height=150, label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True) # End Glass Card

# --- ACTION BUTTON ---
if st.button("▶ INITIATE SCAN SEQUENCE", type="primary", use_container_width=True):
    # Reset
    st.session_state.results = []
    st.session_state.ftp_results = []
    st.session_state.check_done = False
    st.session_state.logs = []
    
    # Parse Logic
    lines = st.session_state.proxy_text.strip().split('\n')
    proxies_to_check = []
    seen = set()
    
    for line in lines:
        line = line.strip()
        if not line: continue
        ip, port, proto = None, None, None
        
        # Regex for 'protocol://ip:port' or 'ip:port'
        regex_match = re.search(r'(?:(?P<proto>[a-z0-9]+)://)?(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(?P<port>\d+)', line, re.IGNORECASE)
        
        if regex_match:
            ip = regex_match.group('ip')
            port = regex_match.group('port')
            extracted_proto = regex_match.group('proto')
            proto = extracted_proto.lower() if extracted_proto else (force_proto if force_proto != "AUTO" else "http")
            if force_proto == "AUTO" and not extracted_proto:
                if "socks5" in line.lower(): proto = "socks5"
                elif "socks4" in line.lower(): proto = "socks4"
                elif "https" in line.lower(): proto = "https"
        else:
            parts = line.split()
            if len(parts) >= 2:
                ip, port = parts[0], parts[1]
                proto = force_proto if force_proto != "AUTO" else "http"
                if force_proto == "AUTO":
                    if "socks5" in line.lower(): proto = "socks5"
                    elif "socks4" in line.lower(): proto = "socks4"
                    elif "https" in line.lower(): proto = "https"
        
        if ip and port and re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
            unique_id = f"{ip}:{port}"
            if unique_id not in seen:
                seen.add(unique_id)
                proxies_to_check.append({"ip": ip, "port": port, "protocol": proto})

    if not proxies_to_check:
        st.warning("No valid proxies detected.")
    else:
        # EXECUTION: PHASE 1
        real_ip = get_real_ip()
        results_temp = []
        
        # Progress Bar
        bar = st.progress(0)
        status_text = st.empty()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_proxy = {executor.submit(check_proxy_basic, p, timeout, real_ip): p for p in proxies_to_check}
            completed = 0
            for future in concurrent.futures.as_completed(future_to_proxy):
                res = future.result()
                results_temp.append(res)
                completed += 1
                progress = completed / len(proxies_to_check)
                bar.progress(progress)
                status_text.markdown(f"**Scanning Node: {completed}/{len(proxies_to_check)}**")
                
                if res['Status'] == 'Working': 
                    log_event(f"ALIVE: {res['IP']} :: {res['ISP']}")
                
        st.session_state.results = results_temp
        
        # EXECUTION: PHASE 2
        log_event("Initializing Target Matrix Check...")
        target_list = target_text.strip().split('\n')
        ftp_temp = []
        bar.progress(0)
        completed = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_ftp = {executor.submit(check_specific_target, p, target_list, 5): p for p in results_temp}
            for future in concurrent.futures.as_completed(future_to_ftp):
                f_res = future.result()
                ftp_temp.append(f_res)
                completed += 1
                bar.progress(completed / len(results_temp))
                status_text.markdown(f"**Verifying Targets: {completed}/{len(results_temp)}**")

        st.session_state.ftp_results = ftp_temp
        st.session_state.check_done = True
        status_text.empty()
        bar.empty()
        st.rerun()

# --- RESULTS SECTION ---
if st.session_state.check_done:
    df = pd.DataFrame(st.session_state.results)
    df_working = df[df['Status'] == "Working"]
    df_dead = df[df['Status'] == "Dead"]
    
    # METRICS ROW
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nodes Processed", len(df))
    c2.metric("Online Nodes", len(df_working))
    c3.metric("Latency (Avg)", f"{int(df_working['Latency'].mean())}ms" if not df_working.empty else "-")
    c4.metric("Targets", len(target_text.strip().split('\n')))

    # TABS (GLASS CARD WRAPPED)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    res_tab1, res_tab2, res_tab3 = st.tabs(["🚀 **BDIX Matrix**", "✅ **Working List**", "❌ **Dead List**"])

    # --- TAB 1: BDIX MATRIX ---
    with res_tab1:
        if st.session_state.ftp_results:
            st.markdown("##### Target Connectivity Matrix")
            df_ftp = pd.DataFrame(st.session_state.ftp_results)
            
            success_mask = df_ftp.astype(str).apply(lambda x: x.str.contains('✅')).any(axis=1)
            success_proxies = df_ftp[success_mask].copy()

            base_cols = ['Proxy', 'Type']
            target_cols = [c for c in df_ftp.columns if c not in base_cols and c != 'Raw_IP']
            
            # Styling for the dataframe
            def color_matrix(val):
                if '✅' in str(val): return 'background-color: #1c4e28; color: #a6ffbe;' # Dark Green background
                if '⛔' in str(val): return 'background-color: #5c4d00; color: #ffdca6;' # Dark Orange
                return ''
            
            st.dataframe(df_ftp[base_cols + target_cols].style.applymap(color_matrix), use_container_width=True)

            if not success_proxies.empty:
                st.divider()
                st.subheader("📋 Extraction")
                
                # Format logic
                def format_success_row(row):
                    worked_urls = []
                    for col in target_cols:
                        if '✅' in str(row[col]): worked_urls.append(col)
                    return f"{row['Type'].lower()}://{row['Raw_IP']} | Opens: {', '.join(worked_urls)}"

                success_proxies['Copy_Format'] = success_proxies.apply(format_success_row, axis=1)

                col_sel, col_code = st.columns([1, 1])
                with col_sel:
                    st.caption("Select to Copy")
                    sel_ftp = st.dataframe(
                        success_proxies[['Type', 'Raw_IP', 'Copy_Format']],
                        column_config={"Copy_Format": None, "Raw_IP": "IP Address"},
                        use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row"
                    )
                with col_code:
                    rows = sel_ftp.selection.rows
                    if rows:
                        txt = "\n".join(success_proxies.iloc[rows]['Copy_Format'].tolist())
                        st.info(f"{len(rows)} Selected")
                        st.code(txt, language="text")
                    else:
                        st.info("Copy All")
                        st.code("\n".join(success_proxies['Copy_Format'].tolist()), language="text")
            else:
                st.warning("No proxies successfully opened any target.")

    # --- TAB 2: WORKING LIST ---
    with res_tab2:
        if not df_working.empty:
            def latency_color(val):
                if val < 200: return "🟢"
                if val < 800: return "🟡"
                return "🔴"
            
            df_working['Speed'] = df_working['Latency'].apply(latency_color)
            disp_df = df_working[['Speed', 'IP', 'Port', 'Protocol', 'ISP', 'Country', 'Latency', 'Full_Address']]
            
            sel_w = st.dataframe(
                disp_df,
                column_config={"Latency": st.column_config.NumberColumn(format="%d ms"), "Full_Address": None},
                use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row"
            )
            
            rows = sel_w.selection.rows
            if rows:
                txt = "\n".join(disp_df.iloc[rows]['Full_Address'].tolist())
                st.code(txt, language="text")
            else:
                # ISP Filter Logic
                isps = sorted(df_working['ISP'].unique().tolist())
                c_f1, c_f2 = st.columns([1, 2])
                with c_f1:
                    selected_isp = st.selectbox("Filter ISP", ["All"] + isps)
                with c_f2:
                    if selected_isp != "All":
                        filtered = df_working[df_working['ISP'] == selected_isp]
                        st.code("\n".join(filtered['Full_Address'].tolist()), language="text")
                    else:
                        with st.expander("Show All"):
                            st.code("\n".join(df_working['Full_Address'].tolist()))
        else:
            st.warning("No working proxies detected.")

    # --- TAB 3: DEAD LIST ---
    with res_tab3:
        if not df_dead.empty:
            st.dataframe(df_dead[['IP', 'Port', 'Protocol']], use_container_width=True, hide_index=True)
            with st.expander("Show List"):
                st.code("\n".join(df_dead['Full_Address'].tolist()))

    st.markdown('</div>', unsafe_allow_html=True) # End Glass Card

# --- LIVE TERMINAL ---
if st.session_state.logs:
    st.write("")
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.caption("🖥️ System Logs")
    # Custom HTML log for style
    log_content = "<br>".join([f"<span style='color: #00ff00;'>&gt;</span> {l}" for l in st.session_state.logs[::-1]])
    st.markdown(f"""
    <div class='terminal-container'>
        {log_content}
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- FOOTER ---
st.markdown("""
<div class="glass-footer">
    Developed by <b>RAKIB</b> &nbsp;•&nbsp; BDIX Intelligence &nbsp;•&nbsp;
</div>
""", unsafe_allow_html=True)

