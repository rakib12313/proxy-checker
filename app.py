import streamlit as st
import requests
import concurrent.futures
import time
import re
import pandas as pd
import random
import io
from datetime import datetime

# --- FAILSAFE IMPORT ---
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- CONFIGURATION ---
st.set_page_config(
    page_title="NETRUNNER_V3.0 | RAKIB",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CYBERPUNK THEME (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;500;700&family=Share+Tech+Mono&display=swap');

    :root {
        --neon-cyan: #00f3ff;
        --neon-pink: #bc13fe;
        --neon-green: #0aff0a;
        --bg-dark: #050505;
        --panel-bg: rgba(10, 15, 20, 0.90);
        --grid-color: rgba(0, 243, 255, 0.05);
    }

    /* BACKGROUND & GRID */
    .stApp {
        background-color: var(--bg-dark);
        background-image: 
            linear-gradient(var(--grid-color) 1px, transparent 1px),
            linear-gradient(90deg, var(--grid-color) 1px, transparent 1px);
        background-size: 50px 50px;
        font-family: 'Rajdhani', sans-serif;
        color: #e0e0e0;
    }

    /* HEADERS */
    h1, h2, h3, h4, h5 {
        font-family: 'Orbitron', sans-serif !important;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    /* CUSTOM CARDS */
    .cyber-card {
        background: var(--panel-bg);
        border: 1px solid #333;
        border-left: 2px solid var(--neon-cyan);
        box-shadow: 0 0 15px rgba(0,0,0,0.5);
        padding: 20px;
        margin-bottom: 20px;
        position: relative;
    }
    .cyber-card::before {
        content: "SYSTEM_MODULE";
        position: absolute;
        top: -10px;
        right: 10px;
        background: var(--bg-dark);
        color: var(--neon-cyan);
        font-size: 10px;
        padding: 0 5px;
        font-family: 'Share Tech Mono', monospace;
        border: 1px solid var(--neon-cyan);
    }

    /* INPUTS */
    .stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: rgba(0, 0, 0, 0.7) !important;
        color: var(--neon-green) !important;
        border: 1px solid #444 !important;
        font-family: 'Share Tech Mono', monospace !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: var(--neon-cyan) !important;
        box-shadow: 0 0 10px rgba(0, 243, 255, 0.2);
    }

    /* BUTTONS */
    div.stButton > button {
        background: transparent;
        color: var(--neon-cyan);
        border: 1px solid var(--neon-cyan);
        border-radius: 0px;
        font-family: 'Orbitron', sans-serif;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background: var(--neon-cyan);
        color: #000;
        box-shadow: 0 0 20px var(--neon-cyan);
    }
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

    /* DATAFRAMES */
    [data-testid="stDataFrame"] { border: 1px solid #333; }
    [data-testid="stDataFrame"] th { background-color: #111 !important; color: var(--neon-cyan) !important; }
    [data-testid="stDataFrame"] td { background-color: #080808 !important; color: #ccc !important; font-family: 'Share Tech Mono', monospace; }

    /* LOGS */
    .terminal-container {
        background: #000;
        border: 1px solid #333;
        border-bottom: 2px solid var(--neon-green);
        padding: 15px;
        font-family: 'Share Tech Mono', monospace;
        font-size: 12px;
        color: var(--neon-green);
        height: 200px;
        overflow-y: auto;
    }

    /* FOOTER/HEADER BRANDING */
    .rakib-brand {
        color: var(--neon-pink);
        font-weight: 900;
        text-shadow: 0 0 5px var(--neon-pink);
    }

    /* Hide Streamlit Stuff */
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

# User Agents for Stealth Mode
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
]

# --- FUNCTIONS ---
def log_event(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {message}")
    if len(st.session_state.logs) > 60:
        st.session_state.logs.pop(0)

def get_real_ip():
    try: return requests.get("https://api.ipify.org", timeout=3).text
    except: return "Unknown"

# 1. General Check (Stealth Enhanced)
def check_proxy_basic(proxy_data, timeout, real_ip):
    ip, port, protocol = proxy_data['ip'], proxy_data['port'], proxy_data['protocol']
    proxy_conf = {
        "http": f"{protocol}://{ip}:{port}",
        "https": f"{protocol}://{ip}:{port}",
    }
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    
    result = {
        "IP": ip, "Port": port, "Protocol": protocol.upper(),
        "Country": "-", "ISP": "Unknown", "Latency": 99999, "Status": "Dead", 
        "Full_Address": f"{ip}:{port}"
    }
    
    try:
        start = time.time()
        # Using httpbin to verify connectivity
        resp = requests.get("http://httpbin.org/get", proxies=proxy_conf, headers=headers, timeout=timeout)
        latency = round((time.time() - start) * 1000)
        
        if resp.status_code == 200:
            result['Latency'] = latency
            result['Status'] = "Working"
            
            # Geo/ISP Check (Direct, no proxy needed for speed)
            try:
                geo = requests.get(f"http://ip-api.com/json/{ip}", timeout=2).json()
                if geo['status'] == 'success': 
                    result['Country'] = geo['countryCode']
                    result['ISP'] = geo['isp']
            except: pass
    except: pass
    return result

# 2. Target Check (Stealth Enhanced)
def check_specific_target(proxy_data, target_urls, timeout):
    ip = proxy_data.get('IP') or proxy_data.get('ip')
    port = proxy_data.get('Port') or proxy_data.get('port')
    protocol = proxy_data.get('Protocol') or proxy_data.get('protocol')
    protocol_lower = protocol.lower()

    proxy_conf = {
        "http": f"{protocol_lower}://{ip}:{port}",
        "https": f"{protocol_lower}://{ip}:{port}",
    }
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    
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
            resp = requests.get(url, proxies=proxy_conf, headers=headers, timeout=5) 
            if resp.status_code == 200:
                proxy_result[url] = "ACCESS_GRANTED"
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
    st.markdown("## <span class='neon-text'>// SYSTEM_CORE</span>", unsafe_allow_html=True)
    st.markdown("Developed by <span class='rakib-brand'>RAKIB</span>", unsafe_allow_html=True)
    st.markdown("---")
    
    threads = st.slider("THREAD_COUNT", 5, 50, 25)
    timeout = st.slider("TIMEOUT_SEC", 1, 15, 6)
    force_proto = st.selectbox("FORCE_PROTOCOL", ["AUTO", "http", "socks4", "socks5"])
    
    st.markdown("---")
    st.info("💡 TIP: Enable 'AUTO' for mixed proxy lists. System will attempt to detect protocol.")

# --- HEADER AREA ---
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown("<h1>NETRUNNER <span style='color: var(--neon-pink); font-size: 0.6em; vertical-align: top;'>PRO</span></h1>", unsafe_allow_html=True)
    st.markdown("<span style='font-family: monospace; color: var(--neon-green);'>:: ARCHITECT: RAKIB :: BDIX INTELLIGENCE SYSTEM ::</span>", unsafe_allow_html=True)
with col_h2:
    st.write("")
    if st.button("↻ REBOOT_UI", use_container_width=True):
        st.rerun()

st.write("") 

# --- INPUT SECTION (CYBER CARD) ---
st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
st.markdown("<h4 style='color: var(--neon-cyan)'>DATA_INJECTION_MODULE</h4>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📋 PROXY_NODES", "🎯 TARGET_VECTORS"])

with tab1:
    # New Input Method Selection
    input_method = st.radio("INPUT_SOURCE", ["MANUAL_ENTRY", "FILE_UPLOAD"], horizontal=True, label_visibility="collapsed")
    
    if input_method == "FILE_UPLOAD":
        uploaded_file = st.file_uploader("UPLOAD_NODELIST (TXT/CSV)", type=['txt', 'csv'], label_visibility="collapsed")
        if uploaded_file:
            stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
            st.session_state.proxy_text = stringio.read()
            st.success(f"FILE LOADED: {uploaded_file.name}")
    else:
        st.session_state.proxy_text = st.text_area(
            "Input", 
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
    st.caption("NODES WILL BE TESTED AGAINST THESE ENDPOINTS:")
    target_text = st.text_area("Targets", value=DEFAULT_TARGETS, height=150, label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

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
            
            bar = st.progress(0)
            status_text = st.empty()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
                future_to_proxy = {executor.submit(check_proxy_basic, p, timeout, real_ip): p for p in proxies_to_check}
                completed = 0
                for future in concurrent.futures.as_completed(future_to_proxy):
                    res = future.result()
                    results_temp.append(res)
                    completed += 1
                    bar.progress(completed / len(proxies_to_check))
                    status_text.markdown(f"**SCANNING NODE:** {completed}/{len(proxies_to_check)}")
                    
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
                    status_text.markdown(f"**VERIFYING VECTORS:** {completed}/{len(results_temp)}")

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
    
    # METRICS
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("NODES_SCANNED", len(df))
    c2.metric("ACTIVE_LINKS", len(df_working))
    c3.metric("LATENCY_AVG", f"{int(df_working['Latency'].mean())}ms" if not df_working.empty else "-")
    c4.metric("TARGETS", len(target_text.strip().split('\n')))

    # --- GEOSPATIAL & ANALYTICS VISUALIZATION ---
    if not df_working.empty and PLOTLY_AVAILABLE:
        st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
        st.markdown("##### <span class='neon-text'>GLOBAL_INTELLIGENCE_MAP</span>", unsafe_allow_html=True)
        
        # MAP
        fig = px.scatter_geo(
            df_working, 
            locations="Country", 
            locationmode='ISO-3',
            hover_name="ISP",
            size="Latency", 
            projection="orthographic", 
            color="Protocol", 
            color_discrete_map={"HTTP": "#00f3ff", "SOCKS4": "#bc13fe", "SOCKS5": "#0aff0a"}
        )
        fig.update_layout(
            font=dict(family="Orbitron", color="#00f3ff"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            geo=dict(
                bgcolor="rgba(0,0,0,0)", showland=True, landcolor="#0a0f14",
                showocean=True, oceancolor="#050505", showcountries=True, countrycolor="#333"
            )
        )
        st.plotly_chart(fig, use_container_width=True)

        # CHARTS
        st.markdown("---")
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            proto_counts = df_working['Protocol'].value_counts().reset_index()
            proto_counts.columns = ['Protocol', 'Count']
            fig_proto = px.pie(proto_counts, values='Count', names='Protocol', hole=0.5,
                               color_discrete_sequence=['#00f3ff', '#bc13fe', '#0aff0a'])
            fig_proto.update_layout(title_text="PROTOCOL_DIST", title_font_family="Orbitron", paper_bgcolor="rgba(0,0,0,0)", font_color="#ccc")
            st.plotly_chart(fig_proto, use_container_width=True)

        with col_chart2:
            fig_hist = px.histogram(df_working, x="Latency", nbins=20, color_discrete_sequence=['#bc13fe'])
            fig_hist.update_layout(title_text="LATENCY_SPECTRUM (ms)", title_font_family="Orbitron", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0.3)", font_color="#ccc")
            st.plotly_chart(fig_hist, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- FILTERING ---
    if not df_working.empty:
        max_latency = st.slider("FILTER: MAX_LATENCY (MS)", 
                                min_value=0, 
                                max_value=int(df_working['Latency'].max()) if not df_working.empty else 1000, 
                                value=3000)
        df_filtered = df_working[df_working['Latency'] <= max_latency]
        st.caption(f"DISPLAYING {len(df_filtered)} NODES (FILTERED FROM {len(df_working)})")
    else:
        df_filtered = df_working

    # --- TABS ---
    st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
    res_tab1, res_tab2, res_tab3 = st.tabs(["🚀 **MATRIX_GRID**", "✅ **ACTIVE_LIST**", "❌ **DEAD_POOL**"])

    # TAB 1: MATRIX
    with res_tab1:
        if st.session_state.ftp_results:
            st.markdown("##### CONNECTION MATRIX")
            df_ftp = pd.DataFrame(st.session_state.ftp_results)
            
            # Apply Filter to Matrix view as well (Filter by IPs present in df_filtered)
            valid_ips = set(df_filtered['Full_Address'].tolist())
            # We need to reconstruct full address from Raw_IP (which is ip:port)
            df_ftp = df_ftp[df_ftp['Raw_IP'].isin(valid_ips)]

            base_cols = ['Proxy', 'Type']
            target_cols = [c for c in df_ftp.columns if c not in base_cols and c != 'Raw_IP']
            
            def color_matrix(val):
                if 'ACCESS_GRANTED' in str(val): return 'color: #0aff0a; font-weight: bold; background-color: rgba(0, 255, 10, 0.1);' 
                if 'FORBIDDEN' in str(val): return 'color: #ffaa00;' 
                if 'TIMEOUT' in str(val): return 'color: #555;'
                return ''
            
            st.dataframe(df_ftp[base_cols + target_cols].style.applymap(color_matrix), use_container_width=True)

    # TAB 2: ACTIVE LIST
    with res_tab2:
        if not df_filtered.empty:
            # 1. DOWNLOAD BUTTON
            csv = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇ EXPORT_CSV_DUMP",
                data=csv,
                file_name=f'NETRUNNER_SCAN_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
                mime='text/csv',
                key='download-csv'
            )

            # 2. QUICK COPY
            st.markdown("#### QUICK_COPY_TERMINAL")
            proxy_list_str = "\n".join(df_filtered['Full_Address'].tolist())
            st.code(proxy_list_str, language="text")

            # 3. DETAILED TABLE
            def latency_color(val):
                if val < 200: return "🟢"
                if val < 800: return "🟡"
                return "🔴"
            
            df_filtered['Signal'] = df_filtered['Latency'].apply(latency_color)
            disp_df = df_filtered[['Signal', 'IP', 'Port', 'Protocol', 'ISP', 'Country', 'Latency', 'Full_Address']]
            
            st.dataframe(
                disp_df,
                column_config={"Latency": st.column_config.NumberColumn(format="%d ms"), "Full_Address": None},
                use_container_width=True, hide_index=True
            )
        else:
            st.warning("NO ACTIVE NODES IN CURRENT FILTER RANGE.")

    # TAB 3: DEAD LIST
    with res_tab3:
        if not df_dead.empty:
            st.dataframe(df_dead[['IP', 'Port', 'Protocol']], use_container_width=True, hide_index=True)
            with st.expander("VIEW_RAW_DUMP"):
                st.code("\n".join(df_dead['Full_Address'].tolist()))

    st.markdown('</div>', unsafe_allow_html=True)

# --- LIVE TERMINAL ---
if st.session_state.logs:
    st.write("")
    st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
    st.caption("🖥️ KERNEL_LOGS")
    log_content = "<br>".join([f"<span style='color: var(--neon-cyan);'>&gt;</span> {l}" for l in st.session_state.logs[::-1]])
    st.markdown(f"<div class='terminal-container'>{log_content}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- FOOTER ---
st.markdown("""
<div style="position: fixed; bottom: 0; left: 0; width: 100%; text-align: center; color: #555; background: rgba(0,0,0,0.95); border-top: 1px solid #222; padding: 5px; font-size: 10px; z-index: 9999;">
    NETRUNNER_V3.0 &nbsp;•&nbsp; CREATED_BY <span class="rakib-brand">RAKIB</span> &nbsp;•&nbsp; <span style='color: var(--neon-pink)'>ENCRYPTED_CONNECTION</span>
</div>
""", unsafe_allow_html=True)
