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

# NEW ROUTE: UPDATE/EDIT FEATURE
@app.route("/api/admin/update", methods=["POST"])
@login_required
def update_entry():
    data = request.json
    old_site = normalize(data.get("old_site"))
    old_bin = str(data.get("old_bin"))
    new_site = normalize(data.get("new_site"))
    new_bin = str(data.get("new_bin"))
    
    # Updates the record matching the old values
    supabase.table("sites").update({
        "site": new_site, 
        "bin": new_bin
    }).match({"site": old_site, "bin": old_bin}).execute()
    
    return jsonify({"success": True})

@app.route("/api/admin/remove", methods=["POST"])
@login_required
def remove():
    data = request.json
    site = normalize(data.get("site"))
    bin_val = data.get("bin")
    supabase.table("sites").delete().match({"site": site, "bin": str(bin_val)}).execute()
    return jsonify({"success": True})

@app.route("/")
def admin():
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nano Registry Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        body { background: #050505; color: #e2e8f0; font-family: 'Inter', sans-serif; overflow: hidden; }
        .glass { background: rgba(15, 15, 15, 0.7); backdrop-filter: blur(14px); border: 1px solid rgba(255,255,255,0.08); }
        .input-saas { background: #0a0a0a; border: 1px solid #1a1a1a; transition: 0.2s; color: #fff; }
        .input-saas:focus { border-color: #3b82f6; outline: none; }
        
        /* NEW: Sync Overlay Styles */
        #sync-overlay {
            display: none; position: fixed; inset: 0; z-index: 9999;
            background: rgba(0,0,0,0.9); backdrop-filter: blur(10px);
            flex-direction: column; align-items: center; justify-content: center;
        }
        .progress-container { width: 300px; height: 4px; background: rgba(255,255,255,0.05); border-radius: 10px; overflow: hidden; margin-top: 25px; }
        .progress-fill { height: 100%; background: #3b82f6; width: 0%; transition: width 0.3s ease; box-shadow: 0 0 15px #3b82f6; }

        #app-interface { display: none; }
        .btn-icon { @apply p-2 text-gray-500 hover:bg-white/5 rounded-lg transition-all; }
    </style>
</head>
<body class="flex h-screen">

    <div id="sync-overlay">
        <div class="relative">
            <div class="w-16 h-16 border-2 border-blue-500/20 border-t-blue-500 rounded-full animate-spin"></div>
        </div>
        <h2 class="mt-8 text-sm font-bold tracking-[0.3em] text-blue-500 uppercase">Synchronizing Core</h2>
        <div class="progress-container"><div id="sync-fill" class="progress-fill"></div></div>
        <p id="sync-status" class="mt-4 text-[10px] font-mono text-gray-500 uppercase">Encapsulating data segments...</p>
    </div>

    <div id="login-screen" class="w-full flex items-center justify-center p-6">
        <div class="glass p-10 rounded-3xl w-full max-w-sm shadow-2xl">
            <h1 class="text-xl font-bold mb-6 text-center">Nano Core Access</h1>
            <input type="password" id="auth-key" placeholder="Access Key" class="w-full input-saas px-4 py-3 rounded-xl mb-4 text-center">
            <button onclick="login()" class="w-full bg-blue-600 hover:bg-blue-500 py-3 rounded-xl font-bold transition-all">Unlock</button>
        </div>
    </div>

    <div id="app-interface" class="w-full flex">
        <aside class="w-64 border-r border-white/5 flex flex-col p-6 bg-[#080808]">
            <div class="flex items-center gap-3 mb-10">
                <div class="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center font-bold">N</div>
                <span class="font-bold tracking-tighter">NANO REGISTRY</span>
            </div>
            <nav class="flex-1 space-y-2">
                <div class="bg-blue-600/10 text-blue-400 px-4 py-3 rounded-xl text-xs font-bold flex items-center gap-3 cursor-pointer">
                    <i data-lucide="database" class="w-4 h-4"></i> REGISTRY
                </div>
            </nav>
            <button onclick="location.reload()" class="text-red-500 text-[10px] font-bold py-3 text-left">TERMINATE SESSION</button>
        </aside>

        <main class="flex-1 flex flex-col min-w-0">
            <header class="h-16 border-b border-white/5 flex items-center justify-between px-10 bg-[#050505]">
                <div class="flex items-center gap-4 bg-black/40 border border-white/5 px-4 py-1.5 rounded-xl w-80">
                    <i data-lucide="search" class="w-3 h-3 text-gray-500"></i>
                    <input type="text" id="search-input" onkeyup="filterTable()" placeholder="Search registry..." class="bg-transparent text-xs w-full outline-none">
                </div>
                <div class="flex gap-3">
                    <button onclick="exportData()" class="text-[10px] font-bold text-gray-400 px-3 py-2 border border-white/5 rounded-lg hover:text-white transition">EXPORT</button>
                    <button onclick="document.getElementById('import-file').click()" class="text-[10px] font-bold text-white bg-blue-600 px-4 py-2 rounded-lg hover:bg-blue-500 transition">IMPORT JSON</button>
                    <input type="file" id="import-file" class="hidden" onchange="importData(event)">
                </div>
            </header>

            <div class="flex-1 overflow-y-auto p-10">
                <div class="glass p-6 rounded-2xl mb-8 flex gap-4 items-center">
                    <input type="text" id="site-in" placeholder="Source Domain" class="flex-1 input-saas px-4 py-2.5 rounded-xl text-sm">
                    <input type="text" id="bin-in" placeholder="Target Bin" class="flex-1 input-saas px-4 py-2.5 rounded-xl text-sm">
                    <button id="commit-btn" onclick="saveRecord()" class="bg-blue-600 hover:bg-blue-500 px-8 py-2.5 rounded-xl text-xs font-bold transition-all shadow-lg shadow-blue-600/20">Commit</button>
                    <button id="cancel-edit-btn" onclick="cancelEdit()" class="hidden text-red-500 text-xs font-bold px-2 hover:underline">Cancel</button>
                </div>

                <div class="glass rounded-2xl overflow-hidden">
                    <table class="w-full text-left text-sm">
                        <thead class="bg-white/5 text-[10px] font-bold text-gray-500 uppercase tracking-widest border-b border-white/5">
                            <tr>
                                <th class="px-8 py-4">Domain Endpoint</th>
                                <th class="px-8 py-4">Mapping Bin</th>
                                <th class="px-8 py-4 text-right">Operations</th>
                            </tr>
                        </thead>
                        <tbody id="db-body" class="divide-y divide-white/5"></tbody>
                    </table>
                </div>
            </div>
        </main>
    </div>

    <script>
        lucide.createIcons();
        let editingRef = null; // Stores original data when editing

        async function login() {
            const key = document.getElementById('auth-key').value;
            const res = await fetch('/api/admin/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({key})
            });
            if(res.ok) {
                document.getElementById('login-screen').style.display = 'none';
                document.getElementById('app-interface').style.display = 'flex';
                loadData();
            }
        }

        async function loadData() {
            const res = await fetch('/api/admin/list');
            const data = await res.json();
            const body = document.getElementById('db-body');
            body.innerHTML = data.map(item => `
                <tr class="hover:bg-white/[0.01] transition-all group">
                    <td class="px-8 py-4 font-bold text-white">${item.site}</td>
                    <td class="px-8 py-4 font-mono text-blue-400 font-semibold">${item.bin}</td>
                    <td class="px-8 py-4 text-right">
                        <div class="flex justify-end gap-1">
                            <button onclick='startEdit("${item.site}", "${item.bin}")' class="p-2 text-gray-500 hover:text-blue-500 transition"><i data-lucide="pencil" class="w-4 h-4"></i></button>
                            <button onclick='removeRecord("${item.site}", "${item.bin}")' class="p-2 text-gray-500 hover:text-red-500 transition"><i data-lucide="trash-2" class="w-4 h-4"></i></button>
                        </div>
                    </td>
                </tr>
            `).join('');
            lucide.createIcons();
        }

        // NEW: PENCIL EDIT START
        function startEdit(site, bin) {
            editingRef = {site, bin};
            document.getElementById('site-in').value = site;
            document.getElementById('bin-in').value = bin;
            document.getElementById('commit-btn').innerText = "Update Record";
            document.getElementById('cancel-edit-btn').classList.remove('hidden');
            document.getElementById('site-in').focus();
        }

        // NEW: CANCEL EDIT
        function cancelEdit() {
            editingRef = null;
            document.getElementById('site-in').value = '';
            document.getElementById('bin-in').value = '';
            document.getElementById('commit-btn').innerText = "Commit";
            document.getElementById('cancel-edit-btn').classList.add('hidden');
        }

        async function saveRecord() {
            const site = document.getElementById('site-in').value;
            const bin = document.getElementById('bin-in').value;
            if(!site || !bin) return;

            if(editingRef) {
                // RUN UPDATE API
                await fetch('/api/admin/update', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        old_site: editingRef.site, 
                        old_bin: editingRef.bin,
                        new_site: site, 
                        new_bin: bin
                    })
                });
                cancelEdit();
            } else {
                // RUN ADD API
                await fetch('/api/admin/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({site, bin})
                });
            }
            document.getElementById('site-in').value = '';
            document.getElementById('bin-in').value = '';
            loadData();
        }

        async function removeRecord(site, bin) {
            await fetch('/api/admin/remove', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({site, bin})
            });
            loadData();
        }

        function exportData() {
            const rows = Array.from(document.querySelectorAll('#db-body tr'));
            const data = rows.map(r => ({site: r.cells[0].innerText, bin: r.cells[1].innerText}));
            const a = document.createElement('a');
            a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'}));
            a.download = 'registry_export.json'; a.click();
        }

        // NEW: SMOOTH IMPORTING LOADING SCREEN
        async function importData(e) {
            const file = e.target.files[0];
            const reader = new FileReader();
            reader.onload = async (event) => {
                const data = JSON.parse(event.target.result);
                const overlay = document.getElementById('sync-overlay');
                const fill = document.getElementById('sync-fill');
                const status = document.getElementById('sync-status');
                
                overlay.style.display = 'flex';

                for(let i=0; i < data.length; i++) {
                    const pct = Math.round(((i+1)/data.length)*100);
                    fill.style.width = pct + '%';
                    status.innerText = `WRITING BLOCK ${i+1} OF ${data.length}...`;
                    
                    await fetch('/api/admin/add', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({site: data[i].site, bin: data[i].bin})
                    });
                }
                setTimeout(() => { 
                    overlay.style.display = 'none'; 
                    fill.style.width = '0%';
                    loadData(); 
                }, 800);
            };
            reader.readAsText(file);
        }

        function filterTable() {
            const q = document.getElementById('search-input').value.toLowerCase();
            document.querySelectorAll('#db-body tr').forEach(r => {
                r.style.display = r.innerText.toLowerCase().includes(q) ? '' : 'none';
            });
        }
    </script>
</body>
</html>
''')

if __name__ == "__main__":
    app.run(debug=True)
