import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import requests
import concurrent.futures
import time
import threading
import re
import json
import csv

# --- CONSTANTS ---
JUDGE_URL = "http://httpbin.org/get"  # Returns headers and origin IP
GEO_URL = "http://ip-api.com/json/"   # Free Geo-IP API

class UltimateProxyTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Ultimate Proxy Checker & Organizer")
        self.root.geometry("1100x700")
        
        # State Variables
        self.is_running = False
        self.stop_event = False
        self.proxies_to_check = []
        self.valid_proxies = []
        self.real_ip = self.get_real_ip()

        # --- STYLES ---
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", rowheight=25)
        style.map('Treeview', background=[('selected', '#347083')])

        # --- LAYOUT FRAMES ---
        
        # 1. CONTROL PANEL (Top)
        control_frame = ttk.LabelFrame(root, text="Input & Controls", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # Left side: Buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        ttk.Button(btn_frame, text="📋 Paste Clipboard", command=self.paste_clipboard).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="🌐 Load from URL", command=self.load_from_url_dialog).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="🧹 Remove Dupes", command=self.remove_duplicates).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="❌ Clear List", command=self.clear_list).pack(fill=tk.X, pady=2)

        # Center: Input Text
        self.txt_input = scrolledtext.ScrolledText(control_frame, width=60, height=6)
        self.txt_input.pack(side=tk.LEFT, padx=10)

        # Right side: Settings
        settings_frame = ttk.Frame(control_frame)
        settings_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(settings_frame, text="Timeout (sec):").grid(row=0, column=0, sticky="w")
        self.ent_timeout = ttk.Entry(settings_frame, width=5)
        self.ent_timeout.insert(0, "10")
        self.ent_timeout.grid(row=0, column=1, sticky="w")

        ttk.Label(settings_frame, text="Threads:").grid(row=1, column=0, sticky="w")
        self.scale_threads = ttk.Scale(settings_frame, from_=1, to=100, orient=tk.HORIZONTAL)
        self.scale_threads.set(20)
        self.scale_threads.grid(row=1, column=1, sticky="ew")
        
        self.protocol_var = tk.StringVar(value="AUTO")
        ttk.Label(settings_frame, text="Force Protocol:").grid(row=2, column=0, sticky="w")
        proto_combo = ttk.Combobox(settings_frame, textvariable=self.protocol_var, width=8)
        proto_combo['values'] = ('AUTO', 'HTTP', 'SOCKS4', 'SOCKS5')
        proto_combo.grid(row=2, column=1, sticky="w")

        # 2. ACTION BAR
        action_frame = ttk.Frame(root, padding=10)
        action_frame.pack(fill=tk.X)

        self.btn_start = ttk.Button(action_frame, text="▶ START CHECK", command=self.start_process)
        self.btn_start.pack(side=tk.LEFT, padx=5)

        self.btn_stop = ttk.Button(action_frame, text="⏹ STOP", command=self.stop_process, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        self.lbl_status = ttk.Label(action_frame, text="Idle")
        self.lbl_status.pack(side=tk.LEFT, padx=15)

        self.progress = ttk.Progressbar(action_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)

        # 3. RESULTS TABLE
        self.tree = ttk.Treeview(root, columns=("ip", "port", "proto", "country", "anon", "speed", "status"), show="headings")
        
        self.tree.heading("ip", text="IP Address", command=lambda: self.sort_column("ip", False))
        self.tree.heading("port", text="Port")
        self.tree.heading("proto", text="Protocol")
        self.tree.heading("country", text="Country")
        self.tree.heading("anon", text="Anonymity")
        self.tree.heading("speed", text="Latency (ms)", command=lambda: self.sort_column("speed", False))
        self.tree.heading("status", text="Status")

        self.tree.column("ip", width=120)
        self.tree.column("port", width=60)
        self.tree.column("proto", width=70)
        self.tree.column("country", width=100)
        self.tree.column("anon", width=100)
        self.tree.column("speed", width=80)
        self.tree.column("status", width=200)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10)

        # --- EVENT BINDINGS (RIGHT CLICK & DOUBLE CLICK) ---
        self.context_menu = tk.Menu(root, tearoff=0)
        self.context_menu.add_command(label="📋 Copy Selected (IP:Port)", command=self.copy_selected_rows)
        
        self.tree.bind("<Button-3>", self.show_context_menu) # Windows/Linux Right Click
        self.tree.bind("<Button-2>", self.show_context_menu) # MacOS Right Click
        self.tree.bind("<Double-1>", self.on_double_click_copy) # Double Left Click to Copy Single

        # 4. EXPORT PANEL
        export_frame = ttk.Frame(root, padding=10)
        export_frame.pack(fill=tk.X)
        
        ttk.Label(export_frame, text="Actions:").pack(side=tk.LEFT)
        
        # New Button for Quick Copy
        ttk.Button(export_frame, text="📋 Copy All Working (IP:Port)", command=self.copy_all_working).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(export_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Button(export_frame, text="Export TXT", command=lambda: self.export_data("txt")).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Export CSV", command=lambda: self.export_data("csv")).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Export JSON", command=lambda: self.export_data("json")).pack(side=tk.LEFT, padx=5)

    # --- UTILITIES ---

    def get_real_ip(self):
        try:
            return requests.get("https://api.ipify.org", timeout=5).text
        except:
            return "Unknown"

    def paste_clipboard(self):
        try:
            self.txt_input.insert(tk.END, self.root.clipboard_get() + "\n")
        except:
            pass

    def clear_list(self):
        self.txt_input.delete('1.0', tk.END)

    def load_from_url_dialog(self):
        url = tk.simpledialog.askstring("Load URL", "Enter URL to raw proxy list:")
        if url:
            threading.Thread(target=self._fetch_url, args=(url,)).start()

    def _fetch_url(self, url):
        try:
            self.lbl_status.config(text="Downloading list...")
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                self.txt_input.delete('1.0', tk.END)
                self.txt_input.insert(tk.END, resp.text)
                self.lbl_status.config(text="List loaded from URL.")
            else:
                messagebox.showerror("Error", f"Failed to load URL. Code: {resp.status_code}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def remove_duplicates(self):
        raw = self.txt_input.get('1.0', tk.END).strip().splitlines()
        unique = sorted(list(set(raw)))
        self.txt_input.delete('1.0', tk.END)
        self.txt_input.insert(tk.END, "\n".join(unique))
        self.lbl_status.config(text=f"Removed duplicates. Total: {len(unique)}")

    # --- PARSING ---

    def parse_proxies(self):
        raw_data = self.txt_input.get('1.0', tk.END).strip()
        lines = raw_data.split('\n')
        parsed = []
        
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                ip = parts[0]
                port = parts[1]
                
                protocol_override = self.protocol_var.get().lower()
                protocol = "http" 
                
                if protocol_override != "auto":
                    protocol = protocol_override
                elif len(parts) > 2:
                    line_lower = line.lower()
                    if "socks5" in line_lower: protocol = "socks5"
                    elif "socks4" in line_lower: protocol = "socks4"
                    elif "https" in line_lower: protocol = "https"
                
                if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
                    parsed.append({"ip": ip, "port": port, "protocol": protocol})
        return parsed

    # --- CHECKING ENGINE ---

    def start_process(self):
        self.proxies_to_check = self.parse_proxies()
        if not self.proxies_to_check:
            messagebox.showwarning("Empty", "No valid proxies found.")
            return

        self.is_running = True
        self.stop_event = False
        self.valid_proxies = []
        
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.progress['maximum'] = len(self.proxies_to_check)
        self.progress['value'] = 0

        threading.Thread(target=self.run_checks, daemon=True).start()

    def stop_process(self):
        self.stop_event = True
        self.lbl_status.config(text="Stopping...")

    def run_checks(self):
        max_threads = int(self.scale_threads.get())
        timeout = int(self.ent_timeout.get())

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            future_to_proxy = {
                executor.submit(self.check_proxy, p, timeout): p 
                for p in self.proxies_to_check
            }
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_proxy):
                if self.stop_event:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                
                result = future.result()
                completed += 1
                
                self.root.after(0, self.update_row, result)
                self.root.after(0, self.update_progress, completed)

        self.root.after(0, self.finish_process)

    def check_proxy(self, proxy_data, timeout):
        ip = proxy_data['ip']
        port = proxy_data['port']
        protocol = proxy_data['protocol']
        
        proxy_conf = {
            "http": f"{protocol}://{ip}:{port}",
            "https": f"{protocol}://{ip}:{port}",
        }

        result = {
            "ip": ip, "port": port, "protocol": protocol,
            "valid": False, "latency": 9999, "country": "-", "anon": "-", "status": "Dead"
        }

        try:
            start = time.time()
            resp = requests.get(JUDGE_URL, proxies=proxy_conf, timeout=timeout)
            latency = round((time.time() - start) * 1000)
            
            if resp.status_code == 200:
                result['valid'] = True
                result['latency'] = latency
                
                json_resp = resp.json()
                origin = json_resp.get('origin', '')
                headers = json_resp.get('headers', {})
                
                if self.real_ip in origin:
                    result['anon'] = "Transparent"
                elif 'Via' in headers or 'X-Forwarded-For' in headers:
                    result['anon'] = "Anonymous"
                else:
                    result['anon'] = "Elite"

                try:
                    geo_resp = requests.get(f"{GEO_URL}{ip}", timeout=3).json()
                    if geo_resp['status'] == 'success':
                        result['country'] = f"{geo_resp['countryCode']} - {geo_resp['country']}"
                except:
                    result['country'] = "Unknown"
                    
                result['status'] = "Working"

        except Exception:
            result['status'] = "Connection Failed"
        
        return result

    def update_row(self, data):
        if data['valid']:
            self.valid_proxies.append(data)
            tag = "success"
        else:
            tag = "failed"

        self.tree.insert("", "end", values=(
            data['ip'], data['port'], data['protocol'].upper(),
            data['country'], data['anon'], data['latency'], data['status']
        ), tags=(tag,))
        
        self.tree.tag_configure("success", background="#E8F5E9")
        self.tree.tag_configure("failed", background="#FFEBEE", foreground="#C62828")

    def update_progress(self, val):
        self.progress['value'] = val
        self.lbl_status.config(text=f"Checked {val}/{len(self.proxies_to_check)}")

    def finish_process(self):
        self.is_running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.lbl_status.config(text=f"Done. Found {len(self.valid_proxies)} working proxies.")
        self.sort_column("speed", False)

    # --- COPY & EXPORT ---

    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def on_double_click_copy(self, event):
        """Copies IP:Port when user double clicks a row"""
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        
        vals = self.tree.item(item_id)['values']
        if vals:
            ip, port = vals[0], vals[1]
            text_to_copy = f"{ip}:{port}"
            self.root.clipboard_clear()
            self.root.clipboard_append(text_to_copy)
            self.lbl_status.config(text=f"✅ Copied: {text_to_copy}")

    def copy_all_working(self):
        if not self.valid_proxies:
            messagebox.showinfo("Empty", "No working proxies to copy.")
            return
        
        data = "\n".join([f"{p['ip']}:{p['port']}" for p in self.valid_proxies])
        self.root.clipboard_clear()
        self.root.clipboard_append(data)
        messagebox.showinfo("Copied", f"Copied {len(self.valid_proxies)} proxies to clipboard.")

    def copy_selected_rows(self):
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        copied_data = []
        for item_id in selected_items:
            row_values = self.tree.item(item_id)['values']
            if row_values:
                ip = row_values[0]
                port = row_values[1]
                copied_data.append(f"{ip}:{port}")
        
        if copied_data:
            final_str = "\n".join(copied_data)
            self.root.clipboard_clear()
            self.root.clipboard_append(final_str)
            self.lbl_status.config(text=f"✅ Copied {len(copied_data)} selected proxies.")

    def sort_column(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        
        if col == "speed":
            l.sort(key=lambda t: int(t[0]) if t[0] != 9999 else 999999, reverse=reverse)
        else:
            l.sort(key=lambda t: t[0], reverse=reverse)

        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)

        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def export_data(self, fmt):
        if not self.valid_proxies:
            messagebox.showinfo("Info", "No data to export.")
            return
            
        filename = filedialog.asksaveasfilename(defaultextension=f".{fmt}")
        if not filename: return

        try:
            if fmt == "txt":
                with open(filename, "w") as f:
                    for p in self.valid_proxies:
                        f.write(f"{p['ip']}:{p['port']}\n")
            
            elif fmt == "json":
                with open(filename, "w") as f:
                    json.dump(self.valid_proxies, f, indent=4)
                    
            elif fmt == "csv":
                with open(filename, "w", newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["IP", "Port", "Protocol", "Country", "Anonymity", "Latency"])
                    for p in self.valid_proxies:
                        writer.writerow([p['ip'], p['port'], p['protocol'], p['country'], p['anon'], p['latency']])
                        
            messagebox.showinfo("Success", f"Saved to {filename}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = UltimateProxyTool(root)
    root.mainloop()