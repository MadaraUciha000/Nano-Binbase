from flask import Flask, request, session, jsonify, render_template_string
from urllib.parse import urlparse
from supabase import create_client, Client
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = "nano_core_ultra_2026_secure"

# =========================
# SUPABASE CONFIG
# =========================
# In Vercel, it is better to use os.environ.get("SUPABASE_URL")
SUPABASE_URL = "https://yfxyhzswspmnnvwuzrbz.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlmeHloenN3c3Btbm52d3V6cmJ6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE4NzAwMTUsImV4cCI6MjA4NzQ0NjAxNX0.6SLZtRie02fRMtdvrMVGv-zi6P4tmbJ89GykuoZ9D3M"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# HELPERS
# =========================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged"):
            return jsonify({"success": False, "msg": "Unauthorized"}), 403
        return f(*args, **kwargs)
    return decorated

def normalize(site):
    if not site: return ""
    site = site.strip().lower()
    if not site.startswith("http"): site = "http://" + site
    parsed = urlparse(site).netloc
    # Handles cases like 'ultahost' (no TLD) or 'google.com'
    return parsed.replace("www.", "") if parsed else site.replace("http://", "").replace("www.", "")

# =========================
# ADMIN API
# =========================

@app.route("/api/admin/login", methods=["POST"])
def login():
    data = request.json
    if data.get("key") == "admin@000":
        session["logged"] = True
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

@app.route("/api/admin/list")
@login_required
def list_sites():
    response = supabase.table("sites").select("*").order("id", desc=True).execute()
    return jsonify(response.data)

@app.route("/api/admin/add", methods=["POST"])
@login_required
def add():
    data = request.json
    site = normalize(data.get("site", ""))
    bin_val = data.get("bin", "")
    
    # Critical Fix: Convert single string/int to list to handle iteration
    bins_to_add = bin_val if isinstance(bin_val, list) else [bin_val]
    
    try:
        for b in bins_to_add:
            supabase.table("sites").insert({"site": site, "bin": str(b)}).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/remove", methods=["POST"])
@login_required
def remove():
    data = request.json
    site = normalize(data.get("site"))
    bin_val = data.get("bin")
    supabase.table("sites").delete().eq("site", site).eq("bin", str(bin_val)).execute()
    return jsonify({"success": True})

@app.route("/api/admin/clear_all", methods=["POST"])
@login_required
def clear_all():
    # Postgres delete requires a filter
    supabase.table("sites").delete().neq("id", -1).execute()
    return jsonify({"success": True})

# =========================
# PUBLIC SEARCH API
# =========================

@app.route("/nano")
def public_search():
    q = request.args.get("search")
    if not q: return jsonify({"status": "error", "msg": "No query"}), 400
    site = normalize(q)
    
    response = supabase.table("sites").select("bin").eq("site", site).execute()
    
    if response.data:
        return jsonify({
            "status": "Found", 
            "site": site, 
            "bins": list(set([r["bin"] for r in response.data]))
        })
    return jsonify({"status": "Not Found", "queried": site}), 404

# =========================
# UI TEMPLATE
# =========================

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

