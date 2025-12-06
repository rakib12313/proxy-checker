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

# --- CUSTOM STYLING ---
st.markdown("""
    <style>
    .stApp {background-color: #0e1117;}
    
    /* Live Log Styling */
    .terminal-log {
        background-color: #000000;
        color: #00ff00;
        font-family: 'Courier New', monospace;
        padding: 10px;
        border-radius: 5px;
        height: 150px;
        overflow-y: auto;
        font-size: 12px;
        border: 1px solid #333;
    }
    
    /* Footer */
    .footer {
        width: 100%;
        text-align: center;
        padding: 15px;
        margin-top: 50px;
        color: #555;
        font-size: 12px;
        border-top: 1px solid #333;
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
    if len(st.session_state.logs) > 50:
        st.session_state.logs.pop(0)

def get_real_ip():
    try: return requests.get("https://api.ipify.org", timeout=3).text
    except: return "Unknown"

def fetch_from_url(url):
    try:
        resp = requests.get(url, timeout=10)
        return resp.text if resp.status_code == 200 else None
    except: return None

# 1. General Check + ISP DETECTION
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
                proxy_result[url] = "⛔ 403 (Blocked)"
            elif resp.status_code == 404:
                proxy_result[url] = "⚠️ 404 (Not Found)"
            else:
                proxy_result[url] = f"⚠️ {resp.status_code}"
        except:
            proxy_result[url] = "❌"
            
    return proxy_result

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Proxy Master")
    st.markdown("### By **RAKIB**")
    st.divider()
    
    with st.expander("⚙️ Advanced Settings", expanded=True):
        threads = st.slider("Threads", 5, 50, 25)
        timeout = st.slider("Timeout", 1, 15, 6)
        force_proto = st.selectbox("Protocol", ["AUTO", "http", "socks4", "socks5"])
    
    st.info("Supported: ip:port | protocol://ip:port")

# --- MAIN UI ---
st.title("🚀 Proxy & BDIX Master")
st.markdown("**Created by RAKIB** | *v4.3 Professional*")

# INPUT SECTION
tab1, tab2 = st.tabs(["📋 Proxies", "🎯 BDIX/FTP Targets"])

with tab1:
    st.session_state.proxy_text = st.text_area(
        "Paste Proxies", value=st.session_state.proxy_text, height=120, 
        placeholder="socks5://103.141.67.50:9090\n113.212.109.40:1080", 
        label_visibility="collapsed"
    )
    c1, c2 = st.columns(2)
    if c1.button("🗑️ Clear Input", use_container_width=True):
        st.session_state.proxy_text = ""
        st.session_state.results = []
        st.session_state.ftp_results = []
        st.session_state.check_done = False
        st.session_state.logs = []
        st.rerun()
    if c2.button("🧹 Remove Dupes", use_container_width=True):
        raw = st.session_state.proxy_text.strip().split('\n')
        unique = sorted(list(set([l.strip() for l in raw if l.strip()])))
        st.session_state.proxy_text = "\n".join(unique)
        st.rerun()

with tab2:
    st.info("Proxies will be tested against these URLs:")
    target_text = st.text_area("Target URLs", value=DEFAULT_TARGETS, height=120)

# START BUTTON
if st.button("▶ START INTELLIGENT SCAN", type="primary", use_container_width=True):
    st.session_state.results = []
    st.session_state.ftp_results = []
    st.session_state.check_done = False
    st.session_state.logs = []
    
    lines = st.session_state.proxy_text.strip().split('\n')
    proxies_to_check = []
    seen = set()
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        ip, port, proto = None, None, None
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
        st.warning("No valid proxies found.")
    else:
        # PHASE 1
        real_ip = get_real_ip()
        results_temp = []
        col_p1, col_p2 = st.columns([3, 1])
        with col_p1: bar = st.progress(0)
        with col_p2: status = st.empty()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_proxy = {executor.submit(check_proxy_basic, p, timeout, real_ip): p for p in proxies_to_check}
            completed = 0
            for future in concurrent.futures.as_completed(future_to_proxy):
                res = future.result()
                results_temp.append(res)
                completed += 1
                bar.progress(completed / len(proxies_to_check))
                status.markdown(f"**Scan: {completed}/{len(proxies_to_check)}**")
                if res['Status'] == 'Working': log_event(f"SUCCESS: {res['IP']} ({res['ISP']})")
                
        st.session_state.results = results_temp
        
        # PHASE 2
        log_event("Starting Target Checks...")
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
                status.markdown(f"**Target: {completed}/{len(results_temp)}**")

        st.session_state.ftp_results = ftp_temp
        st.session_state.check_done = True
        status.markdown("**✅ DONE**")
        st.rerun()

# --- RESULTS DISPLAY ---
if st.session_state.check_done:
    df = pd.DataFrame(st.session_state.results)
    df_working = df[df['Status'] == "Working"]
    df_dead = df[df['Status'] == "Dead"]
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total", len(df))
    m2.metric("Working", len(df_working))
    m3.metric("Avg Latency", f"{int(df_working['Latency'].mean())}ms" if not df_working.empty else "-")
    m4.metric("Targets Hit", "View Below")

    res_tab1, res_tab2, res_tab3 = st.tabs(["🎯 BDIX/FTP Matrix", "✅ Working & ISPs", "❌ Dead"])

    # --- TAB 1: FTP MATRIX (ENHANCED COPY) ---
    with res_tab1:
        if st.session_state.ftp_results:
            st.markdown("💡 **Tip:** Look for cells marked `✅ 200 OK`.")
            df_ftp = pd.DataFrame(st.session_state.ftp_results)
            
            # 1. Identify Successful Rows
            # Check if any column contains "✅"
            success_mask = df_ftp.astype(str).apply(lambda x: x.str.contains('✅')).any(axis=1)
            success_proxies = df_ftp[success_mask].copy()

            # 2. Show Main Matrix Table
            base_cols = ['Proxy', 'Type']
            target_cols = [c for c in df_ftp.columns if c not in base_cols and c != 'Raw_IP']
            
            def color_matrix(val):
                if '✅' in str(val): return 'background-color: #28a745; color: white;'
                if '⛔' in str(val): return 'background-color: #ffc107; color: black;'
                return ''
            
            st.dataframe(df_ftp[base_cols + target_cols].style.applymap(color_matrix), use_container_width=True)

            st.divider()
            st.subheader("📋 Copy Successful Proxies")

            if not success_proxies.empty:
                # 3. Create Detailed Format for Copying
                # Function to generate string: "PROTO://IP:PORT | Opens: url1, url2"
                def format_success_row(row):
                    worked_urls = []
                    for col in target_cols:
                        if '✅' in str(row[col]):
                            worked_urls.append(col)
                    
                    proto_prefix = f"{row['Type']}://".lower()
                    return f"{proto_prefix}{row['Raw_IP']} | Opens: {', '.join(worked_urls)}"

                success_proxies['Copy_Format'] = success_proxies.apply(format_success_row, axis=1)

                col_sel, col_code = st.columns([3, 2])
                
                with col_sel:
                    st.caption("👇 **Select checkboxes** to copy specific proxies.")
                    # Show a clean table for selection
                    sel_ftp = st.dataframe(
                        success_proxies[['Type', 'Raw_IP', 'Copy_Format']],
                        column_config={
                            "Copy_Format": None, # Hide the long string
                            "Raw_IP": "IP Address"
                        },
                        use_container_width=True,
                        hide_index=True,
                        on_select="rerun",
                        selection_mode="multi-row"
                    )

                with col_code:
                    # Logic for Copy Box
                    rows = sel_ftp.selection.rows
                    if rows:
                        # Copy Selected
                        txt = "\n".join(success_proxies.iloc[rows]['Copy_Format'].tolist())
                        st.info(f"{len(rows)} Selected")
                        st.code(txt, language="text")
                        st.caption("⬆ Click icon to copy selection")
                    else:
                        # Copy All
                        all_txt = "\n".join(success_proxies['Copy_Format'].tolist())
                        st.markdown("**Copy All Working:**")
                        st.code(all_txt, language="text")
                        st.caption("⬆ Click icon to copy all")
            else:
                st.warning("No proxies opened any of your target URLs.")

        else:
            st.info("No results yet.")

    # TAB 2: WORKING & ISP
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
                isps = sorted(df_working['ISP'].unique().tolist())
                selected_isp = st.selectbox("Quick Copy by ISP:", ["All"] + isps)
                if selected_isp != "All":
                    filtered = df_working[df_working['ISP'] == selected_isp]
                    st.code("\n".join(filtered['Full_Address'].tolist()))
                else:
                    with st.expander("Show All Working List"):
                        st.code("\n".join(df_working['Full_Address'].tolist()))
        else:
            st.warning("No working proxies.")

    # TAB 3: DEAD
    with res_tab3:
        if not df_dead.empty:
            st.dataframe(df_dead[['IP', 'Port', 'Protocol', 'Status']], use_container_width=True, hide_index=True)
            with st.expander("Copy Dead List"):
                st.code("\n".join(df_dead['Full_Address'].tolist()))

# --- FOOTER ---
st.markdown("""
<div class="footer">
    Developed with ❤️ by <b>RAKIB</b><br>
    BDIX Specialist • ISP Detection • Latency Grading
</div>
""", unsafe_allow_html=True)
