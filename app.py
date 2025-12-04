import streamlit as st
import requests
import concurrent.futures
import time
import re
import pandas as pd
import json

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Ultimate Proxy Tool",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SESSION STATE MANAGEMENT ---
if 'proxy_text' not in st.session_state:
    st.session_state.proxy_text = ""
if 'results' not in st.session_state:
    st.session_state.results = []
if 'check_done' not in st.session_state:
    st.session_state.check_done = False

# --- CONSTANTS ---
JUDGE_URL = "http://httpbin.org/get"
GEO_URL = "http://ip-api.com/json/"

# --- NETWORK FUNCTIONS ---
def get_real_ip():
    """Gets the server's real IP to detect transparency."""
    try:
        return requests.get("https://api.ipify.org", timeout=3).text
    except:
        return "Unknown"

def fetch_from_url(url):
    """Downloads raw text from a URL."""
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.text
        return None
    except:
        return None

def check_proxy(proxy_data, timeout, real_ip):
    """Checks a single proxy for validity, speed, and anonymity."""
    ip = proxy_data['ip']
    port = proxy_data['port']
    protocol = proxy_data['protocol']
    
    proxy_conf = {
        "http": f"{protocol}://{ip}:{port}",
        "https": f"{protocol}://{ip}:{port}",
    }

    result = {
        "IP": ip, 
        "Port": port, 
        "Protocol": protocol.upper(),
        "Country": "-", 
        "Anonymity": "-", 
        "Latency": 9999, 
        "Status": "Dead",
        "Full_Address": f"{ip}:{port}" # Hidden field for copying
    }

    try:
        start = time.time()
        # The Check
        resp = requests.get(JUDGE_URL, proxies=proxy_conf, timeout=timeout)
        latency = round((time.time() - start) * 1000)
        
        if resp.status_code == 200:
            result['Latency'] = latency
            result['Status'] = "Working"
            
            # 1. Anonymity Logic
            try:
                json_resp = resp.json()
                origin = json_resp.get('origin', '')
                headers = json_resp.get('headers', {})
                if real_ip in origin:
                    result['Anonymity'] = "Transparent"
                elif 'Via' in headers or 'X-Forwarded-For' in headers:
                    result['Anonymity'] = "Anonymous"
                else:
                    result['Anonymity'] = "Elite"
            except:
                result['Anonymity'] = "Unknown"

            # 2. Geo-Location Logic
            try:
                geo_resp = requests.get(f"{GEO_URL}{ip}", timeout=2).json()
                if geo_resp['status'] == 'success':
                    result['Country'] = geo_resp['countryCode']
            except:
                pass
    except:
        pass # Proxy is dead or timed out
    
    return result

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    threads = st.slider("Threads (Speed)", 1, 50, 25, help="Higher = Faster, but might get blocked.")
    timeout = st.number_input("Timeout (seconds)", value=10, min_value=1)
    force_proto = st.selectbox("Force Protocol", ["AUTO", "http", "socks4", "socks5"])
    
    st.markdown("---")
    st.markdown("""
    **How to Copy IP:Port:**
    1. Run the check.
    2. Click the **checkboxes** in the result table.
    3. A copyable code block will appear.
    """)

# --- MAIN UI ---
st.title("🛡️ Ultimate Proxy Tool")
st.markdown("Check, Sort, Filter and Organize proxies directly in the cloud.")

# TABS
tab1, tab2 = st.tabs(["📋 Paste List", "🌐 Load from URL"])

with tab1:
    st.session_state.proxy_text = st.text_area(
        "Paste Proxies Here", 
        value=st.session_state.proxy_text,
        height=150, 
        placeholder="103.141.67.50 9090 socks5\n113.212.109.40 1080",
        label_visibility="collapsed"
    )
    
    c1, c2 = st.columns([1, 4])
    if c1.button("🗑️ Clear", use_container_width=True):
        st.session_state.proxy_text = ""
        st.session_state.results = []
        st.session_state.check_done = False
        st.rerun()
        
    if c2.button("🧹 Remove Duplicates", use_container_width=True):
        raw_list = st.session_state.proxy_text.strip().split('\n')
        # Clean logic
        unique = sorted(list(set([line.strip() for line in raw_list if line.strip()])))
        st.session_state.proxy_text = "\n".join(unique)
        st.toast(f"Duplicates removed! Total unique: {len(unique)}", icon="✅")
        st.rerun()

