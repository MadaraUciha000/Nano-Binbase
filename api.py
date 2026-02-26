from flask import Flask, request, session, jsonify, render_template_string
from urllib.parse import urlparse
from supabase import create_client, Client
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = "enterprise_core_ultra_2026"

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
    try:
        parsed = urlparse(site).netloc
        return parsed.replace("www.", "") if parsed else site.replace("http://", "").replace("www.", "")
    except:
        return site

# =========================
# ADMIN & PUBLIC API
# =========================

@app.route("/api/admin/login", methods=["POST"])
def login():
    if request.json.get("key") == "Taisirshaik@34":
        session["logged"] = True
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

@app.route("/api/admin/list")
@login_required
def list_sites():
    # Returns raw list for the dashboard management
    res = supabase.table("sites").select("*").order("id", desc=True).execute()
    return jsonify(res.data)

@app.route("/api/admin/batch_add", methods=["POST"])
@login_required
def batch_add():
    """Stable Massive Import: Handles 10,000+ records via recursive chunking"""
    data = request.json
    if not isinstance(data, list): data = [data]
    
    prepared = []
    for item in data:
        site = normalize(item.get("site") or item.get("domain"))
        bin_val = item.get("bin")
        if site and bin_val:
            if isinstance(bin_val, list):
                for b in bin_val: prepared.append({"site": site, "bin": str(b)})
            else:
                prepared.append({"site": site, "bin": str(bin_val)})

    try:
        # Breaks data into chunks of 500 to bypass database timeout limits
        for i in range(0, len(prepared), 500):
            supabase.table("sites").insert(prepared[i:i+500]).execute()
        return jsonify({"success": True, "count": len(prepared)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/clear", methods=["POST"])
@login_required
def clear_db():
    # Wipes entire database table
    supabase.table("sites").delete().gt("id", 0).execute()
    return jsonify({"success": True})

@app.route("/api/admin/remove", methods=["POST"])
@login_required
def remove():
    supabase.table("sites").delete().eq("id", request.json.get("id")).execute()
    return jsonify({"success": True})

# =========================
# NEW ENDPOINTS
# =========================

@app.route("/allbins")
def all_bins():
    """Aggregates all sites and their associated bins into one view"""
    res = supabase.table("sites").select("site, bin").execute()
    grouped = {}
    for entry in res.data:
        site = entry['site']
        if site not in grouped: grouped[site] = set()
        grouped[site].add(entry['bin'])
    
    return jsonify([{ "site": s, "bins": list(b) } for s, b in grouped.items()])

@app.route("/nano")
def public_search():
    q = request.args.get("search")
    if not q: return jsonify({"status": "error"}), 400
    site = normalize(q)
    res = supabase.table("sites").select("bin").eq("site", site).execute()
    if res.data:
        return jsonify({"status": "Found", "site": site, "bins": list(set([r["bin"] for r in res.data]))})
    return jsonify({"status": "Not Found"}), 404

# =========================
# UI TEMPLATE
# =========================

@app.route("/")
def index():
    return render_template_string(UI_HTML)

UI_HTML = r'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enterprise OS</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        :root { --bg: #09090b; --border: rgba(255, 255, 255, 0.08); --accent: #3b82f6; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: #e4e4e7; }
        .mono { font-family: 'JetBrains Mono', monospace; }
        .glass { background: rgba(18, 18, 21, 0.8); backdrop-filter: blur(14px); border: 1px solid var(--border); }
        #processingOverlay { background: rgba(9, 9, 11, 0.85); backdrop-filter: blur(8px); display: none; z-index: 999; }
        #toastContainer { top: 1.5rem; right: 1.5rem; z-index: 1000; }
        .toast { animation: slideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        @keyframes slideIn { from { transform: translateX(100%) scale(0.9); opacity: 0; } to { transform: translateX(0) scale(1); opacity: 1; } }
        .input-field { background: rgba(255, 255, 255, 0.03); border: 1px solid var(--border); outline: none; transition: 0.2s; }
        .input-field:focus { border-color: var(--accent); background: rgba(255, 255, 255, 0.06); }
        .spinner { width: 40px; height: 40px; border: 3px solid rgba(59, 130, 246, 0.1); border-top: 3px solid var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>

<div id="processingOverlay" class="fixed inset-0 flex items-center justify-center">
    <div class="glass p-8 rounded-3xl flex flex-col items-center gap-4 text-center">
        <div class="spinner"></div>
        <p class="mono text-[10px] text-blue-500 uppercase tracking-widest">CLOUD_SYNCHRONIZING</p>
        <h3 id="processCount" class="text-xl font-bold">BATCH PROCESSING...</h3>
    </div>
</div>

<div id="loginScreen" class="fixed inset-0 z-[100] bg-[#09090b] flex items-center justify-center p-6">
    <div class="glass p-8 rounded-3xl w-full max-w-md">
        <h2 class="text-2xl font-bold mb-6">Security Gateway</h2>
        <input id="passwordInput" type="password" placeholder="Passkey" class="input-field w-full p-4 rounded-xl mb-4 mono text-center">
        <button onclick="authenticate()" class="w-full bg-zinc-100 text-black font-bold py-4 rounded-xl hover:bg-white transition">LOGIN</button>
    </div>
</div>

<div id="app" class="hidden opacity-0 transition-opacity duration-700">
    <nav class="border-b border-white/[0.05] sticky top-0 z-40 backdrop-blur-md bg-[#09090b]/50">
        <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <span class="font-bold tracking-tighter text-lg uppercase">Registry.OS</span>
            <div class="flex items-center gap-2">
                <button onclick="triggerImport()" class="glass px-4 py-2 rounded-lg text-xs font-medium">Import</button>
                <button onclick="exportData()" class="glass px-4 py-2 rounded-lg text-xs font-medium">Export</button>
                <button onclick="clearDatabase()" class="px-4 py-2 rounded-lg text-xs font-medium bg-red-500/10 text-red-500 border border-red-500/20 hover:bg-red-500 transition">Purge DB</button>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto p-6 md:p-8 grid lg:grid-cols-12 gap-8">
        <div class="lg:col-span-4 space-y-6">
            <div class="glass p-6 rounded-2xl">
                <h4 class="text-sm font-semibold mb-4">Command Entry</h4>
                <div class="space-y-4">
                    <input id="domainInput" placeholder="domain.com" class="input-field w-full p-3 rounded-xl text-sm mono">
                    <input id="binInput" placeholder="BIN" class="input-field w-full p-3 rounded-xl text-sm mono">
                    <button onclick="addEntry()" class="w-full bg-blue-600 py-3 rounded-xl font-bold text-xs tracking-widest">COMMIT_PUSH</button>
                </div>
            </div>
            <div class="glass p-5 rounded-2xl text-center">
                <p class="text-zinc-500 text-[10px] mono uppercase">Global Nodes</p>
                <h3 id="totalEntries" class="text-3xl font-bold">0</h3>
            </div>
        </div>

        <div class="lg:col-span-8">
            <div class="glass rounded-2xl overflow-hidden">
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm">
                        <thead class="text-zinc-500 text-[11px] uppercase border-b border-white/[0.05] bg-white/[0.02]">
                            <tr><th class="p-4">Domain</th><th class="p-4">Bin</th><th class="p-4 text-right">Action</th></tr>
                        </thead>
                        <tbody id="entryTable" class="divide-y divide-white/[0.03]"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </main>
</div>

<div id="toastContainer" class="fixed flex flex-col gap-3"></div>

<script>
    let entries = [];

    async function authenticate() {
        const res = await fetch("/api/admin/login", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({key: document.getElementById("passwordInput").value})
        });
        if(res.ok) {
            document.getElementById("loginScreen").style.display = 'none';
            document.getElementById("app").classList.remove("hidden");
            setTimeout(() => document.getElementById("app").style.opacity = "1", 50);
            loadData();
            showToast("Authenticated", "success");
        } else showToast("Invalid Key", "error");
    }

    async function loadData() {
        const res = await fetch("/api/admin/list");
        entries = await res.json();
        render();
    }

    function render() {
        const table = document.getElementById("entryTable");
        table.innerHTML = entries.map((e) => `
            <tr class="hover:bg-white/[0.02] transition">
                <td class="p-4 mono text-zinc-300 text-xs">${e.site}</td>
                <td class="p-4"><span class="bg-zinc-800 text-blue-400 px-2 py-0.5 rounded text-[10px] mono border border-white/5">${e.bin}</span></td>
                <td class="p-4 text-right">
                    <button onclick="deleteEntry(${e.id})" class="text-zinc-600 hover:text-red-400 transition"><i data-lucide="trash-2" class="w-4 h-4"></i></button>
                </td>
            </tr>
        `).join('');
        document.getElementById("totalEntries").innerText = entries.length;
        lucide.createIcons();
    }

    async function triggerImport() {
        const input = document.createElement("input");
        input.type = "file";
        input.onchange = async e => {
            const reader = new FileReader();
            reader.onload = async event => {
                const data = JSON.parse(event.target.result);
                document.getElementById("processingOverlay").style.display = "flex";
                
                const res = await fetch("/api/admin/batch_add", {
                    method: "POST", headers: {"Content-Type": "application/json"},
                    body: JSON.stringify(data)
                });
                
                document.getElementById("processingOverlay").style.display = "none";
                if(res.ok) { loadData(); showToast("Import Complete", "success"); }
                else showToast("Import Error", "error");
            };
            reader.readAsText(e.target.files[0]);
        };
        input.click();
    }

    async function clearDatabase() {
        if(!confirm("Wipe all registry data?")) return;
        await fetch("/api/admin/clear", { method: "POST" });
        loadData();
        showToast("Database Purged", "success");
    }

    async function addEntry() {
        const site = document.getElementById("domainInput").value;
        const bin = document.getElementById("binInput").value;
        if(!site || !bin) return;
        await fetch("/api/admin/batch_add", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify([{site, bin}])
        });
        document.getElementById("domainInput").value = "";
        document.getElementById("binInput").value = "";
        loadData();
        showToast("Committed", "success");
    }

    async function deleteEntry(id) {
        await fetch("/api/admin/remove", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({id})
        });
        loadData();
    }

    function exportData() {
        const blob = new Blob([JSON.stringify(entries)], {type: "application/json"});
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "registry_backup.json";
        a.click();
    }

    function showToast(msg, type) {
        const container = document.getElementById("toastContainer");
        const t = document.createElement("div");
        t.className = `toast glass px-6 py-3.5 rounded-xl border-l-4 ${type==='success'?'border-l-blue-500':'border-l-red-500'} flex items-center gap-3`;
        t.innerHTML = `<i data-lucide="${type==='success'?'check-circle':'alert-triangle'}" class="w-4 h-4 ${type==='success'?'text-blue-500':'text-red-500'}"></i><span class="text-xs font-semibold">${msg}</span>`;
        container.appendChild(t);
        lucide.createIcons();
        setTimeout(() => t.remove(), 4000);
    }
</script>
</body>
</html>
'''

if __name__ == "__main__":
    app.run(debug=True)
