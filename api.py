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
SUPABASE_URL = "https://yfxyhzswspmnnvwuzrbz.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlmeHloenN3c3Btbm52d3V6cmJ6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE4NzAwMTUsImV4cCI6MjA4NzQ0NjAxNX0.6SLZtRie02fRMtdvrMVGv-zi6P4tmbJ89GykuoZ9D3M"

# Initialize Supabase Client
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
    return parsed.replace("www.", "") if parsed else site.replace("www.", "")

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
    try:
        response = supabase.table("sites").select("*").order("id", desc=True).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/add", methods=["POST"])
@login_required
def add():
    data = request.json
    site = normalize(data.get("site", ""))
    bin_val = data.get("bin", "")
    if isinstance(bin_val, list): bin_val = bin_val[0] if bin_val else ""
    
    try:
        supabase.table("sites").insert({"site": site, "bin": str(bin_val)}).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/remove", methods=["POST"])
@login_required
def remove():
    data = request.json
    site = normalize(data.get("site"))
    bin_val = data.get("bin")
    try:
        supabase.table("sites").delete().eq("site", site).eq("bin", bin_val).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/clear_all", methods=["POST"])
@login_required
def clear_all():
    try:
        # Postgres hack to delete all: match where ID is not null
        supabase.table("sites").delete().neq("id", -1).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# PUBLIC API
# =========================

@app.route("/nano")
def public_search():
    q = request.args.get("search")
    if not q: return jsonify({"status": "error", "msg": "No query"}), 400
    site = normalize(q)
    
    try:
        response = supabase.table("sites").select("bin").eq("site", site).execute()
        if response.data:
            return jsonify({
                "status": "Found", 
                "site": site, 
                "bins": list(set([r["bin"] for r in response.data]))
            })
        return jsonify({"status": "Not Found", "queried": site}), 404
    except Exception as e:
        return jsonify({"error": "DB_ERROR"}), 500

