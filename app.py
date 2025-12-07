import streamlit as st
import requests
import concurrent.futures
import time
import re
import pandas as pd
import random
import io
import json
from datetime import datetime

# --- FAILSAFE IMPORT ---
try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- CONFIGURATION ---
st.set_page_config(
    page_title="NETRUNNER_V5.0 | RAKIB",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ADVANCED CYBERPUNK CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@300;500;700&family=Share+Tech+Mono&display=swap');

    :root {
        --neon-cyan: #00f3ff;
        --neon-pink: #ff0055;
        --neon-purple: #bc13fe;
        --neon-green: #0aff0a;
        --bg-dark: #050505;
        --panel-bg: rgba(12, 12, 14, 0.95);
    }

    /* 1. MAIN LAYOUT */
    .stApp {
        background-color: var(--bg-dark);
        background-image: 
            radial-gradient(circle at 50% 50%, rgba(20, 20, 30, 0.5) 0%, transparent 100%),
            linear-gradient(rgba(0, 243, 255, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 243, 255, 0.03) 1px, transparent 1px);
        background-size: 100% 100%, 40px 40px, 40px 40px;
        font-family: 'Rajdhani', sans-serif;
        color: #e0e0e0;
    }

    /* 2. TYPOGRAPHY */
    h1, h2, h3, h4 {
        font-family: 'Orbitron', sans-serif !important;
        text-transform: uppercase;
        letter-spacing: 3px;
        text-shadow: 0 0 10px rgba(0, 243, 255, 0.3);
    }
    .rakib-brand {
        color: var(--neon-pink);
        font-weight: 900;
        text-shadow: 0 0 10px var(--neon-pink);
        animation: flicker 3s infinite;
    }

    /* 3. SCI-FI BUTTONS */
    div.stButton > button {
        position: relative;
        background: rgba(0, 0, 0, 0.6);
        color: var(--neon-cyan);
        font-family: 'Orbitron', sans-serif;
        font-weight: 700;
        letter-spacing: 2px;
        border: 1px solid var(--neon-cyan);
        border-radius: 0;
        padding: 12px 24px;
        transition: all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
        clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
        overflow: hidden;
    }
    div.stButton > button:hover {
        background: var(--neon-cyan);
        color: #000;
        box-shadow: 0 0 30px var(--neon-cyan);
        transform: translateY(-2px);
    }

    /* Primary Button (SCAN) */
    div.stButton > button[kind="primary"] {
        border-color: var(--neon-green);
        color: var(--neon-green);
        background: rgba(0, 255, 10, 0.05);
    }
    div.stButton > button[kind="primary"]:hover {
        background: var(--neon-green);
        color: #000;
        box-shadow: 0 0 40px var(--neon-green);
    }

    /* Stop Button (Custom Class Workaround) */
    div.stButton > button[data-testid="baseButton-secondary"] {
        border-color: var(--neon-pink);
        color: var(--neon-pink);
    }
    
    /* 4. CYBER CARDS */
    .cyber-card {
        background: var(--panel-bg);
        border: 1px solid rgba(0, 243, 255, 0.2);
        position: relative;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    .cyber-card::before {
        content: '';
        position: absolute;
        top: -1px; left: -1px;
        width: 10px; height: 10px;
        border-top: 2px solid var(--neon-cyan);
        border-left: 2px solid var(--neon-cyan);
    }

    /* 5. INPUTS & TABLES */
    .stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: rgba(0, 0, 0, 0.8) !important;
        color: var(--neon-green) !important;
        border: 1px solid #333 !important;
        font-family: 'Share Tech Mono', monospace !important;
        border-radius: 0 !important;
    }
    
    [data-testid="stDataFrame"] { border: 1px solid #333; }
    [data-testid="stDataFrame"] th { background-color: #0f0f0f !important; color: var(--neon-cyan) !important; font-family: 'Orbitron'; }
    [data-testid="stDataFrame"] td { background-color: #080808 !important; color: #bbb !important; font-family: 'Share Tech Mono'; }

    /* 6. METRICS */
    [data-testid="stMetric"] {
        background: rgba(0,0,0,0.5);
        border-left: 2px solid var(--neon-purple);
        padding: 10px 15px;
    }
    [data-testid="stMetricValue"] { color: #fff; text-shadow: 0 0 10px rgba(255,255,255,0.5); }
    [data-testid="stMetricLabel"] { color: #888; font-size: 12px; font-family: 'Orbitron'; }

    /* 7. TERMINAL */
    .terminal-window {
        background: #000;
        border: 1px solid #333;
        border-top: 3px solid var(--neon-green);
        padding: 10px;
        font-family: 'Share Tech Mono', monospace;
        color: var(--neon-green);
        height: 180px;
        overflow-y: auto;
        box-shadow: inset 0 0 20px rgba(0, 255, 0, 0.1);
    }
    
    /* ANIMATIONS */
    @keyframes flicker { 0% { opacity: 1; } 50% { opacity: 0.8; } 100% { opacity: 1; } }
    
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
if 'stop_scan' not in st.session_state: st.session_state.stop_scan = False

# --- CONSTANTS ---
DEFAULT_TARGETS = """http://10.16.100.244/
http://172.16.50.4/
http://new.circleftp.net/
http://ftp.samonline.net/"""

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
]

# --- LOGIC FUNCTIONS ---
def log_event(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {message}")
    if len(st.session_state.logs) > 60:
        st.session_state.logs.pop(0)

def get_real_ip():
    try: return requests.get("https://api.ipify.org", timeout=3).text.strip()
    except: return "Unknown"

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
        "Full_Address": f"{ip}:{port}", "Anonymity": "Unknown"
    }
    try:
        start = time.time()
        # Use httpbin to get IP and headers for Anonymity check
        resp = requests.get("http://httpbin.org/get", proxies=proxy_conf, headers=headers, timeout=timeout)
        latency = round((time.time() - start) * 1000)
        
        if resp.status_code == 200:
            result['Latency'] = latency
            result['Status'] = "Working"
            
            # ANONYMITY CHECK
            try:
                json_data = resp.json()
                origin = json_data.get('origin', '').split(',')[0].strip()
                if origin != real_ip and origin != "Unknown":
                    result['Anonymity'] = "🛡️ ELITE"
                else:
                    result['Anonymity'] = "⚠️ TRANSPARENT"
            except:
                result['Anonymity'] = "❓ UNKNOWN"

            # GEO CHECK
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
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    
    proxy_result = {
        "Proxy": f"{ip}:{port}", 
        "Type": protocol.upper(), 
        "Raw_IP": f"{ip}:{port}" # Key for linking back
    }
    
    for url in target_urls:
        url = url.strip()
        if not url: continue
        try:
            resp = requests.get(url, proxies=proxy_conf, headers=headers, timeout=5) 
            if resp.status_code == 200: proxy_result[url] = "ACCESS_GRANTED"
            elif resp.status_code == 403: proxy_result[url] = "FORBIDDEN"
            elif resp.status_code == 404: proxy_result[url] = "NOT_FOUND"
            else: proxy_result[url] = f"ERR_{resp.status_code}"
        except:
            proxy_result[url] = "TIMEOUT"
            
    return proxy_result

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## 💠 SYSTEM_CORE")
    st.caption("Developed by <span class='rakib-brand'>RAKIB</span>", unsafe_allow_html=True)
    st.markdown("---")
    
    threads = st.slider("THREAD_COUNT", 5, 50, 25)
    timeout = st.slider("TIMEOUT_SEC", 1, 15, 6)
    force_proto = st.selectbox("FORCE_PROTOCOL", ["AUTO", "http", "socks4", "socks5"])
    
    st.markdown("---")
    # STOP BUTTON
    if st.button("🚨 EMERGENCY STOP", use_container_width=True):
        st.session_state.stop_scan = True
        st.toast("⚠️ STOPPING SCAN...", icon="🛑")

# --- HEADER ---
c1, c2 = st.columns([4, 1])
with c1:
    st.markdown("<h1>NETRUNNER <span style='color:var(--neon-pink); font-size:0.5em; vertical-align:middle'>V5.0</span></h1>", unsafe_allow_html=True)
    st.markdown("<div style='font-family:monospace; color:var(--neon-cyan); letter-spacing:1px'>:: ARCHITECT: RAKIB :: BDIX INTELLIGENCE SYSTEM ::</div>", unsafe_allow_html=True)
with c2:
    st.write("")
    if st.button("↻ REBOOT", use_container_width=True):
        st.session_state.stop_scan = False
        st.rerun()

st.write("")

# --- INPUT AREA ---
st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
st.markdown("#### <span style='color:var(--neon-green)'>DATA_INJECTION</span>", unsafe_allow_html=True)
tab_in1, tab_in2 = st.tabs(["📄 NODE_LIST", "🎯 TARGET_VECTORS"])

with tab_in1:
    in_method = st.radio("INPUT_METHOD", ["MANUAL", "FILE_UPLOAD"], horizontal=True, label_visibility="collapsed")
    if in_method == "FILE_UPLOAD":
        up_file = st.file_uploader("UPLOAD .TXT/.CSV", type=['txt', 'csv'], label_visibility="collapsed")
        if up_file:
            st.session_state.proxy_text = io.StringIO(up_file.getvalue().decode("utf-8")).read()
            st.success(f"FILE_LOADED: {len(st.session_state.proxy_text.splitlines())} LINES")
    else:
        st.session_state.proxy_text = st.text_area("MANUAL", st.session_state.proxy_text, height=150, placeholder="socks5://1.1.1.1:8080", label_visibility="collapsed")

    bc1, bc2, bc3 = st.columns([1, 1, 3])
    with bc1:
        if st.button("🗑️ PURGE", use_container_width=True):
            st.session_state.proxy_text = ""
            st.session_state.results = []
            st.session_state.ftp_results = []
            st.session_state.check_done = False
            st.session_state.logs = []
            st.rerun()
    with bc2:
        if st.button("🧹 DEFRAG", use_container_width=True):
            raw = st.session_state.proxy_text.strip().split('\n')
            unique = sorted(list(set([l.strip() for l in raw if l.strip()])))
            st.session_state.proxy_text = "\n".join(unique)
            st.rerun()

with tab_in2:
    st.caption("CONNECTION_ENDPOINTS:")
    target_text = st.text_area("TARGETS", DEFAULT_TARGETS, height=150, label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

# --- EXECUTION ---
col_act1, col_act2 = st.columns([1, 4])
with col_act2:
    if st.button("▶ INITIATE_SCAN_SEQUENCE", type="primary", use_container_width=True):
        st.session_state.stop_scan = False
        st.session_state.results = []
        st.session_state.ftp_results = []
        st.session_state.check_done = False
        st.session_state.logs = []
        
        # PARSE
        lines = st.session_state.proxy_text.strip().split('\n')
        proxies_to_check = []
        seen = set()
        
        for line in lines:
            line = line.strip()
            if not line: continue
            ip, port, proto = None, None, None
            match = re.search(r'(?:(?P<proto>[a-z0-9]+)://)?(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(?P<port>\d+)', line, re.IGNORECASE)
            
            if match:
                ip, port = match.group('ip'), match.group('port')
                extracted = match.group('proto')
                proto = extracted.lower() if extracted else (force_proto if force_proto != "AUTO" else "http")
                if force_proto == "AUTO" and not extracted:
                    if "socks5" in line.lower(): proto = "socks5"
                    elif "socks4" in line.lower(): proto = "socks4"
                    elif "https" in line.lower(): proto = "https"
            
            if ip and port:
                uid = f"{ip}:{port}"
                if uid not in seen:
                    seen.add(uid)
                    proxies_to_check.append({"ip": ip, "port": port, "protocol": proto})

        if not proxies_to_check:
            st.error("NO DATA DETECTED.")
        else:
            # PHASE 1
            real_ip = get_real_ip()
            results_temp = []
            bar = st.progress(0)
            status = st.empty()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
                futures = {executor.submit(check_proxy_basic, p, timeout, real_ip): p for p in proxies_to_check}
                done = 0
                for f in concurrent.futures.as_completed(futures):
                    if st.session_state.stop_scan: break
                    res = f.result()
                    results_temp.append(res)
                    done += 1
                    bar.progress(done/len(proxies_to_check))
                    status.markdown(f"**SCANNING:** {done}/{len(proxies_to_check)}")
                    if res['Status'] == 'Working': log_event(f"ALIVE: {res['IP']} ({res['Anonymity']})")
            
            st.session_state.results = results_temp
            
            # PHASE 2 (Targets)
            if not st.session_state.stop_scan and results_temp:
                log_event("STARTING MATRIX VERIFICATION...")
                t_list = target_text.strip().split('\n')
                ftp_temp = []
                bar.progress(0)
                done = 0
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
                    futures = {executor.submit(check_specific_target, p, t_list, 5): p for p in results_temp}
                    for f in concurrent.futures.as_completed(futures):
                        if st.session_state.stop_scan: break
                        ftp_temp.append(f.result())
                        done += 1
                        bar.progress(done/len(results_temp))
                        status.markdown(f"**VERIFYING:** {done}/{len(results_temp)}")

                st.session_state.ftp_results = ftp_temp

            st.session_state.check_done = True
            status.empty()
            bar.empty()
            if st.session_state.stop_scan:
                st.warning("SCAN ABORTED BY USER.")
            else:
                st.rerun()

# --- RESULTS ---
if st.session_state.check_done:
    df = pd.DataFrame(st.session_state.results)
    if not df.empty:
        df_ok = df[df['Status'] == "Working"]
        df_dead = df[df['Status'] == "Dead"]
    else:
        df_ok = pd.DataFrame()
        df_dead = pd.DataFrame()
    
    # METRICS
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL_NODES", len(df))
    m2.metric("ACTIVE_NODES", len(df_ok))
    m3.metric("AVG_LATENCY", f"{int(df_ok['Latency'].mean())}ms" if not df_ok.empty else "-")
    m4.metric("TARGETS", len(target_text.strip().split('\n')))

    # CHARTS & MAP
    if not df_ok.empty and PLOTLY_AVAILABLE:
        st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
        st.markdown("##### <span class='neon-text'>GLOBAL_INTELLIGENCE</span>", unsafe_allow_html=True)
        
        # 3D MAP
        fig = px.scatter_geo(
            df_ok, locations="Country", locationmode='ISO-3', hover_name="ISP",
            size="Latency", projection="orthographic", color="Protocol",
            color_discrete_map={"HTTP": "#00f3ff", "SOCKS4": "#bc13fe", "SOCKS5": "#0aff0a"}
        )
        fig.update_layout(
            font=dict(family="Orbitron", color="#00f3ff"),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0,r=0,t=0,b=0),
            geo=dict(bgcolor="rgba(0,0,0,0)", showland=True, landcolor="#0a0f14", oceancolor="#050505", showcountries=True, countrycolor="#333")
        )
        st.plotly_chart(fig, use_container_width=True)

        # CHARTS
        cc1, cc2 = st.columns(2)
        with cc1:
            pc = df_ok['Protocol'].value_counts().reset_index()
            pc.columns = ['Protocol', 'Count']
            fig_p = px.pie(pc, values='Count', names='Protocol', hole=0.5, color_discrete_sequence=['#00f3ff', '#bc13fe', '#0aff0a'])
            fig_p.update_layout(title="PROTOCOLS", title_font_family="Orbitron", paper_bgcolor="rgba(0,0,0,0)", font_color="#ccc")
            st.plotly_chart(fig_p, use_container_width=True)
        with cc2:
            fig_h = px.histogram(df_ok, x="Latency", nbins=20, color_discrete_sequence=['#bc13fe'])
            fig_h.update_layout(title="LATENCY (ms)", title_font_family="Orbitron", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0.3)", font_color="#ccc")
            st.plotly_chart(fig_h, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # FILTER SLIDER
    if not df_ok.empty:
        max_lat = st.slider("LATENCY_FILTER (MS)", 0, 5000, 3000)
        df_filt = df_ok[df_ok['Latency'] <= max_lat]
    else:
        df_filt = df_ok

    # TABS
    st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["🚀 **MATRIX_GRID**", "✅ **ACTIVE_LIST**", "❌ **DEAD_POOL**"])

    # TAB 1: MATRIX (RESTORED DETAILED COPY LOGIC)
    with t1:
        if st.session_state.ftp_results:
            st.markdown("##### CONNECTION MATRIX")
            df_ftp = pd.DataFrame(st.session_state.ftp_results)
            if not df_filt.empty:
                valid_ips = set(df_filt['Full_Address'])
                df_ftp = df_ftp[df_ftp['Raw_IP'].isin(valid_ips)]

            if not df_ftp.empty:
                base = ['Proxy', 'Type']
                t_cols = [c for c in df_ftp.columns if c not in base and c != 'Raw_IP']

                def color_m(val):
                    s = str(val)
                    if 'ACCESS' in s: return 'color:#0f0; font-weight:bold; background:rgba(0,255,0,0.1)'
                    if 'FORBID' in s: return 'color:#fa0'
                    if 'TIME' in s: return 'color:#666'
                    return ''

                sel_matrix = st.dataframe(
                    df_ftp[base + t_cols].style.applymap(color_m),
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="multi-row"
                )
                
                rows = sel_matrix.selection.rows
                if rows:
                    st.info(f"{len(rows)} ROWS SELECTED")
                    selected_data = df_ftp.iloc[rows]
                    copy_lines = []
                    for idx, row in selected_data.iterrows():
                        # RESTORED FEATURE: Show which specific URL opened
                        opened_urls = []
                        for col in t_cols:
                            if "ACCESS_GRANTED" in str(row[col]):
                                opened_urls.append(col)
                        
                        url_str = f" | Opens: {', '.join(opened_urls)}" if opened_urls else ""
                        copy_lines.append(f"{row['Type'].lower()}://{row['Raw_IP']}{url_str}")
                    
                    st.code("\n".join(copy_lines), language="text")
                else:
                    st.caption("SELECT ROWS TO EXTRACT DETAILS")
            else:
                st.warning("NO ACTIVE PROXIES MATCH FILTER.")

    # TAB 2: ACTIVE LIST
    with t2:
        if not df_filt.empty:
            isps = sorted(df_filt['ISP'].unique().tolist())
            c_f1, c_f2 = st.columns([1, 2])
            with c_f1:
                sel_isp = st.selectbox("FILTER_BY_ISP", ["ALL_NETWORKS"] + isps)
            
            if sel_isp != "ALL_NETWORKS":
                df_display = df_filt[df_filt['ISP'] == sel_isp]
            else:
                df_display = df_filt
                
            csv = df_display.to_csv(index=False).encode('utf-8')
            st.download_button("⬇ DOWNLOAD_CSV", csv, f"NETRUNNER_SCAN_{datetime.now().strftime('%M%S')}.csv", "text/csv")

            st.markdown("#### QUICK_COPY")
            st.code("\n".join(df_display['Full_Address'].tolist()), language="text")

            # Updated Columns for Anonymity
            st.dataframe(
                df_display[['IP', 'Port', 'Protocol', 'Anonymity', 'ISP', 'Country', 'Latency']],
                use_container_width=True, hide_index=True
            )
        else:
            st.warning("NO DATA MATCHES FILTERS.")

    # TAB 3: DEAD LIST
    with t3:
        if not df_dead.empty:
            st.dataframe(df_dead[['IP', 'Port', 'Protocol']], use_container_width=True)
            with st.expander("VIEW_DUMP"):
                st.code("\n".join(df_dead['Full_Address']))
    st.markdown('</div>', unsafe_allow_html=True)

# --- TERMINAL ---
if st.session_state.logs:
    st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
    st.caption("🖥️ KERNEL_LOGS")
    logs = "<br>".join([f"<span style='color:var(--neon-cyan)'>&gt;</span> {l}" for l in st.session_state.logs[::-1]])
    st.markdown(f"<div class='terminal-window'>{logs}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- FOOTER ---
st.markdown("""
<div style="position:fixed; bottom:0; left:0; width:100%; background:rgba(0,0,0,0.9); border-top:1px solid #333; text-align:center; font-size:10px; padding:5px; z-index:9999">
    NETRUNNER_V5.0 &nbsp;•&nbsp; CREATED_BY <span class="rakib-brand">RAKIB</span> &nbsp;•&nbsp; <span style='color:var(--neon-green)'>SYSTEM_ONLINE</span>
</div>
""", unsafe_allow_html=True)