with tab2:
    url_input = st.text_input("Enter URL to Raw Text File")
    if st.button("📥 Load URL"):
        with st.spinner("Downloading..."):
            data = fetch_from_url(url_input)
            if data:
                st.session_state.proxy_text = data
                st.success("Loaded! Switch to 'Paste List' tab.")
                st.rerun()
            else:
                st.error("Failed to load URL.")

# --- CHECKER LOGIC ---
if st.button("▶ START CHECK", type="primary", use_container_width=True):
    # Reset previous results
    st.session_state.results = []
    st.session_state.check_done = False
    
    # Parse Input
    lines = st.session_state.proxy_text.strip().split('\n')
    proxies_to_check = []
    seen = set()
    
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            ip = parts[0]
            port = parts[1]
            if f"{ip}:{port}" not in seen:
                seen.add(f"{ip}:{port}")
                
                # Protocol Logic
                proto = force_proto if force_proto != "AUTO" else "http"
                if force_proto == "AUTO":
                    if "socks5" in line.lower(): proto = "socks5"
                    elif "socks4" in line.lower(): proto = "socks4"
                    elif "https" in line.lower(): proto = "https"
                
                # IP Validation Regex
                if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
                    proxies_to_check.append({"ip": ip, "port": port, "protocol": proto})

    if not proxies_to_check:
        st.warning("No valid IPs found.")
    else:
        # Run Threads
        real_ip = get_real_ip()
        results_temp = []
        
        prog_bar = st.progress(0)
        status_txt = st.empty()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_proxy = {executor.submit(check_proxy, p, timeout, real_ip): p for p in proxies_to_check}
            completed = 0
            
            for future in concurrent.futures.as_completed(future_to_proxy):
                data = future.result()
                if data['Status'] == "Working":
                    results_temp.append(data)
                
                completed += 1
                prog_bar.progress(completed / len(proxies_to_check))
                status_txt.caption(f"Checking: {completed}/{len(proxies_to_check)}")
        
        st.session_state.results = results_temp
        st.session_state.check_done = True
        prog_bar.empty()
        status_txt.empty()
        st.rerun()

# --- RESULTS DISPLAY ---
if st.session_state.check_done:
    if not st.session_state.results:
        st.error("All proxies failed.")
    else:
        df = pd.DataFrame(st.session_state.results)
        df = df.sort_values(by="Latency")
        
        st.divider()
        st.subheader(f"✅ Working Proxies: {len(df)}")
        
        # Split Layout: Table vs Copy Box
        col_table, col_actions = st.columns([3, 1])
        
        with col_table:
            st.caption("👇 Select checkboxes to Copy")
            # Interactive Table with Selection
            selection = st.dataframe(
                df,
                column_config={
                    "Latency": st.column_config.NumberColumn(format="%d ms"),
                    "Full_Address": None # Hide the helper column
                },
                use_container_width=True,
                hide_index=True,
                on_select="rerun",  # Critical for the feature to work
                selection_mode="multi-row"
            )

        with col_actions:
            # COPY LOGIC
            selected_rows = selection.selection.rows
            if selected_rows:
                # Get selected data
                subset = df.iloc[selected_rows]
                copy_text = "\n".join(subset['Full_Address'].tolist())
                
                st.info(f"{len(selected_rows)} Selected")
                # Streamlit's Code block has a built-in Copy Button
                st.code(copy_text, language="text")
                st.caption("⬆ Click the copy icon in the box above.")
            else:
                st.info("Select rows in the table to generate a copy list.")

        # EXPORT SECTION
        st.markdown("### 📂 Export All")
        
        # Prepare file formats
        txt_all = "\n".join(df['Full_Address'].tolist())
        csv_all = df.drop(columns=['Full_Address']).to_csv(index=False).encode('utf-8')
        json_all = json.dumps(st.session_state.results, indent=4)
        
        b1, b2, b3 = st.columns(3)
        b1.download_button("📄 TXT (IP:Port)", txt_all, "proxies.txt", "text/plain")
        b2.download_button("📊 CSV (Excel)", csv_all, "proxies.csv", "text/csv")
        b3.download_button("📦 JSON", json_all, "proxies.json", "application/json")
