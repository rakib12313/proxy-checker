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
    page_title="NETRUNNER_V2.0",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CYBERPUNK / SCI-FI THEME (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;500;700&family=Share+Tech+Mono&display=swap');

    /* 1. GLOBAL VARIABLES */
    :root {
        --neon-cyan: #00f3ff;
        --neon-pink: #bc13fe;
        --neon-green: #0aff0a;
        --bg-dark: #050505;
        --panel-bg: rgba(10, 15, 20, 0.85);
        --grid-color: rgba(0, 243, 255, 0.1);
    }

    /* 2. MAIN BACKGROUND & GRID */
    .stApp {
        background-color: var(--bg-dark);
        background-image: 
            linear-gradient(var(--grid-color) 1px, transparent 1px),
            linear-gradient(90deg, var(--grid-color) 1px, transparent 1px);
        background-size: 40px 40px;
        font-family: 'Rajdhani', sans-serif;
        color: #e0e0e0;
    }
    
    /* CRT SCANLINE OVERLAY */
    .stApp::before {
        content: " ";
        display: block;
        position: absolute;
        top: 0; left: 0; bottom: 0; right: 0;
        background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
        z-index: 9999;
        background-size: 100% 2px, 3px 100%;
        pointer-events: none;
    }

    /* 3. HEADERS & TYPOGRAPHY */
    h1, h2, h3 {
        font-family: 'Orbitron', sans-serif !important;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    h1 {
        background: -webkit-linear-gradient(0deg, var(--neon-cyan), #ffffff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 20px rgba(0, 243, 255, 0.5);
    }

    /* 4. CYBER CARDS (Containers) */
    .cyber-card {
        background: var(--panel-bg);
        border: 1px solid var(--neon-cyan);
        box-shadow: 0 0 10px rgba(0, 243, 255, 0.1), inset 0 0 20px rgba(0, 243, 255, 0.05);
        border-radius: 4px;
        padding: 20px;
        margin-bottom: 20px;
        position: relative;
        overflow: hidden;
    }
    /* Corner Decorations */
    .cyber-card::after {
        content: '';
        position: absolute;
        top: 0; right: 0;
        width: 20px; height: 20px;
        border-top: 2px solid var(--neon-pink);
        border-right: 2px solid var(--neon-pink);
    }
    .cyber-card::before {
        content: '';
        position: absolute;
        bottom: 0; left: 0;
        width: 20px; height: 20px;
        border-bottom: 2px solid var(--neon-pink);
        border-left: 2px solid var(--neon-pink);
    }

    /* 5. INPUTS & TEXTAREAS */
    .stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: rgba(0, 0, 0, 0.6) !important;
        color: var(--neon-green) !important;
        border: 1px solid #333 !important;
        border-left: 3px solid var(--neon-cyan) !important;
        font-family: 'Share Tech Mono', monospace !important;
        border-radius: 0px !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        box-shadow: 0 0 15px rgba(0, 243, 255, 0.2);
        border-color: var(--neon-cyan) !important;
    }

    /* 6. BUTTONS */
    div.stButton > button {
        background: transparent;
        color: var(--neon-cyan);
        border: 1px solid var(--neon-cyan);
        border-radius: 0px;
        font-family: 'Orbitron', sans-serif;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
        width: 100%;
    }
    div.stButton > button:hover {
        background: var(--neon-cyan);
        color: #000;
        box-shadow: 0 0 20px var(--neon-cyan);
        border-color: var(--neon-cyan);
    }
    /* Primary Action Button Special Style */
    div.stButton > button[kind="primary"] {
        background: rgba(188, 19, 254, 0.1);
        border: 1px solid var(--neon-pink);
        color: var(--neon-pink);
    }
    div.stButton > button[kind="primary"]:hover {
        background: var(--neon-pink);
        color: #fff;
        box-shadow: 0 0 25px var(--neon-pink);
    }

    /* 7. METRICS */
    [data-testid="stMetric"] {
        background: rgba(0, 0, 0, 0.5);
        border: 1px solid #333;
        border-right: 3px solid var(--neon-cyan);
        padding: 10px;
    }
    [data-testid="stMetricLabel"] {
        color: #888;
        font-family: 'Share Tech Mono', monospace;
        font-size: 14px;
    }
    [data-testid="stMetricValue"] {
        color: #fff;
        font-family: 'Orbitron', sans-serif;
        text-shadow: 0 0 10px var(--neon-cyan);
    }

    /* 8. DATAFRAMES */
    [data-testid="stDataFrame"] {
        border: 1px solid #333;
    }
    [data-testid="stDataFrame"] th {
        background-color: #111 !important;
        color: var(--neon-cyan) !important;
        font-family: 'Orbitron', sans-serif;
    }
    [data-testid="stDataFrame"] td {
        background-color: #080808 !important;
        color: #ccc !important;
        font-family: 'Share Tech Mono', monospace;
    }

    /* 9. TERMINAL LOG */
    .terminal-container {
        background: #000;
        border: 1px solid #333;
        border-top: 2px solid var(--neon-green);
        padding: 15px;
        font-family: 'Share Tech Mono', monospace;
        font-size: 12px;
        color: var(--neon-green);
        height: 200px;
        overflow-y: auto;
        box-shadow: inset 0 0 30px rgba(0, 255, 0, 0.1);
    }
    /* Scrollbar */
    ::-webkit-scrollbar {width: 8px;}
    ::-webkit-scrollbar-track {background: #000;}
    ::-webkit-scrollbar-thumb {background: #333; border: 1px solid var(--neon-cyan);}

    /* 10. SIDEBAR */
    [data-testid="stSidebar"] {
        background-color: #080808;
        border-right: 1px solid #333;
    }
    
    /* ANIMATIONS */
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    .status-blink {
        animation: pulse 1s infinite;
        color: var(--neon-green);
        font-weight: bold;
    }

    /* UTILITIES */
    .glitch {
        position: relative;
    }
    .neon-text { color: var(--neon-cyan); }
    .pink-text { color: var(--neon-pink); }
    
    /* Hide Streamlit Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
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

# --- FUNCTIONS (LOGIC REMAINS SAME) ---
def log_event(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {message}")
    if len(st.session_state.logs) > 60:
        st.session_state.logs.pop(0)

def get_real_ip():
    try: return requests.get("https://api.ipify.org", timeout=3).text
    except: return "Unknown"

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
                proxy_result[url] = "ACCESS_GRANTED" # Changed text for theme
            elif resp.status_code == 403:
                proxy_result[url] = "FORBIDDEN"
            elif resp.status_code == 404:
                proxy_result[url] = "NOT_FOUND"
            else:
                proxy_result[url] = f"ERR_{resp.status_code}"
        except:
            proxy_result[url] = "TIMEOUT"
            
    return proxy_result

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### <span class='neon-text'>// SYSTEM CONFIG</span>", unsafe_allow_html=True)
    st.caption("NETRUNNER V2.0")
    st.markdown("---")
    
    threads = st.slider("THREAD_COUNT", 5, 50, 25)
    timeout = st.slider("TIMEOUT_SEC", 1, 15, 6)
    force_proto = st.selectbox("FORCE_PROTOCOL", ["AUTO", "http", "socks4", "socks5"])
    
    st.markdown("---")
    st.markdown("""
    <div style='background: #111; border-left: 2px solid var(--neon-pink); padding: 10px; font-size: 11px; font-family: monospace;'>
    <b>PROTOCOL TIP:</b><br>
    The Matrix Grid identifies Node compatibility with BDIX/FTP endpoints.
    </div>
    """, unsafe_allow_html=True)

# --- HEADER AREA ---
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown("<h1>NETRUNNER <span style='font-size: 20px; color: var(--neon-pink); vertical-align: top;'>PRO</span></h1>", unsafe_allow_html=True)
    st.markdown("<span style='font-family: monospace; color: var(--neon-green);'>:: BDIX INTELLIGENCE SYSTEM INITIALIZED ::</span>", unsafe_allow_html=True)
with col_h2:
    st.write("")
    if st.button("↻ REBOOT_UI", use_container_width=True):
        st.rerun()

st.write("") # Spacer

# --- INPUT SECTION (CYBER CARD) ---
st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
st.markdown("<h3 style='margin-top:0'>DATA_INJECTION</h3>", unsafe_allow_html=True)
tab1, tab2 = st.tabs(["📋 PROXY_NODES", "🎯 TARGET_VECTORS"])

with tab1:
    st.session_state.proxy_text = st.text_area(
        "Proxy Input", 
        value=st.session_state.proxy_text, 
        height=150, 
        placeholder="socks5://103.141.67.50:9090\n113.212.109.40:1080", 
        label_visibility="collapsed"
    )
    
    c1, c2, c3 = st.columns([1, 1, 3])
    with c1:
        if st.button("🗑️ PURGE", use_container_width=True):
            st.session_state.proxy_text = ""
            st.session_state.results = []
            st.session_state.ftp_results = []
            st.session_state.check_done = False
            st.session_state.logs = []
            st.rerun()
    with c2:
        if st.button("🧹 DEFRAG", use_container_width=True):
            raw = st.session_state.proxy_text.strip().split('\n')
            unique = sorted(list(set([l.strip() for l in raw if l.strip()])))
            st.session_state.proxy_text = "\n".join(unique)
            st.rerun()

with tab2:
    st.info("NODES WILL BE TESTED AGAINST THESE ENDPOINTS:")
    target_text = st.text_area("Targets", value=DEFAULT_TARGETS, height=150, label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True) # End Cyber Card

# --- ACTION BUTTON ---
col_act1, col_act2 = st.columns([1, 4])
with col_act2:
    if st.button("▶ INITIATE_SCAN_SEQUENCE", type="primary", use_container_width=True):
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
            st.warning("SYSTEM ERROR: NO VALID NODES DETECTED.")
        else:
            # EXECUTION: PHASE 1
            real_ip = get_real_ip()
            results_temp = []
            
            # Progress Bar (Custom HTML if possible, but st.progress works)
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
                    status_text.markdown(f"<span class='status-blink'>SCANNING NODE:</span> {completed}/{len(proxies_to_check)}", unsafe_allow_html=True)
                    
                    if res['Status'] == 'Working': 
                        log_event(f"LINK_ESTABLISHED: {res['IP']} :: {res['ISP']}")
                    
            st.session_state.results = results_temp
            
            # EXECUTION: PHASE 2
            log_event("INITIALIZING TARGET MATRIX VERIFICATION...")
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
                    status_text.markdown(f"<span class='status-blink'>VERIFYING VECTORS:</span> {completed}/{len(results_temp)}", unsafe_allow_html=True)

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
    c1.metric("NODES_SCANNED", len(df))
    c2.metric("ACTIVE_LINKS", len(df_working))
    c3.metric("LATENCY_AVG", f"{int(df_working['Latency'].mean())}ms" if not df_working.empty else "-")
    c4.metric("TARGETS", len(target_text.strip().split('\n')))

    # TABS (CYBER CARD WRAPPED)
    st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
    res_tab1, res_tab2, res_tab3 = st.tabs(["🚀 **MATRIX_GRID**", "✅ **ACTIVE_LIST**", "❌ **DEAD_POOL**"])

    # --- TAB 1: BDIX MATRIX ---
    with res_tab1:
        if st.session_state.ftp_results:
            st.markdown("##### CONNECTION MATRIX")
            df_ftp = pd.DataFrame(st.session_state.ftp_results)
            
            success_mask = df_ftp.astype(str).apply(lambda x: x.str.contains('ACCESS_GRANTED')).any(axis=1)
            success_proxies = df_ftp[success_mask].copy()

            base_cols = ['Proxy', 'Type']
            target_cols = [c for c in df_ftp.columns if c not in base_cols and c != 'Raw_IP']
            
            # Styling for the dataframe
            def color_matrix(val):
                if 'ACCESS_GRANTED' in str(val): return 'color: #0aff0a; font-weight: bold; background-color: rgba(0, 255, 10, 0.1);' 
                if 'FORBIDDEN' in str(val): return 'color: #ffaa00;' 
                if 'TIMEOUT' in str(val): return 'color: #555;'
                return ''
            
            st.dataframe(df_ftp[base_cols + target_cols].style.applymap(color_matrix), use_container_width=True)

            if not success_proxies.empty:
                st.divider()
                st.subheader("📋 DATA_EXTRACTION")
                
                # Format logic
                def format_success_row(row):
                    worked_urls = []
                    for col in target_cols:
                        if 'ACCESS_GRANTED' in str(row[col]): worked_urls.append(col)
                    return f"{row['Type'].lower()}://{row['Raw_IP']} | Access: {', '.join(worked_urls)}"

                success_proxies['Copy_Format'] = success_proxies.apply(format_success_row, axis=1)

                col_sel, col_code = st.columns([1, 1])
                with col_sel:
                    st.caption("SELECT_ROWS")
                    sel_ftp = st.dataframe(
                        success_proxies[['Type', 'Raw_IP', 'Copy_Format']],
                        column_config={"Copy_Format": None, "Raw_IP": "IP Address"},
                        use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row"
                    )
                with col_code:
                    rows = sel_ftp.selection.rows
                    if rows:
                        txt = "\n".join(success_proxies.iloc[rows]['Copy_Format'].tolist())
                        st.info(f"{len(rows)} ROWS SELECTED")
                        st.code(txt, language="text")
                    else:
                        st.info("EXPORT_ALL")
                        st.code("\n".join(success_proxies['Copy_Format'].tolist()), language="text")
            else:
                st.warning("ZERO CONNECTIVITY DETECTED.")

    # --- TAB 2: WORKING LIST ---
    with res_tab2:
        if not df_working.empty:
            def latency_color(val):
                if val < 200: return "🟢"
                if val < 800: return "🟡"
                return "🔴"
            
            df_working['Signal'] = df_working['Latency'].apply(latency_color)
            disp_df = df_working[['Signal', 'IP', 'Port', 'Protocol', 'ISP', 'Country', 'Latency', 'Full_Address']]
            
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
                    selected_isp = st.selectbox("FILTER_ISP", ["ALL_NETWORKS"] + isps)
                with c_f2:
                    if selected_isp != "ALL_NETWORKS":
                        filtered = df_working[df_working['ISP'] == selected_isp]
                        st.code("\n".join(filtered['Full_Address'].tolist()), language="text")
                    else:
                        with st.expander("SHOW_RAW_LIST"):
                            st.code("\n".join(df_working['Full_Address'].tolist()))
        else:
            st.warning("NO ACTIVE NODES.")

    # --- TAB 3: DEAD LIST ---
    with res_tab3:
        if not df_dead.empty:
            st.dataframe(df_dead[['IP', 'Port', 'Protocol']], use_container_width=True, hide_index=True)
            with st.expander("VIEW_DUMP"):
                st.code("\n".join(df_dead['Full_Address'].tolist()))

    st.markdown('</div>', unsafe_allow_html=True) # End Cyber Card

# --- LIVE TERMINAL ---
if st.session_state.logs:
    st.write("")
    st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
    st.caption("🖥️ KERNEL_LOGS")
    # Custom HTML log for style
    log_content = "<br>".join([f"<span style='color: var(--neon-cyan);'>&gt;</span> {l}" for l in st.session_state.logs[::-1]])
    st.markdown(f"""
    <div class='terminal-container'>
        {log_content}
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- FOOTER ---
st.markdown("""
<div style="position: fixed; bottom: 0; width: 100%; text-align: center; color: #555; background: rgba(0,0,0,0.9); border-top: 1px solid #222; padding: 5px; font-size: 10px;">
    NETRUNNER_V2.0 &nbsp;•&nbsp; SYSTEM_STATUS: ONLINE &nbsp;•&nbsp; <span style='color: var(--neon-pink)'>ENCRYPTED</span>
</div>
""", unsafe_allow_html=True)