# =========================
# UI CONSOLE
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
    <title>Nano Core | SaaS Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: #050505; color: #fff; }
        .glass { background: rgba(15, 15, 15, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.08); }
        .toast-glass { background: rgba(20, 20, 20, 0.9); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }
        .input-saas { background: #0a0a0a; border: 1px solid #1a1a1a; transition: 0.2s; color: #fff; }
        .input-saas:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 2px rgba(59,130,246,0.1); }
        #app-interface { display: none; }
        .row-hidden { display: none !important; }
        @keyframes slideIn { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        .animate-up { animation: slideIn 0.4s ease-out forwards; }
    </style>
</head>
<body class="min-h-screen">

    <div id="toast-container" class="fixed top-6 right-6 z-[100] space-y-3 pointer-events-none"></div>

    <div id="login-screen" class="min-h-screen flex items-center justify-center p-6 bg-[#020202]">
        <div class="w-full max-w-[400px] p-10 glass rounded-[2.5rem] shadow-2xl text-center animate-up">
            <div class="inline-flex p-4 bg-blue-600/10 border border-blue-500/20 rounded-2xl mb-6">
                <i data-lucide="shield-check" class="text-blue-500 w-8 h-8"></i>
            </div>
            <h1 class="text-2xl font-bold mb-2">Nano Core</h1>
            <p class="text-slate-500 text-sm mb-10">Secure Management Interface</p>
            <input type="password" id="auth-key" placeholder="Access Key" class="w-full input-saas p-4 rounded-2xl text-center mb-4">
            <button onclick="attemptLogin()" class="w-full bg-white text-black font-bold py-4 rounded-2xl text-xs uppercase tracking-widest hover:bg-slate-200 transition-all">Initialize Session</button>
        </div>
    </div>

    <div id="app-interface" class="min-h-screen flex flex-col">
        <nav class="h-16 border-b border-white/5 px-8 flex items-center justify-between sticky top-0 bg-[#050505]/90 backdrop-blur-xl z-30">
            <div class="flex items-center gap-2">
                <div class="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center"><i data-lucide="zap" class="w-4 h-4 text-white"></i></div>
                <span class="font-bold tracking-tight">NANO<span class="text-blue-500">CORE</span></span>
            </div>
            <div class="flex items-center gap-6">
                <button onclick="nuclearClear()" class="text-[11px] font-bold text-orange-400 hover:text-orange-300">PURGE DB</button>
                <div class="h-4 w-[1px] bg-white/10"></div>
                <button onclick="location.reload()" class="text-[11px] font-bold text-red-500">TERMINATE</button>
            </div>
        </nav>

        <div class="flex flex-col lg:flex-row flex-1">
            <aside class="w-full lg:w-80 border-r border-white/5 p-8 space-y-8 bg-[#080808]">
                <div>
                    <label class="text-[10px] font-bold text-slate-500 uppercase mb-3 block tracking-widest">Live Filter</label>
                    <div class="relative">
                        <i data-lucide="search" class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-600"></i>
                        <input id="search-input" oninput="filterTable()" placeholder="Search site or bin..." class="w-full input-saas pl-10 p-3 rounded-xl text-xs">
                    </div>
                </div>
                <div>
                    <label class="text-[10px] font-bold text-slate-500 uppercase mb-3 block tracking-widest">Add Record</label>
                    <div class="space-y-3">
                        <input id="as" placeholder="Site Domain" class="w-full input-saas p-3.5 rounded-xl text-xs">
                        <input id="ab" placeholder="BIN ID" class="w-full input-saas p-3.5 rounded-xl text-xs font-mono">
                        <button onclick="addSite()" class="w-full bg-blue-600 hover:bg-blue-500 shadow-lg shadow-blue-600/20 text-white font-bold py-3.5 rounded-xl text-[11px] transition-all">COMMIT TO CLOUD</button>
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
                        <h2 class="text-2xl font-bold">Cloud Registry</h2>
                        <span id="record-count" class="text-[10px] font-bold text-blue-400 bg-blue-500/10 px-4 py-1.5 rounded-full tracking-tighter">FETCHING...</span>
                    </div>
                    
                    <div class="glass rounded-3xl overflow-hidden shadow-2xl">
                        <table class="w-full text-left">
                            <thead class="bg-white/5 text-[10px] text-slate-500 uppercase font-bold tracking-widest border-b border-white/5">
                                <tr><th class="px-8 py-5">Endpoint Domain</th><th class="px-8 py-5">BIN Identifier</th><th class="px-8 py-5 text-right">Action</th></tr>
                            </thead>
                            <tbody id="db-body" class="text-xs divide-y divide-white/5"></tbody>
                        </table>
                        <div id="empty-state" class="py-24 text-center hidden">
                            <i data-lucide="database-zap" class="w-10 h-10 text-slate-800 mx-auto mb-4"></i>
                            <p class="text-slate-500 text-sm">No data segments found.</p>
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
            div.className = 'toast-glass p-4 rounded-2xl flex items-center gap-4 min-w-[280px] animate-up pointer-events-auto shadow-2xl';
            div.innerHTML = `<i data-lucide="${type==='success'?'check-circle':'alert-circle'}" class="w-5 h-5 ${type==='success'?'text-green-400':'text-red-400'}"></i><span class="text-xs font-semibold text-slate-200">${msg}</span>`;
            container.appendChild(div);
            lucide.createIcons();
            setTimeout(() => {
                div.style.opacity = '0';
                div.style.transform = 'translateY(-20px)';
                div.style.transition = '0.4s ease';
                setTimeout(() => div.remove(), 400);
            }, 3000);
        }

        async function attemptLogin() {
            const key = document.getElementById('auth-key').value;
            const res = await fetch('/api/admin/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({key})
            });
            if(res.ok) {
                document.getElementById('login-screen').style.display = 'none';
                document.getElementById('app-interface').style.display = 'flex';
                toast('Secure Connection Established');
                loadData();
            } else toast('Authentication Denied', 'error');
        }

        async function loadData() {
            const res = await fetch('/api/admin/list');
            const data = await res.json();
            const tbody = document.getElementById('db-body');
            tbody.innerHTML = "";
            if(data.length === 0) document.getElementById('empty-state').classList.remove('hidden');
            else {
                document.getElementById('empty-state').classList.add('hidden');
                data.forEach(item => renderRow(item.site, item.bin));
            }
            updateCount();
        }

        async function addSite() {
            const site = document.getElementById('as').value;
            const bin = document.getElementById('ab').value;
            if(!site || !bin) return toast('Input fields required', 'error');
            const res = await fetch('/api/admin/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({site, bin})
            });
            if(res.ok) {
                renderRow(site, bin);
                document.getElementById('as').value = '';
                document.getElementById('ab').value = '';
                toast('Cloud Synced Successfully');
                updateCount();
            }
        }

        function renderRow(site, bin) {
            const tbody = document.getElementById('db-body');
            document.getElementById('empty-state').classList.add('hidden');
            const row = document.createElement('tr');
            row.className = "hover:bg-white/[0.03] transition-colors group";
            row.innerHTML = `<td class="px-8 py-5 text-white font-medium">${site}</td>
                             <td class="px-8 py-5 text-slate-400 font-mono tracking-wider">${bin}</td>
                             <td class="px-8 py-5 text-right">
                                <button onclick="removeRow(this, '${site}', '${bin}')" class="text-slate-600 hover:text-red-500 transition-colors">
                                    <i data-lucide="trash-2" class="w-4 h-4"></i>
                                </button>
                             </td>`;
            tbody.prepend(row);
            lucide.createIcons();
        }

        async function removeRow(btn, site, bin) {
            if(!confirm("Destroy this record permanently?")) return;
            const res = await fetch('/api/admin/remove', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({site, bin})
            });
            if(res.ok) { 
                btn.closest('tr').remove(); 
                updateCount(); 
                toast('Segment Purged', 'error'); 
            }
        }

        async function nuclearClear() {
            if(!confirm("⚠️ WARNING: This will wipe the ENTIRE cloud database. Proceed?")) return;
            const res = await fetch('/api/admin/clear_all', { method: 'POST' });
            if(res.ok) { 
                document.getElementById('db-body').innerHTML = ""; 
                updateCount(); 
                toast('Full Database Wipe Complete', 'error'); 
            }
        }

        function filterTable() {
            const q = document.getElementById('search-input').value.toLowerCase();
            const rows = document.querySelectorAll('#db-body tr');
            let matchCount = 0;
            rows.forEach(r => {
                const text = r.innerText.toLowerCase();
                const visible = text.includes(q);
                r.classList.toggle('row-hidden', !visible);
                if(visible) matchCount++;
            });
            document.getElementById('record-count').innerText = matchCount + " MATCHES";
            document.getElementById('empty-state').classList.toggle('hidden', matchCount > 0);
        }

        function updateCount() {
            const count = document.querySelectorAll('#db-body tr').length;
            document.getElementById('record-count').innerText = count + " TOTAL RECORDS";
            document.getElementById('empty-state').classList.toggle('hidden', count > 0);
        }

        function exportData() {
            const data = Array.from(document.querySelectorAll('#db-body tr')).map(r => ({
                site: r.cells[0].innerText, bin: r.cells[1].innerText
            }));
            const a = document.createElement('a');
            a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'}));
            a.download = 'nano_core_export_' + Date.now() + '.json';
            a.click();
            toast('Data Snapshot Exported');
        }

        function importData(e) {
            const reader = new FileReader();
            reader.onload = async (event) => {
                const data = JSON.parse(event.target.result);
                toast(`Importing ${data.length} records...`);
                for(const item of data) {
                    await fetch('/api/admin/add', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(item)
                    });
                }
                loadData();
                toast('Bulk Synchronization Complete');
            };
            reader.readAsText(e.target.files[0]);
        }
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    app.run(debug=True)
