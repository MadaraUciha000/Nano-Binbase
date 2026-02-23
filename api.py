from flask import Flask, request, session, jsonify, render_template_string
from urllib.parse import urlparse
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = "nano_core_ultra_2026"

DB_FILE = "nano.db"

# =========================
# DB SETUP
# =========================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS sites (id INTEGER PRIMARY KEY AUTOINCREMENT, site TEXT, bin TEXT)")
    conn.commit()
    conn.close()

init_db()

def db_op(query, args=(), fetch=False):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(query, args)
    res = c.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return res

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
    site = site.strip().lower()
    if not site.startswith("http"): site = "http://" + site
    parsed = urlparse(site).netloc
    return parsed.replace("www.", "") if parsed else site.replace("www.", "")

# =========================
# ADMIN API ROUTES
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
    rows = db_op("SELECT site, bin FROM sites ORDER BY id DESC", fetch=True)
    return jsonify([{"site": r["site"], "bin": r["bin"]} for r in rows])

@app.route("/api/admin/add", methods=["POST"])
@login_required
def add():
    data = request.json
    site = normalize(data["site"])
    bin_val = data["bin"]
    if isinstance(bin_val, list): bin_val = bin_val[0] if bin_val else ""
    db_op("INSERT INTO sites (site, bin) VALUES (?,?)", (site, str(bin_val)))
    return jsonify({"success": True})

@app.route("/api/admin/remove", methods=["POST"])
@login_required
def remove():
    data = request.json
    db_op("DELETE FROM sites WHERE site=? AND bin=?", (normalize(data["site"]), data["bin"]))
    return jsonify({"success": True})

@app.route("/api/admin/clear_all", methods=["POST"])
@login_required
def clear_all():
    db_op("DELETE FROM sites")
    return jsonify({"success": True})

# =========================
# PUBLIC SEARCH API
# =========================

