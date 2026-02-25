from flask import Flask, request, session, jsonify, render_template_string
from urllib.parse import urlparse
from supabase import create_client, Client
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = "enterprise_cyber_2026_key"

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
# API ENDPOINTS
# =========================

@app.route("/api/admin/login", methods=["POST"])
def login():
    data = request.json
    if data.get("key") == "123":
        session["logged"] = True
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

@app.route("/api/admin/list")
@login_required
def list_sites():
    # Returns all records. Same site with different bins appear as separate rows
    response = supabase.table("sites").select("*").order("id", desc=True).execute()
    return jsonify(response.data)

@app.route("/api/admin/batch_add", methods=["POST"])
@login_required
def batch_add():
    """Stable Batch Import Fix: Handles 1000+ entries without crashing"""
    data = request.json # Expects list of {site, bin}
    if not isinstance(data, list): return jsonify({"error": "Invalid format"}), 400
    
    prepared_data = []
    for item in data:
        site = normalize(item.get("site") or item.get("domain"))
        bin_val = item.get("bin")
        if site and bin_val:
            prepared_data.append({"site": site, "bin": str(bin_val)})

    try:
        # Supabase handles up to 1000 per batch efficiently
        for i in range(0, len(prepared_data), 1000):
            chunk = prepared_data[i:i + 1000]
            supabase.table("sites").insert(chunk).execute()
        return jsonify({"success": True, "count": len(prepared_data)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/remove", methods=["POST"])
@login_required
def remove():
    data = request.json
    supabase.table("sites").delete().eq("id", data.get("id")).execute()
    return jsonify({"success": True})

@app.route("/nano")
def public_search():
    """Groups multiple bins for the same site in public view"""
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
    return render_template_string(UI_TEMPLATE)

UI_TEMPLATE = r'''
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
        :root { --bg: #09090b; --card: #121215; --border: rgba(255, 255, 255, 0.08); --accent: #3b82f6; }
        body { font-family: 'Inter', sans-serif; background-color: var(--bg); color: #e4e4e7; -webkit-font-smoothing: antialiased; }
        .mono { font-family: 'JetBrains Mono', monospace; }
        .glass { background: rgba(18, 18, 21, 0.8); backdrop-filter: blur(12px); border: 1px solid var(--border); }
        #processingOverlay { background: rgba(9, 9, 11, 0.7); backdrop-filter: blur(8px); display: none; z-index: 999; }
        #toastContainer { top: 1.5rem; right: 1.5rem; pointer-events: none; }
        .toast { pointer-events: auto; animation: slideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        @keyframes slideIn { from { transform: translateX(100%) scale(0.9); opacity: 0; } to { transform: translateX(0) scale(1); opacity: 1; } }
        .input-field { background: rgba(255, 255, 255, 0.03); border: 1px solid var(--border); outline: none; transition: 0.2s; }
        .input-field:focus { border-color: var(--accent); box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2); }
        .loader-ring { width: 48px; height: 48px; border: 3px solid rgba(59, 130, 246, 0.1); border-top: 3px solid var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>

<div id="processingOverlay" class="fixed inset-0 flex items-center justify-center">
    <div class="glass p-8 rounded-2xl flex flex-col items-center gap-4 min-w-[280px]">
        <div class="loader-ring"></div>
        <div class="text-center">
            <p id="processTitle" class="mono text-[10px] text-blue-500 uppercase tracking-widest">PROCESSING</p>
            <h3 id="processCount" class="text-xl font-semibold mt-1">0 / 0</h3>
        </div>
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
    <nav class="border-b border-white/[0.05] sticky top-0 z-40 backdrop-blur-md">
        <div class="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
            <span class="font-bold tracking-tighter">CORE.SYSTEM</span>
            <div class="flex gap-2">
                <button onclick="triggerImport()" class="glass px-4 py-2 rounded-lg text-xs font-medium flex items-center gap-2">Import</button>
                <button onclick="handleExport()" class="glass px-4 py-2 rounded-lg text-xs font-medium flex items-center gap-2">Export</button>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto p-4 md:p-8 grid lg:grid-cols-12 gap-8">
        <div class="lg:col-span-4 space-y-6">
            <div class="glass p-6 rounded-2xl">
                <h4 class="text-sm font-semibold mb-4">New Entry</h4>
                <div class="space-y-4">
                    <input id="domainInput" placeholder="domain.com" class="input-field w-full p-3 rounded-xl text-sm mono">
                    <input id="binInput" placeholder="123456" class="input-field w-full p-3 rounded-xl text-sm mono">
                    <button onclick="addEntry()" class="w-full bg-blue-600 py-3 rounded-xl font-bold text-xs tracking-widest">COMMIT</button>
                </div>
            </div>
        </div>
        <div class="lg:col-span-8">
            <div class="glass rounded-2xl overflow-hidden">
                <table class="w-full text-left text-sm">
                    <thead class="text-zinc-500 text-[11px] uppercase border-b border-white/[0.05]">
                        <tr><th class="p-4">Domain</th><th class="p-4">Bin</th><th class="p-4 text-right">Action</th></tr>
                    </thead>
                    <tbody id="entryTable" class="divide-y divide-white/[0.03]"></tbody>
                </table>
            </div>
        </div>
    </main>
</div>

<div id="toastContainer" class="fixed flex flex-col gap-3 z-[1000]"></div>

<script>
    lucide.createIcons();
    let entries = [];

    async function authenticate() {
        const key = document.getElementById("passwordInput").value;
        const res = await fetch("/api/admin/login", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({key})
        });
        if(res.ok) {
            document.getElementById("loginScreen").classList.add("hidden");
            document.getElementById("app").classList.remove("hidden");
            document.getElementById("app").style.opacity = "1";
            loadData();
        } else { showToast("Access Denied", "error"); }
    }

    async function loadData() {
        const res = await fetch("/api/admin/list");
        entries = await res.json();
        renderTable();
    }

    function renderTable() {
        const table = document.getElementById("entryTable");
        table.innerHTML = entries.map((e, i) => `
            <tr class="hover:bg-white/[0.02]">
                <td class="p-4 mono">${e.site}</td>
                <td class="p-4"><span class="bg-zinc-800 px-2 py-0.5 rounded text-[11px] mono">${e.bin}</span></td>
                <td class="p-4 text-right">
                    <button onclick="deleteEntry(${e.id})" class="text-zinc-600 hover:text-red-400"><i data-lucide="trash-2" class="w-4 h-4"></i></button>
                </td>
            </tr>
        `).join('');
        lucide.createIcons();
    }

    async function addEntry() {
        const site = document.getElementById("domainInput").value;
        const bin = document.getElementById("binInput").value;
        const res = await fetch("/api/admin/batch_add", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify([{site, bin}])
        });
        if(res.ok) { loadData(); showToast("Record Committed", "success"); }
    }

    async function deleteEntry(id) {
        await fetch("/api/admin/remove", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({id})
        });
        loadData();
    }

    function triggerImport() {
        const input = document.createElement("input");
        input.type = "file";
        input.onchange = async e => {
            const reader = new FileReader();
            reader.onload = async evt => {
                const data = JSON.parse(evt.target.result);
                const overlay = document.getElementById("processingOverlay");
                overlay.style.display = "flex";
                document.getElementById("processTitle").innerText = "IMPORTING_BATCH";
                
                const res = await fetch("/api/admin/batch_add", {
                    method: "POST", headers: {"Content-Type": "application/json"},
                    body: JSON.stringify(data)
                });
                
                overlay.style.display = "none";
                if(res.ok) { loadData(); showToast("Batch Sync Complete", "success"); }
            };
            reader.readAsText(e.target.files[0]);
        };
        input.click();
    }

    function handleExport() {
        const blob = new Blob([JSON.stringify(entries)], {type:"application/json"});
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "export.json";
        a.click();
        showToast("Backup Created", "success");
    }

    function showToast(msg, type) {
        const t = document.createElement("div");
        t.className = `toast glass px-5 py-3 rounded-xl border-l-4 ${type==='success'?'border-l-blue-500':'border-l-red-500'}`;
        t.innerHTML = `<span class="text-xs font-medium">${msg}</span>`;
        document.getElementById("toastContainer").appendChild(t);
        setTimeout(() => t.remove(), 4000);
    }
</script>
</body>
</html>
'''

if __name__ == "__main__":
    app.run(debug=True)
