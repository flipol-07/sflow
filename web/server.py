import threading
import os
from flask import Flask, jsonify, render_template_string, send_from_directory
from db.database import TranscriptionDB
from config import DB_PATH

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Howl - Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: { sans: ['Inter', 'sans-serif'] },
                    colors: {
                        dark: '#030303',
                        panel: 'rgba(20, 20, 20, 0.65)',
                        accent: '#E0E0E0'
                    },
                    animation: {
                        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                        'blob': 'blob 7s infinite',
                    },
                    keyframes: {
                        blob: {
                            '0%': { transform: 'translate(0px, 0px) scale(1)' },
                            '33%': { transform: 'translate(30px, -50px) scale(1.1)' },
                            '66%': { transform: 'translate(-20px, 20px) scale(0.9)' },
                            '100%': { transform: 'translate(0px, 0px) scale(1)' },
                        }
                    }
                }
            }
        }
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        body { 
            background-color: #000;
            color: #E2E8F0;
            overflow-y: scroll;
        }

        /* Animated Mesh Background */
        .bg-mesh {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            z-index: -1;
            background: radial-gradient(circle at 15% 50%, rgba(30, 30, 30, 0.4), transparent 25%),
                        radial-gradient(circle at 85% 30%, rgba(15, 15, 25, 0.5), transparent 25%);
            background-color: #050505;
        }

        .glass-panel { 
            background: rgba(15, 15, 15, 0.4); 
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 1px solid rgba(255, 255, 255, 0.05); 
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
        }

        .row-hover {
            transition: all 0.2s ease;
            position: relative;
        }
        
        .row-hover::before {
            content: '';
            position: absolute;
            inset: 0;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.02), transparent);
            opacity: 0;
            transition: opacity 0.2s ease;
            pointer-events: none;
        }

        .row-hover:hover { 
            background: rgba(255,255,255,0.02); 
            border-color: rgba(255, 255, 255, 0.1);
            transform: translateX(2px);
        }
        
        .row-hover:hover::before { opacity: 1; }

        .text-preview { 
            max-height: 2.8em; 
            overflow: hidden; 
            transition: max-height 0.4s cubic-bezier(0.16, 1, 0.3, 1); 
            line-height: 1.4;
            display: -webkit-box;
            -webkit-box-orient: vertical;
            -webkit-line-clamp: 2;
        }
        
        .text-preview.expanded { 
            max-height: 800px; 
            -webkit-line-clamp: unset;
        }

        .btn-copy {
            transition: all 0.2s;
            opacity: 0.3;
        }
        
        .row-hover:hover .btn-copy { opacity: 1; }
        
        .btn-copy:hover {
            background: rgba(255,255,255,0.1);
            color: #fff;
            transform: scale(1.05);
        }

        .copied-toast {
            position: fixed; top: 20px; right: 20px;
            background: rgba(40, 40, 40, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            color: white; padding: 12px 24px;
            border-radius: 8px; font-weight: 500; font-size: 14px;
            transform: translateY(-100px); opacity: 0;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            z-index: 50;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        .copied-toast.show { transform: translateY(0); opacity: 1; }

        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; border: 2px solid #050505; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
        
        .search-input {
            transition: all 0.3s ease;
        }
        .search-input:focus {
            background: rgba(255,255,255,0.05);
            width: 280px;
        }
    </style>
</head>
<body class="antialiased selection:bg-white/20 selection:text-white pb-20">
    <div class="bg-mesh"></div>
    
    <!-- Toast -->
    <div id="toast" class="copied-toast flex items-center gap-2">
        <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
        Copiado al portapapeles
    </div>

    <div class="max-w-5xl mx-auto px-6 pt-16">
        <!-- Header -->
        <header class="flex flex-col md:flex-row items-start md:items-center justify-between mb-12 gap-6 relative z-10">
            <div class="flex items-center gap-4">
                <div class="relative group">
                    <div class="absolute -inset-1 bg-white/20 rounded-full blur opacity-0 group-hover:opacity-100 transition duration-500"></div>
                    <img src="/logo_small.png" alt="Howl Logo" class="relative w-12 h-12 rounded-full bg-white/5 border border-white/10 p-2 object-contain shadow-xl">
                </div>
                <div>
                    <h1 class="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
                        Howl <span class="bg-white/10 border border-white/5 text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full text-white/60 font-medium">Dashboard</span>
                    </h1>
                    <p class="text-sm text-white/40 mt-1 flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                        Transcribiendo y refinando en local
                    </p>
                </div>
            </div>
            
            <div class="flex items-center gap-3 bg-black/40 p-1.5 rounded-xl border border-white/5 backdrop-blur-md">
                <div class="relative">
                    <svg class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-white/30" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                    <input type="text" id="search" placeholder="Buscar ideas, código, texto..."
                        class="search-input bg-transparent border-none rounded-lg pl-9 pr-4 py-2 text-sm text-white/90
                        placeholder-white/30 focus:outline-none focus:ring-0 w-48 md:w-64">
                </div>
            </div>
        </header>

        <!-- Stats row (Optional but looks cool) -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div class="glass-panel rounded-xl p-4 flex flex-col justify-center">
                <span class="text-xs text-white/40 uppercase tracking-wider font-semibold mb-1">Total Registros</span>
                <span class="text-2xl font-bold text-white" id="stat-total">-</span>
            </div>
            <div class="glass-panel rounded-xl p-4 flex flex-col justify-center">
                <span class="text-xs text-white/40 uppercase tracking-wider font-semibold mb-1">Última Actividad</span>
                <span class="text-sm font-medium text-white/80" id="stat-last">Buscando...</span>
            </div>
        </div>

        <!-- Main List -->
        <main class="glass-panel rounded-2xl overflow-hidden shadow-2xl ring-1 ring-white/5 relative z-10">
            <div id="empty" class="hidden flex-col items-center justify-center py-24 text-center">
                <div class="w-16 h-16 bg-white/5 rounded-2xl flex items-center justify-center mb-4 border border-white/5">
                    <svg class="w-8 h-8 text-white/20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"></path></svg>
                </div>
                <h3 class="text-lg font-medium text-white/80">Sin transcripciones</h3>
                <p class="text-sm text-white/40 mt-1 max-w-sm">Presiona Ctrl+Shift (mantener) o doble Ctrl para empezar a dictar text.</p>
            </div>
            
            <div id="list-container" class="divide-y divide-white/5">
                <!-- Rows injected here -->
            </div>
        </main>
    </div>

    <script>
        let allData = [];

        async function loadData() {
            try {
                const res = await fetch('/api/transcriptions');
                allData = await res.json();
                renderList(allData);
                updateStats(allData);
            } catch (e) {
                console.error("Error fetching data:", e);
            }
        }

        function updateStats(data) {
            document.getElementById('stat-total').textContent = data.length;
            if (data.length > 0) {
                const last = new Date(data[0].created_at + 'Z');
                document.getElementById('stat-last').textContent = last.toLocaleTimeString('es-MX', {hour: '2-digit', minute:'2-digit'});
            } else {
                document.getElementById('stat-last').textContent = 'Ninguna';
            }
        }

        function renderList(data) {
            const container = document.getElementById('list-container');
            const empty = document.getElementById('empty');

            if (data.length === 0) {
                container.innerHTML = '';
                empty.classList.remove('hidden');
                empty.classList.add('flex');
                return;
            }
            empty.classList.add('hidden');
            empty.classList.remove('flex');

            container.innerHTML = data.map((t, i) => {
                const date = new Date(t.created_at + 'Z');
                const isToday = date.toDateString() === new Date().toDateString();
                const dayStr = isToday ? 'Hoy' : date.toLocaleDateString('es-MX', {month: 'short', day: 'numeric'});
                const timeStr = date.toLocaleTimeString('es-MX', {hour: '2-digit', minute: '2-digit'});
                const dur = t.duration_seconds ? t.duration_seconds.toFixed(1) + 's' : '';
                
                return `
                <div class="row-hover p-5 cursor-pointer flex gap-4 md:gap-6 items-start group" onclick="toggleExpand('text-${i}')">
                    <div class="shrink-0 pt-1 text-right w-16">
                        <div class="text-sm font-medium text-white/60">${timeStr}</div>
                        <div class="text-[10px] uppercase font-bold tracking-widest text-white/30 mt-0.5">${dayStr}</div>
                    </div>
                    
                    <div class="flex-grow min-w-0">
                        <div class="text-preview text-[15px] font-medium text-white/80" id="text-${i}">
                            ${escapeHtml(t.text)}
                        </div>
                        <div class="mt-2 flex items-center gap-3">
                            ${dur ? `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-white/5 text-[11px] font-medium text-white/40 border border-white/5"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg> ${dur}</span>` : ''}
                        </div>
                    </div>
                    
                    <div class="shrink-0 flex flex-col items-center gap-2">
                        <button onclick="event.stopPropagation(); copyText(${i}, this)"
                            class="btn-copy text-white/60 p-2 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center shadow-sm"
                            title="Copiar texto">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                        </button>
                    </div>
                </div>`;
            }).join('');
        }

        function toggleExpand(id) {
            const preview = document.getElementById(id);
            if(preview) preview.classList.toggle('expanded');
        }

        function copyText(index, btn) {
            navigator.clipboard.writeText(allData[index].text);
            const toast = document.getElementById('toast');
            toast.classList.add('show');
            
            // Visual feedback on button
            const originalHtml = btn.innerHTML;
            btn.innerHTML = `<svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>`;
            btn.classList.add('bg-emerald-500/20', 'border-emerald-500/30', 'text-emerald-300');
            
            setTimeout(() => { 
                toast.classList.remove('show'); 
                btn.innerHTML = originalHtml;
                btn.classList.remove('bg-emerald-500/20', 'border-emerald-500/30', 'text-emerald-300');
            }, 2000);
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML.replace(/\\n/g, '<br/>');
        }

        // Search logic with simple debounce
        let searchTimeout;
        document.getElementById('search').addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const q = e.target.value.toLowerCase();
                if (!q) { renderList(allData); updateStats(allData); return; }
                const filtered = allData.filter(t => t.text.toLowerCase().includes(q));
                renderList(filtered);
                updateStats(filtered);
            }, 300);
        });

        // Initialize and setup polling
        loadData();
        setInterval(() => {
            // Only auto-refresh if not searching to prevent disrupting user view
            if (!document.getElementById('search').value) {
                loadData();
            }
        }, 5000);
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/transcriptions")
def get_transcriptions():
    db = TranscriptionDB()
    return jsonify(db.get_recent(limit=200))

@app.route("/logo_small.png")
def logo():
    root_dir = os.path.dirname(os.path.dirname(__file__))
    return send_from_directory(root_dir, "logo_small.png")


def start_web_server(port: int = 5000):
    """Start Flask in a daemon thread so it doesn't block the Qt event loop."""
    thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    thread.start()
    return port