@app.route("/nano")
def public_search():
    q = request.args.get("search")
    if not q: return jsonify({"status": "error", "msg": "Missing query"}), 400
    site = normalize(q)
    rows = db_op("SELECT bin FROM sites WHERE site=?", (site,), fetch=True)
    if rows:
        return jsonify({
            "status": "Found", 
            "site": site, 
            "bins": list(set([r["bin"] for r in rows]))
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
    <title>Nano Core | SaaS</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: #050505; color: #fff; }
        .glass { background: rgba(15, 15, 15, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.08); }
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
        <div class="w-full max-w-[400px] p-10 glass rounded-[2.5rem] shadow-2xl text-center">
            <div class="inline-flex p-4 bg-white/5 border border-white/10 rounded-2xl mb-6">
                <i data-lucide="shield-check" class="text-blue-500 w-8 h-8"></i>
            </div>
            <h1 class="text-2xl font-bold mb-10">Nano Core Login</h1>
            <input type="password" id="auth-key" placeholder="Access Key" class="w-full input-saas p-4 rounded-2xl text-center mb-4">
            <button onclick="attemptLogin()" class="w-full bg-white text-black font-bold py-4 rounded-2xl text-xs uppercase tracking-widest">Initialize</button>
        </div>
    </div>

    <div id="app-interface" class="min-h-screen flex flex-col">
        <nav class="h-16 border-b border-white/5 px-8 flex items-center justify-between sticky top-0 bg-[#050505]/90 backdrop-blur-xl z-30">
            <div class="flex items-center gap-2"><i data-lucide="zap" class="text-blue-500"></i><span class="font-bold">NANO CORE</span></div>
            <div class="flex gap-4">
                <button onclick="nuclearClear()" class="text-xs text-orange-400 font-semibold px-3 py-1 rounded-lg border border-orange-400/20">WIPE ALL</button>
                <button onclick="location.reload()" class="text-xs text-red-500 font-bold px-3 py-1">EXIT</button>
            </div>
        </nav>

        <div class="flex flex-col lg:flex-row flex-1">
            <aside class="w-full lg:w-80 border-r border-white/5 p-8 space-y-8 bg-[#080808]">
                <div>
                    <label class="text-[10px] font-bold text-slate-500 uppercase mb-3 block">Live Search</label>
                    <input id="search-input" oninput="filterTable()" placeholder="Start typing..." class="w-full input-saas p-3 rounded-xl text-xs">
                </div>
                <div>
                    <label class="text-[10px] font-bold text-slate-500 uppercase mb-3 block">Add Entry</label>
                    <div class="space-y-3">
                        <input id="as" placeholder="Domain" class="w-full input-saas p-3.5 rounded-xl text-xs">
                        <input id="ab" placeholder="BIN ID" class="w-full input-saas p-3.5 rounded-xl text-xs font-mono">
                        <button onclick="addSite()" class="w-full bg-blue-600 font-bold py-3.5 rounded-xl text-[11px]">COMMIT</button>
                    </div>
                </div>
                <div class="pt-8 border-t border-white/5 grid grid-cols-2 gap-2">
                    <button onclick="exportData()" class="bg-white/5 border border-white/10 py-3 rounded-xl text-[10px]">EXPORT</button>
                    <button onclick="document.getElementById('importFile').click()" class="bg-white/5 border border-white/10 py-3 rounded-xl text-[10px]">IMPORT</button>
                    <input type="file" id="importFile" class="hidden" onchange="importData(event)">
                </div>
            </aside>

            <main class="flex-1 p-6 lg:p-12 overflow-y-auto">
                <div class="max-w-4xl mx-auto">
                    <div class="flex justify-between items-end mb-8">
                        <h2 class="text-2xl font-bold">Active Registry</h2>
                        <span id="record-count" class="text-[10px] font-bold text-blue-500 tracking-widest bg-blue-500/10 px-3 py-1 rounded-full">0 RECORDS</span>
                    </div>
                    <div class="glass rounded-3xl overflow-hidden shadow-2xl">
                        <table class="w-full text-left">
                            <thead class="bg-white/5 text-[10px] text-slate-500 uppercase font-bold"><th class="px-8 py-4">Endpoint</th><th class="px-8 py-4">BIN ID</th><th class="px-8 py-4 text-right">Action</th></thead>
                            <tbody id="db-body" class="text-xs divide-y divide-white/5"></tbody>
                        </table>
                        <div id="empty-state" class="py-20 text-center text-slate-600">No matching records.</div>
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
            div.className = 'toast-glass p-4 rounded-2xl flex items-center gap-3 min-w-[250px] animate-toast pointer-events-auto';
            div.innerHTML = `<i data-lucide="${type==='success'?'check-circle':'alert-circle'}" class="w-4 h-4 ${type==='success'?'text-green-400':'text-red-400'}"></i><span class="text-xs font-semibold">${msg}</span>`;
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
                toast('Auth Success');
                loadData();
            } else toast('Invalid Key', 'error');
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
            const bin = document.getElementById('ab').value;
            if(!site || !bin) return toast('Fill all fields', 'error');
            const res = await fetch('/api/admin/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({site, bin})
            });
            if(res.ok) {
                renderRow(site, bin);
                document.getElementById('as').value = '';
                document.getElementById('ab').value = '';
                toast('Record Added');
                updateCount();
            }
        }

        function renderRow(site, bin) {
            const row = document.createElement('tr');
            row.className = "hover:bg-white/[0.02] transition-colors";
            row.innerHTML = `<td class="px-8 py-5 text-white font-medium">${site}</td><td class="px-8 py-5 text-slate-400 font-mono">${bin}</td><td class="px-8 py-5 text-right"><button onclick="removeRow(this, '${site}', '${bin}')" class="text-slate-600 hover:text-red-500"><i data-lucide="trash-2" class="w-4 h-4"></i></button></td>`;
            document.getElementById('db-body').prepend(row);
            lucide.createIcons();
        }

        async function removeRow(btn, site, bin) {
            if(!confirm("Delete?")) return;
            const res = await fetch('/api/admin/remove', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({site, bin})
            });
            if(res.ok) { btn.closest('tr').remove(); updateCount(); toast('Deleted', 'error'); }
        }

        async function nuclearClear() {
            if(!confirm("WIPE EVERYTHING?")) return;
            const res = await fetch('/api/admin/clear_all', { method: 'POST' });
            if(res.ok) { document.getElementById('db-body').innerHTML = ""; updateCount(); toast('Database Purged', 'error'); }
        }

        function filterTable() {
            const q = document.getElementById('search-input').value.toLowerCase();
            const rows = document.querySelectorAll('#db-body tr');
            let match = 0;
            rows.forEach(r => {
                const visible = r.innerText.toLowerCase().includes(q);
                r.classList.toggle('row-hidden', !visible);
                if(visible) match++;
            });
            document.getElementById('empty-state').classList.toggle('hidden', match > 0);
            document.getElementById('record-count').innerText = match + " MATCHES";
        }

        function updateCount() {
            const count = document.querySelectorAll('#db-body tr').length;
            document.getElementById('record-count').innerText = count + " RECORDS";
            document.getElementById('empty-state').classList.toggle('hidden', count > 0);
        }

        function exportData() {
            const data = Array.from(document.querySelectorAll('#db-body tr')).map(r => ({
                site: r.cells[0].innerText, bin: r.cells[1].innerText
            }));
            const a = document.createElement('a');
            a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'}));
            a.download = 'nano_export.json';
            a.click();
            toast('Export Ready');
        }

        function importData(e) {
            const reader = new FileReader();
            reader.onload = async (event) => {
                const data = JSON.parse(event.target.result);
                for(const item of data) {
                    await fetch('/api/admin/add', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(item)
                    });
                }
                loadData();
                toast('Import Done');
            };
            reader.readAsText(e.target.files[0]);
        }
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    app.run(debug=True, port=5000)
