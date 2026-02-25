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
        
        /* Loading Screen Styles */
        .loader-overlay { 
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
            background: rgba(0,0,0,0.85); backdrop-filter: blur(8px);
            z-index: 9999; display: none; flex-direction: column;
            align-items: center; justify-content: center;
        }
        .spinner {
            width: 40px; height: 40px; border: 3px solid rgba(59, 130, 246, 0.2);
            border-top: 3px solid #3b82f6; border-radius: 50%;
            animation: spin 1s linear infinite; margin-bottom: 1rem;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        .animate-toast { animation: slideIn 0.3s ease-out forwards; }
    </style>
</head>
<body class="min-h-screen">
    <div id="import-loader" class="loader-overlay">
        <div class="spinner"></div>
        <p class="text-white font-bold text-lg">Importing Cloud Data</p>
        <p id="import-status" class="text-blue-400 text-sm mt-2">Initializing...</p>
    </div>

    <div id="toast-container" class="fixed top-4 right-4 z-50 flex flex-col gap-2"></div>

    <div id="login-screen" class="min-h-screen flex items-center justify-center p-4">
        <div class="glass p-8 rounded-2xl w-full max-w-md">
            <h1 class="text-2xl font-bold mb-6 text-center">Nano Core Admin</h1>
            <input type="password" id="admin-key" placeholder="Access Key" class="input-saas w-full p-3 rounded-xl mb-4 text-center">
            <button onclick="handleLogin()" class="w-full bg-blue-600 hover:bg-blue-700 py-3 rounded-xl font-bold transition">Unlock Dashboard</button>
        </div>
    </div>

    <div id="app-interface" class="p-4 lg:p-8 max-w-7xl mx-auto">
        <header class="flex flex-col md:flex-row justify-between items-center gap-4 mb-8">
            <div>
                <h1 class="text-3xl font-bold">Cloud Registry</h1>
                <p class="text-gray-400">Manage site-to-bin mappings</p>
            </div>
            <div class="flex gap-2">
                <input type="file" id="import-file" class="hidden" accept=".json" onchange="importData(event)">
                <button onclick="document.getElementById('import-file').click()" class="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg flex items-center gap-2 transition">
                    <i data-lucide="upload" class="w-4 h-4"></i> Import
                </button>
                <button onclick="exportData()" class="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg flex items-center gap-2 transition">
                    <i data-lucide="download" class="w-4 h-4"></i> Export
                </button>
            </div>
        </header>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div class="glass p-6 rounded-2xl h-fit">
                <h2 class="text-xl font-bold mb-4">Add Entry</h2>
                <input type="text" id="site-in" placeholder="website.com" class="input-saas w-full p-3 rounded-xl mb-3">
                <input type="text" id="bin-in" placeholder="Bin (comma separated)" class="input-saas w-full p-3 rounded-xl mb-4">
                <button onclick="addEntry()" class="w-full bg-blue-600 hover:bg-blue-700 py-3 rounded-xl font-bold transition">Add to Cloud</button>
            </div>

            <div class="lg:col-span-2 glass rounded-2xl overflow-hidden">
                <div class="p-4 border-b border-white/5 flex justify-between items-center">
                    <input type="text" id="search-db" placeholder="Filter sites..." class="input-saas px-4 py-2 rounded-lg w-64 text-sm" onkeyup="filterTable()">
                    <button onclick="clearAllData()" class="text-red-400 hover:text-red-300 text-sm font-semibold">Clear All</button>
                </div>
                <div class="overflow-x-auto max-h-[600px]">
                    <table class="w-full text-left">
                        <thead class="bg-white/5 text-gray-400 text-sm">
                            <tr>
                                <th class="p-4 font-semibold">Site</th>
                                <th class="p-4 font-semibold">Bin</th>
                                <th class="p-4 text-right">Action</th>
                            </tr>
                        </thead>
                        <tbody id="db-body"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        lucide.createIcons();

        function toast(msg) {
            const container = document.getElementById('toast-container');
            const t = document.createElement('div');
            t.className = 'toast-glass px-6 py-3 rounded-xl text-sm font-medium animate-toast flex items-center gap-3';
            t.innerHTML = `<i data-lucide="info" class="w-4 h-4 text-blue-400"></i> ${msg}`;
            container.appendChild(t);
            lucide.createIcons();
            setTimeout(() => t.remove(), 3000);
        }

        async function handleLogin() {
            const key = document.getElementById('admin-key').value;
            const res = await fetch('/api/admin/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({key})
            });
            if(res.ok) {
                document.getElementById('login-screen').style.display = 'none';
                document.getElementById('app-interface').style.display = 'block';
                loadData();
            } else {
                toast('Invalid access key');
            }
        }

        async function loadData() {
            const res = await fetch('/api/admin/list');
            const data = await res.json();
            const body = document.getElementById('db-body');
            body.innerHTML = data.map(item => `
                <tr class="border-b border-white/5 hover:bg-white/5 transition">
                    <td class="p-4 font-medium">${item.site}</td>
                    <td class="p-4 font-mono text-sm text-blue-400">${item.bin}</td>
                    <td class="p-4 text-right">
                        <button onclick="removeEntry('${item.site}', '${item.bin}')" class="text-gray-500 hover:text-red-400 transition">
                            <i data-lucide="trash-2" class="w-4 h-4"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
            lucide.createIcons();
        }

        async function addEntry() {
            const site = document.getElementById('site-in').value;
            const binStr = document.getElementById('bin-in').value;
            const bins = binStr.split(',').map(b => b.trim()).filter(b => b);
            
            await fetch('/api/admin/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({site, bin: bins})
            });
            document.getElementById('bin-in').value = '';
            loadData();
            toast('Entry updated');
        }

        async function removeEntry(site, bin) {
            await fetch('/api/admin/remove', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({site, bin})
            });
            loadData();
        }

        async function clearAllData() {
            if(!confirm('Delete everything?')) return;
            await fetch('/api/admin/clear_all', { method: 'POST' });
            loadData();
            toast('Database cleared');
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
            if (!file) return;

            const reader = new FileReader();
            reader.onload = async (event) => {
                const data = JSON.parse(event.target.result);
                
                // Show Processing Screen
                const loader = document.getElementById('import-loader');
                const status = document.getElementById('import-status');
                loader.style.display = 'flex';

                let count = 0;
                for(const item of data) {
                    count++;
                    status.innerText = `Processing segment ${count} of ${data.length}...`;
                    
                    await fetch('/api/admin/add', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({site: item.site, bin: item.bin})
                    });
                }
                
                // Hide Processing Screen
                loader.style.display = 'none';
                loadData();
                toast('Cloud Resynced');
            };
            reader.readAsText(file);
        }

        function filterTable() {
            const q = document.getElementById('search-db').value.toLowerCase();
            const rows = document.querySelectorAll('#db-body tr');
            rows.forEach(r => {
                r.style.display = r.innerText.toLowerCase().includes(q) ? '' : 'none';
            });
        }
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    app.run(debug=True)