HTML_TEMPLATE = r'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nano Core | Cloud Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: #050505; color: #fff; }
        .glass { background: rgba(15, 15, 15, 0.7); backdrop-filter: blur(14px); border: 1px solid rgba(255,255,255,0.08); }
        .toast-glass { background: rgba(20, 20, 20, 0.9); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }
        .input-saas { background: #0a0a0a; border: 1px solid #1a1a1a; transition: 0.2s; color: #fff; }
        .input-saas:focus { border-color: #3b82f6; outline: none; }
        #app-interface { display: none; }
        .row-hidden { display: none !important; }
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        .animate-toast { animation: slideIn 0.3s ease-out forwards; }
    </style>
</head>
<body class="min-h-screen">
    <div id="toast-container" class="fixed top-6 right-6 z-[100] space-y-3 pointer-events-none"></div>

    <div id="login-screen" class="min-h-screen flex items-center justify-center p-6">
        <div class="w-full max-w-[400px] p-10 glass rounded-[2.5rem] text-center shadow-2xl">
            <div class="inline-flex p-4 bg-blue-600/10 border border-blue-500/20 rounded-2xl mb-6">
                <i data-lucide="shield-check" class="text-blue-500 w-8 h-8"></i>
            </div>
            <h1 class="text-2xl font-bold mb-10 tracking-tight">Nano Core</h1>
            <input type="password" id="auth-key" placeholder="Access Key" class="w-full input-saas p-4 rounded-2xl text-center mb-4">
            <button onclick="attemptLogin()" class="w-full bg-white text-black font-bold py-4 rounded-2xl text-xs uppercase tracking-widest hover:bg-slate-200 transition-all">Initialize Session</button>
        </div>
    </div>

    <div id="app-interface" class="min-h-screen flex flex-col">
        <nav class="h-16 border-b border-white/5 px-8 flex items-center justify-between sticky top-0 bg-[#050505]/90 backdrop-blur-xl z-30">
            <div class="flex items-center gap-2"><i data-lucide="zap" class="text-blue-500 w-5 h-5"></i><span class="font-bold tracking-tight">NANO CORE</span></div>
            <div class="flex gap-6 items-center">
                <button onclick="nuclearClear()" class="text-[10px] font-bold text-orange-400 hover:text-orange-300 transition-colors uppercase tracking-widest">Purge Cloud</button>
                <div class="h-4 w-[1px] bg-white/10"></div>
                <button onclick="location.reload()" class="text-[10px] font-bold text-red-500 uppercase tracking-widest">Logout</button>
            </div>
        </nav>

        <div class="flex flex-col lg:flex-row flex-1 overflow-hidden">
            <aside class="w-full lg:w-80 border-r border-white/5 p-8 space-y-8 bg-[#080808] overflow-y-auto">
                <div>
                    <label class="text-[10px] font-bold text-slate-500 uppercase mb-3 block tracking-widest">Live Search</label>
                    <div class="relative">
                        <i data-lucide="search" class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-600"></i>
                        <input id="search-input" oninput="filterTable()" placeholder="Search site or bin..." class="w-full input-saas pl-10 p-3 rounded-xl text-xs">
                    </div>
                </div>
                <div>
                    <label class="text-[10px] font-bold text-slate-500 uppercase mb-3 block tracking-widest">Registry Control</label>
                    <div class="space-y-3">
                        <input id="as" placeholder="Domain / Site" class="w-full input-saas p-3.5 rounded-xl text-xs">
                        <input id="ab" placeholder="BIN (ID)" class="w-full input-saas p-3.5 rounded-xl text-xs font-mono">
                        <button onclick="addSite()" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3.5 rounded-xl text-[11px] shadow-lg shadow-blue-600/20 transition-all">COMMIT RECORD</button>
                    </div>
                </div>
                <div class="pt-8 border-t border-white/5 grid grid-cols-2 gap-3">
                    <button onclick="exportData()" class="bg-white/5 border border-white/10 py-3 rounded-xl text-[10px] flex items-center justify-center gap-2 hover:bg-white/10 transition-all"><i data-lucide="download" class="w-3 h-3"></i> EXPORT</button>
                    <button onclick="document.getElementById('importFile').click()" class="bg-white/5 border border-white/10 py-3 rounded-xl text-[10px] flex items-center justify-center gap-2 hover:bg-white/10 transition-all"><i data-lucide="upload" class="w-3 h-3"></i> IMPORT</button>
                    <input type="file" id="importFile" class="hidden" onchange="importData(event)">
                </div>
            </aside>

            <main class="flex-1 p-6 lg:p-12 overflow-y-auto">
                <div class="max-w-4xl mx-auto">
                    <div class="flex justify-between items-center mb-8">
                        <div>
                            <h2 class="text-2xl font-bold">Cloud Registry</h2>
                            <p class="text-xs text-slate-500 mt-1">Live synchronized data</p>
                        </div>
                        <span id="record-count" class="text-[10px] font-bold text-blue-400 bg-blue-500/10 px-4 py-1.5 rounded-full border border-blue-500/20">0 RECORDS</span>
                    </div>

                    <div class="glass rounded-3xl overflow-hidden shadow-2xl">
                        <table class="w-full text-left">
                            <thead class="bg-white/5 text-[10px] text-slate-500 uppercase font-bold tracking-widest border-b border-white/5">
                                <tr><th class="px-8 py-5">Endpoint</th><th class="px-8 py-5">BIN Identifier</th><th class="px-8 py-5 text-right">Action</th></tr>
                            </thead>
                            <tbody id="db-body" class="text-xs divide-y divide-white/5"></tbody>
                        </table>
                        <div id="empty-state" class="py-24 text-center hidden">
                            <p class="text-slate-500 text-sm">No data matching your search.</p>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    </div>

    <script>
        lucide.createIcons();

        function toast(msg, type='success') {
            const container = document.getElementById('toast-container');
            const div = document.createElement('div');
            div.className = 'toast-glass p-4 rounded-2xl flex items-center gap-4 min-w-[280px] animate-toast pointer-events-auto shadow-2xl';
            div.innerHTML = `<i data-lucide="${type==='success'?'check-circle':'alert-circle'}" class="w-5 h-5 ${type==='success'?'text-green-400':'text-red-400'}"></i><span class="text-xs font-semibold text-slate-200">${msg}</span>`;
            container.appendChild(div);
            lucide.createIcons();
            setTimeout(() => div.remove(), 3000);
        }

        async function attemptLogin() {
            const res = await fetch('/api/admin/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({key: document.getElementById('auth-key').value})
            });
            if(res.ok) {
                document.getElementById('login-screen').style.display = 'none';
                document.getElementById('app-interface').style.display = 'flex';
                toast('Secure Session Started');
                loadData();
            } else toast('Authentication Denied', 'error');
        }

        async function loadData() {
            const res = await fetch('/api/admin/list');
            const data = await res.json();
            const tbody = document.getElementById('db-body');
            tbody.innerHTML = "";
            data.forEach(item => renderRow(item.site, item.bin));
            updateCount();
        }

        async function addSite() {
            const site = document.getElementById('as').value;
            const binRaw = document.getElementById('ab').value;
            if(!site || !binRaw) return toast('Empty values detected', 'error');
            
            // Allow manual comma-separated BIN entry
            const binArr = binRaw.split(',').map(b => b.trim());
            
            const res = await fetch('/api/admin/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({site, bin: binArr})
            });
            if(res.ok) {
                binArr.forEach(b => renderRow(site, b));
                document.getElementById('as').value = '';
                document.getElementById('ab').value = '';
                toast('Cloud Synced');
                updateCount();
            }
        }

        function renderRow(site, bin) {
            const tbody = document.getElementById('db-body');
            const row = document.createElement('tr');
            row.className = "hover:bg-white/[0.02] transition-colors";
            row.innerHTML = `<td class="px-8 py-5 text-white font-medium">${site}</td>
                             <td class="px-8 py-5 text-slate-400 font-mono tracking-widest">${bin}</td>
                             <td class="px-8 py-5 text-right">
                                <button onclick="removeRow(this, '${site}', '${bin}')" class="text-slate-600 hover:text-red-500 transition-colors">
                                    <i data-lucide="trash-2" class="w-4 h-4"></i>
                                </button>
                             </td>`;
            tbody.prepend(row);
            lucide.createIcons();
        }

        async function removeRow(btn, site, bin) {
            const res = await fetch('/api/admin/remove', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({site, bin})
            });
            if(res.ok) { 
                btn.closest('tr').remove(); 
                updateCount(); 
                toast('Record Removed', 'error'); 
            }
        }

        async function nuclearClear() {
            if(!confirm("⚠️ PERMANENT WIPE: Clear all cloud data?")) return;
            const res = await fetch('/api/admin/clear_all', { method: 'POST' });
            if(res.ok) { 
                document.getElementById('db-body').innerHTML = ""; 
                updateCount(); 
                toast('Cloud Purged', 'error'); 
            }
        }

        function filterTable() {
            const q = document.getElementById('search-input').value.toLowerCase();
            const rows = document.querySelectorAll('#db-body tr');
            let m = 0;
            rows.forEach(r => {
                const visible = r.innerText.toLowerCase().includes(q);
                r.classList.toggle('row-hidden', !visible);
                if(visible) m++;
            });
            document.getElementById('record-count').innerText = m + " MATCHES";
            document.getElementById('empty-state').classList.toggle('hidden', m > 0);
        }

        function updateCount() {
            const count = document.querySelectorAll('#db-body tr').length;
            document.getElementById('record-count').innerText = count + " TOTAL RECORDS";
            document.getElementById('empty-state').classList.toggle('hidden', count > 0);
        }

        function exportData() {
            const rows = Array.from(document.querySelectorAll('#db-body tr'));
            const dataMap = {};
            rows.forEach(r => {
                const s = r.cells[0].innerText;
                const b = r.cells[1].innerText;
                if(!dataMap[s]) dataMap[s] = [];
                dataMap[s].push(b);
            });
            const final = Object.keys(dataMap).map(k => ({site: k, bin: dataMap[k]}));
            const a = document.createElement('a');
            a.href = URL.createObjectURL(new Blob([JSON.stringify(final, null, 2)], {type: 'application/json'}));
            a.download = 'registry_export.json';
            a.click();
        }

        async function importData(e) {
            const file = e.target.files[0];
            const reader = new FileReader();
            reader.onload = async (event) => {
                const data = JSON.parse(event.target.result);
                toast(`Importing ${data.length} segments...`);
                for(const item of data) {
                    await fetch('/api/admin/add', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({site: item.site, bin: item.bin})
                    });
                }
                loadData();
                toast('Cloud Resynced');
            };
            reader.readAsText(file);
        }
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    app.run(debug=True)
