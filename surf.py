import discord
from discord import app_commands
from discord.ext import commands
import os
import sqlite3
import datetime
from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from threading import Thread

# --- Configuração do Servidor Web (Flask) ---
app = Flask(__name__)
app.secret_key = 'chave_super_secreta_surf_trama_2026'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

CHAVES_VALIDAS = ["TRAMA-2026-VIP1", "TRAMA-2026-VIP2", "TRAMA-2026-TESTE"]

class User(UserMixin):
    def __init__(self, id, username, token, is_admin=False):
        self.id = id
        self.username = username
        self.token = token
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, token FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        is_admin = (row[1] == 'surf157')
        return User(id=row[0], username=row[1], token=row[2], is_admin=is_admin)
    return None

def setup_database():
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, email TEXT UNIQUE, password_hash TEXT, token TEXT, created_at TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS estatisticas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, user_id TEXT, user_name TEXT, guild_id TEXT, detalhe TEXT, data TEXT)''')
    cursor.execute("SELECT * FROM users WHERE username = 'surf157'")
    if not cursor.fetchone():
        agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        cursor.execute("INSERT INTO users (username, email, password_hash, token, created_at) VALUES (?, ?, ?, ?, ?)", ('surf157', 'admin@trama.com', generate_password_hash('surf'), 'ADMIN-MASTER-TOKEN', agora))
    conn.commit()
    conn.close()

setup_database()

# --- ESTILOS GLOBAIS ---
GLOBAL_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    body { background-color: #050505; color: #e5e7eb; margin: 0; overflow-x: hidden; display: flex; min-height: 100vh; }
    
    .bg-blobs { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -1; overflow: hidden; pointer-events: none; }
    .blob { position: absolute; border-radius: 50%; filter: blur(90px); opacity: 0.35; animation: move 25s infinite alternate; }
    .blob-1 { width: 500px; height: 500px; background: #8B0000; top: -150px; left: -150px; }
    .blob-2 { width: 400px; height: 400px; background: #ff3333; bottom: -100px; right: -100px; animation-delay: -5s; }
    .blob-3 { width: 300px; height: 300px; background: #4a0000; top: 40%; left: 40%; animation-delay: -10s; }
    @keyframes move { 0% { transform: translate(0, 0) scale(1); } 100% { transform: translate(100px, 50px) scale(1.2); } }

    .glass { background: rgba(23, 23, 23, 0.7); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 16px; box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5); }
    .fade-up { animation: fadeUp 0.8s ease-out forwards; opacity: 0; transform: translateY(20px); }
    @keyframes fadeUp { to { opacity: 1; transform: translateY(0); } }
    
    .btn-primary { background: linear-gradient(135deg, #8B0000, #ff3333); color: white; padding: 12px 24px; border-radius: 10px; font-weight: 600; transition: 0.3s; border: none; cursor: pointer; text-decoration: none; display: inline-block; text-align: center; }
    .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(139, 0, 0, 0.4); }

    .marquee-container { overflow: hidden; white-space: nowrap; position: relative; width: 100%; mask-image: linear-gradient(to right, transparent, black 10%, black 90%, transparent); }
    .marquee-content { display: inline-flex; gap: 20px; animation: marquee 30s linear infinite; }
    .marquee-content:hover { animation-play-state: paused; }
    @keyframes marquee { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
    .review-card { display: inline-block; white-space: normal; width: 320px; flex-shrink: 0; text-align: left; }

    /* Sidebar */
    .sidebar { width: 260px; background: rgba(10, 10, 10, 0.8); border-right: 1px solid rgba(255,255,255,0.05); display: flex; flex-direction: column; padding: 20px; backdrop-filter: blur(10px); }
    .sidebar-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-radius: 10px; color: #a3a3a3; font-weight: 500; cursor: pointer; transition: 0.2s; margin-bottom: 5px; text-decoration: none; }
    .sidebar-item:hover { background: rgba(255,255,255,0.05); color: white; }
    .sidebar-item.active { background: rgba(139, 0, 0, 0.2); color: #ff3333; border-left: 3px solid #ff3333; }
    
    .tab-content { display: none; animation: fadeUp 0.4s ease-out; }
    .tab-content.active { display: block; }
    
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th { text-align: left; padding: 12px; color: #888; font-size: 12px; text-transform: uppercase; border-bottom: 1px solid rgba(255,255,255,0.1); }
    td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 14px; }
    tr:hover td { background: rgba(255,255,255,0.02); }
</style>
"""

# --- HTML: LANDING PAGE (VITRINE COMPLETA) ---
HTML_LANDING = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Surf Trama | O Melhor Bot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    {GLOBAL_STYLE}
</head>
<body class="block p-0">
    <div class="bg-blobs"><div class="blob blob-1"></div><div class="blob blob-2"></div><div class="blob blob-3"></div></div>

    <nav class="flex justify-between items-center p-6 max-w-7xl mx-auto fade-up">
        <div class="flex items-center gap-3"><div class="w-10 h-10 rounded-xl bg-gradient-to-br from-red-700 to-red-500 flex items-center justify-center font-bold text-white text-xl">T</div><span class="text-2xl font-extrabold text-white">Surf Trama</span></div>
        <div class="flex items-center gap-4"><a href="/login" class="text-gray-300 hover:text-white font-semibold transition">Entrar</a><a href="/cadastro" class="btn-primary text-sm">Criar Conta</a></div>
    </nav>

    <header class="text-center py-24 px-6 max-w-4xl mx-auto fade-up" style="animation-delay: 0.1s;">
        <h1 class="text-5xl md:text-7xl font-extrabold mb-6 leading-tight tracking-tight text-white">Domine seu servidor com <span class="text-transparent bg-clip-text bg-gradient-to-r from-red-500 to-red-800">inteligência</span>.</h1>
        <p class="text-gray-400 text-lg md:text-xl mb-10 max-w-2xl mx-auto">Moderação impecável, engajamento automatizado, vendas integradas e uma dashboard linda. Tudo em um único bot.</p>
        <a href="/cadastro" class="btn-primary text-lg px-10 py-4">Começar Agora</a>
    </header>

    <section class="py-20 px-6 max-w-7xl mx-auto fade-up" style="animation-delay: 0.3s;">
        <h2 class="text-3xl font-bold text-center mb-12 text-white">Tudo o que você precisa em um só lugar</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div class="glass p-6"><div class="text-4xl mb-4">🛡️</div><h3 class="text-xl font-bold text-white mb-2">Moderação</h3><p class="text-sm text-gray-400">Anti-raid, anti-link, warns e bans automáticos.</p></div>
            <div class="glass p-6"><div class="text-4xl mb-4">🎫</div><h3 class="text-xl font-bold text-white mb-2">Tickets</h3><p class="text-sm text-gray-400">Atendimento profissional com menus suspensos.</p></div>
            <div class="glass p-6"><div class="text-4xl mb-4">💎</div><h3 class="text-xl font-bold text-white mb-2">Vendas VIP</h3><p class="text-sm text-gray-400">Integração Pix (SyncPay) e cargos automáticos.</p></div>
            <div class="glass p-6"><div class="text-4xl mb-4">👥</div><h3 class="text-xl font-bold text-white mb-2">Membros</h3><p class="text-sm text-gray-400">Boas-vindas e cargos por reação.</p></div>
            <div class="glass p-6"><div class="text-4xl mb-4">⚙️</div><h3 class="text-xl font-bold text-white mb-2">Automação</h3><p class="text-sm text-gray-400">Gatilhos e sorteios interativos.</p></div>
            <div class="glass p-6"><div class="text-4xl mb-4">🎵</div><h3 class="text-xl font-bold text-white mb-2">Música</h3><p class="text-sm text-gray-400">Toque músicas do YouTube e Spotify.</p></div>
        </div>
    </section>

    <section class="py-20 overflow-hidden fade-up" style="animation-delay: 0.5s;">
        <h2 class="text-3xl font-bold text-center mb-12 text-white">O que dizem sobre nós</h2>
        <div class="marquee-container"><div class="marquee-content">
            <div class="review-card glass p-6"><div class="flex text-yellow-500 mb-2">★★★★★</div><p class="text-gray-300 text-sm mb-4">"O melhor bot que já usei."</p><p class="text-white text-sm font-bold">- dono_server</p></div>
            <div class="review-card glass p-6"><div class="flex text-yellow-500 mb-2">★★★★★</div><p class="text-gray-300 text-sm mb-4">"A dashboard é incrível."</p><p class="text-white text-sm font-bold">- maria_gamer</p></div>
            <div class="review-card glass p-6"><div class="flex text-yellow-500 mb-2">★★★★★</div><p class="text-gray-300 text-sm mb-4">"Os tickets são muito profissionais."</p><p class="text-white text-sm font-bold">- joao_trama</p></div>
            <div class="review-card glass p-6"><div class="flex text-yellow-500 mb-2">★★★★★</div><p class="text-gray-300 text-sm mb-4">"O melhor bot que já usei."</p><p class="text-white text-sm font-bold">- dono_server</p></div>
            <div class="review-card glass p-6"><div class="flex text-yellow-500 mb-2">★★★★★</div><p class="text-gray-300 text-sm mb-4">"A dashboard é incrível."</p><p class="text-white text-sm font-bold">- maria_gamer</p></div>
            <div class="review-card glass p-6"><div class="flex text-yellow-500 mb-2">★★★★★</div><p class="text-gray-300 text-sm mb-4">"Os tickets são muito profissionais."</p><p class="text-white text-sm font-bold">- joao_trama</p></div>
        </div></div>
    </section>
</body>
</html>
"""

# --- HTML: LOGIN, CADASTRO, VENDAS ---
HTML_LOGIN = f"""
<!DOCTYPE html><html lang="pt-BR"><head><title>Login</title><script src="https://cdn.tailwindcss.com"></script>{GLOBAL_STYLE}</head>
<body class="flex items-center justify-center h-screen"><div class="bg-blobs"><div class="blob blob-1"></div><div class="blob blob-2"></div></div>
<div class="glass p-10 w-[400px] fade-up"><h1 class="text-2xl font-bold text-white text-center mb-6">Entrar no Painel</h1>
{{% if error %}}<div class="bg-red-900/50 text-red-300 p-2 rounded mb-4 text-center">{{{{ error }}}}</div>{{% endif %}}
<form method="POST" action="/login"><div class="mb-4"><label class="text-xs text-gray-400 uppercase">Usuário</label><input type="text" name="username" class="w-full bg-black/50 border border-gray-700 rounded-xl p-3 text-white focus:border-red-500 outline-none" required></div><div class="mb-6"><label class="text-xs text-gray-400 uppercase">Senha</label><input type="password" name="password" class="w-full bg-black/50 border border-gray-700 rounded-xl p-3 text-white focus:border-red-500 outline-none" required></div><button type="submit" class="btn-primary w-full py-3">Entrar</button></form>
<p class="text-center text-sm text-gray-500 mt-4">Não tem conta? <a href="/cadastro" class="text-red-500">Criar Conta</a></p></div></body></html>"""

HTML_CADASTRO = f"""
<!DOCTYPE html><html lang="pt-BR"><head><title>Cadastro</title><script src="https://cdn.tailwindcss.com"></script>{GLOBAL_STYLE}</head>
<body class="flex items-center justify-center h-screen"><div class="bg-blobs"><div class="blob blob-1"></div><div class="blob blob-2"></div></div>
<div class="glass p-10 w-[400px] fade-up"><h1 class="text-2xl font-bold text-white text-center mb-6">Crie sua Conta</h1>
{{% if error %}}<div class="bg-red-900/50 text-red-300 p-2 rounded mb-4 text-center">{{{{ error }}}}</div>{{% endif %}}
<form method="POST" action="/cadastro"><div class="mb-4"><label class="text-xs text-gray-400 uppercase">Usuário</label><input type="text" name="username" class="w-full bg-black/50 border border-gray-700 rounded-xl p-3 text-white focus:border-red-500 outline-none" required></div><div class="mb-4"><label class="text-xs text-gray-400 uppercase">E-mail</label><input type="email" name="email" class="w-full bg-black/50 border border-gray-700 rounded-xl p-3 text-white focus:border-red-500 outline-none" required></div><div class="mb-6"><label class="text-xs text-gray-400 uppercase">Senha</label><input type="password" name="password" class="w-full bg-black/50 border border-gray-700 rounded-xl p-3 text-white focus:border-red-500 outline-none" required></div><button type="submit" class="btn-primary w-full py-3">Cadastrar</button></form>
<p class="text-center text-sm text-gray-500 mt-4">Já tem conta? <a href="/login" class="text-red-500">Fazer Login</a></p></div></body></html>"""

HTML_VENDAS = f"""
<!DOCTYPE html><html lang="pt-BR"><head><title>Acesso Bloqueado</title><script src="https://cdn.tailwindcss.com"></script>{GLOBAL_STYLE}</head>
<body class="flex items-center justify-center h-screen"><div class="bg-blobs"><div class="blob blob-1"></div></div>
<div class="glass p-10 w-[450px] text-center fade-up"><h1 class="text-3xl font-bold text-red-500 mb-4">Acesso Restrito</h1><p class="text-gray-400 mb-8">Você precisa de um Token de Licença válido para acessar a Dashboard.</p><a href="/comprar" class="btn-primary block w-full py-3 mb-6">Comprar Token de Acesso</a>
<form method="POST" action="/validar_token"><p class="text-xs text-gray-500 mb-2 uppercase">Já comprou? Ative aqui:</p><input type="text" name="token" placeholder="TRAMA-XXXX-XXXX" class="w-full bg-black/50 border border-gray-700 rounded-xl p-3 text-white text-center focus:border-red-500 outline-none mb-4 uppercase" required><button type="submit" class="w-full bg-gray-800 hover:bg-gray-700 text-white font-bold py-3 rounded-xl transition">Ativar Token</button></form>
<a href="/logout" class="block mt-6 text-sm text-gray-600 hover:text-white transition">Sair da Conta</a></div></body></html>"""

# --- HTML: DASHBOARD COM SIDEBAR E ABAS ---
HTML_DASHBOARD = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <title>Dashboard | Surf Trama</title>
    <script src="https://cdn.tailwindcss.com"></script>
    {GLOBAL_STYLE}
</head>
<body>
    <div class="bg-blobs"><div class="blob blob-1"></div><div class="blob blob-2"></div></div>
    
    <!-- Sidebar -->
    <aside class="sidebar fade-up">
        <div class="flex items-center gap-3 mb-10 px-2">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-red-700 to-red-500 flex items-center justify-center font-bold text-white text-xl">T</div>
            <span class="text-xl font-extrabold text-white">Surf Trama</span>
        </div>
        <nav class="flex-1">
            <p class="text-xs font-bold text-gray-600 mb-3 px-2 uppercase tracking-wider">Menu Principal</p>
            <div class="sidebar-item active" onclick="openTab('visao-geral', this)">📊 Visão Geral</div>
            <div class="sidebar-item" onclick="openTab('tickets', this)">🎫 Tickets</div>
            <div class="sidebar-item" onclick="openTab('vendas', this)">💎 Vendas VIP</div>
            <div class="sidebar-item" onclick="openTab('pagamentos', this)">💳 Pagamentos</div>
            {{% if current_user.is_admin %}}
            <p class="text-xs font-bold text-gray-600 mb-3 px-2 mt-6 uppercase tracking-wider">Administração</p>
            <div class="sidebar-item" onclick="openTab('usuarios', this)">👥 Usuários</div>
            <div class="sidebar-item" onclick="openTab('servidores', this)">📡 Servidores</div>
            {{% endif %}}
        </nav>
        <div class="mt-auto pt-6 border-t border-white/5">
            <div class="flex items-center gap-3 mb-4 px-2">
                <div class="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-xs">{{{{ current_user.username[0]|upper }}}}</div>
                <div><p class="text-sm font-bold text-white">{{{{ current_user.username }}}}</p><p class="text-xs text-gray-500">{{% if current_user.is_admin %}}Administrador{{% else %}}Cliente{{% endif %}}</p></div>
            </div>
            <a href="/logout" class="sidebar-item text-red-500 hover:text-red-400 hover:bg-red-900/20">🚪 Sair da Conta</a>
        </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto p-10">
        <!-- ABA: VISÃO GERAL -->
        <div id="visao-geral" class="tab-content active fade-up">
            <h1 class="text-3xl font-bold text-white mb-2">Visão Geral</h1>
            <p class="text-gray-400 mb-8">Resumo em tempo real do seu bot.</p>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                <div class="glass p-6 border-t-2 border-red-600"><p class="text-xs text-gray-400 uppercase mb-2">Servidores</p><p class="text-4xl font-extrabold text-white">{{{{ guilds|length }}}}</p></div>
                <div class="glass p-6 border-t-2 border-green-600"><p class="text-xs text-gray-400 uppercase mb-2">Tickets</p><p class="text-4xl font-extrabold text-green-500">{{{{ total_tickets }}}}</p></div>
                <div class="glass p-6 border-t-2 border-yellow-600"><p class="text-xs text-gray-400 uppercase mb-2">Cliques VIP</p><p class="text-4xl font-extrabold text-yellow-500">{{{{ total_vendas }}}}</p></div>
                <div class="glass p-6 border-t-2 border-blue-600"><p class="text-xs text-gray-400 uppercase mb-2">Pix Gerados</p><p class="text-4xl font-extrabold text-blue-500">{{{{ total_pagamentos }}}}</p></div>
            </div>
            <div class="glass p-6">
                <h3 class="text-lg font-bold text-white mb-4">Atividades Recentes</h3>
                <table><thead><tr><th>Tipo</th><th>Usuário</th><th>Detalhe</th><th>Data</th></tr></thead><tbody>
                    {{% for log in logs_recentes %}}<tr><td class="font-bold text-red-500">{{{{ log.tipo }}}}</td><td>{{{{ log.user_name }}}}</td><td>{{{{ log.detalhe }}}}</td><td class="text-gray-500">{{{{ log.data }}}}</td></tr>{{% endfor %}}
                </tbody></table>
            </div>
        </div>

        <!-- ABA: TICKETS -->
        <div id="tickets" class="tab-content">
            <h1 class="text-3xl font-bold text-white mb-2">Histórico de Tickets</h1>
            <div class="glass p-6"><table><thead><tr><th>Usuário</th><th>Assunto</th><th>Data</th></tr></thead><tbody>
                {{% for log in logs_tickets %}}<tr><td class="font-bold text-white">{{{{ log.user_name }}}}</td><td class="text-gray-400">{{{{ log.detalhe }}}}</td><td class="text-gray-500">{{{{ log.data }}}}</td></tr>{{% else %}}<tr><td colspan="3" class="text-center text-gray-500">Nenhum ticket registrado.</td></tr>{{% endfor %}}
            </tbody></table></div>
        </div>

        <!-- ABA: VENDAS -->
        <div id="vendas" class="tab-content">
            <h1 class="text-3xl font-bold text-white mb-2">Histórico de Vendas</h1>
            <div class="glass p-6"><table><thead><tr><th>Usuário</th><th>Ação</th><th>Data</th></tr></thead><tbody>
                {{% for log in logs_vendas %}}<tr><td class="font-bold text-white">{{{{ log.user_name }}}}</td><td class="text-yellow-500">{{{{ log.detalhe }}}}</td><td class="text-gray-500">{{{{ log.data }}}}</td></tr>{{% else %}}<tr><td colspan="3" class="text-center text-gray-500">Nenhuma venda registrada.</td></tr>{{% endfor %}}
            </tbody></table></div>
        </div>

        <!-- ABA: PAGAMENTOS -->
        <div id="pagamentos" class="tab-content">
            <h1 class="text-3xl font-bold text-white mb-2">Histórico de Pagamentos</h1>
            <div class="glass p-6"><table><thead><tr><th>Usuário</th><th>Detalhe</th><th>Data</th></tr></thead><tbody>
                {{% for log in logs_pagamentos %}}<tr><td class="font-bold text-white">{{{{ log.user_name }}}}</td><td class="text-blue-500">{{{{ log.detalhe }}}}</td><td class="text-gray-500">{{{{ log.data }}}}</td></tr>{{% else %}}<tr><td colspan="3" class="text-center text-gray-500">Nenhum pix gerado.</td></tr>{{% endfor %}}
            </tbody></table></div>
        </div>

        <!-- ABA: USUÁRIOS (SÓ ADMIN) -->
        {{% if current_user.is_admin %}}
        <div id="usuarios" class="tab-content">
            <h1 class="text-3xl font-bold text-white mb-2">Usuários Cadastrados</h1>
            <div class="glass p-6"><table><thead><tr><th>ID</th><th>Usuário</th><th>E-mail</th><th>Token</th><th>Data</th></tr></thead><tbody>
                {{% for u in users %}}<tr><td class="text-gray-500">{{{{ u[0] }}}}</td><td class="font-bold text-white">{{{{ u[1] }}}}</td><td class="text-gray-400">{{{{ u[2] }}}}</td><td class="text-green-500 font-mono text-xs">{{{{ u[4] or 'Nenhum' }}}}</td><td class="text-gray-500">{{{{ u[5] }}}}</td></tr>{{% endfor %}}
            </tbody></table></div>
        </div>
        <div id="servidores" class="tab-content">
            <h1 class="text-3xl font-bold text-white mb-2">Servidores Conectados</h1>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {{% for guild in guilds %}}<div class="glass p-4 flex items-center gap-4">{{% if guild.icon %}}<img src="{{{{ guild.icon }}}}" class="w-12 h-12 rounded-full">{{% else %}}<div class="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center text-xs">T</div>{{% endif %}}<div><h3 class="font-bold text-white text-md truncate w-40">{{{{ guild.name }}}}</h3><p class="text-xs text-gray-400">{{{{ guild.members }}}} membros</p></div></div>{{% endfor %}}
            </div>
        </div>
        {{% endif %}}
    </main>

    <script>
        function openTab(tabName, element) {{
            document.querySelectorAll('.tab-content').forEach(tab => {{ tab.classList.remove('active'); }});
            document.querySelectorAll('.sidebar-item').forEach(item => {{ item.classList.remove('active'); }});
            document.getElementById(tabName).classList.add('active');
            if(element) element.classList.add('active');
        }}
    </script>
</body>
</html>
"""

# --- ROTAS ---
@app.route('/')
def landing(): return render_template_string(HTML_LANDING)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username, password = request.form.get('username'), request.form.get('password')
        conn = sqlite3.connect('tickets.db'); cursor = conn.cursor()
        cursor.execute("SELECT id, username, password_hash, token FROM users WHERE username = ?", (username,))
        user_data = cursor.fetchone(); conn.close()
        if user_data and check_password_hash(user_data[2], password):
            login_user(User(id=user_data[0], username=user_data[1], token=user_data[3], is_admin=(user_data[1] == 'surf157')))
            return redirect(url_for('dashboard'))
        return render_template_string(HTML_LOGIN, error="Usuário ou senha incorretos.")
    return render_template_string(HTML_LOGIN)

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        username, email, password = request.form.get('username'), request.form.get('email'), request.form.get('password')
        if username == 'surf157': return render_template_string(HTML_CADASTRO, error="Nome reservado.")
        conn = sqlite3.connect('tickets.db'); cursor = conn.cursor()
        try:
            agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
            cursor.execute("INSERT INTO users (username, email, password_hash, token, created_at) VALUES (?, ?, ?, ?, ?)", (username, email, generate_password_hash(password), None, agora))
            conn.commit(); conn.close(); return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close(); return render_template_string(HTML_CADASTRO, error="Usuário ou E-mail já cadastrado.")
    return render_template_string(HTML_CADASTRO)

@app.route('/logout')
@login_required
def logout(): logout_user(); return redirect(url_for('landing'))

@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.token and not current_user.is_admin: return render_template_string(HTML_VENDAS)
    if not bot.is_ready(): return "Iniciando... Recarregue.", 200
    conn = sqlite3.connect('tickets.db'); cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM estatisticas WHERE tipo = 'Ticket'"); total_tickets = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM estatisticas WHERE tipo = 'Venda'"); total_vendas = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM estatisticas WHERE tipo = 'Pagamento'"); total_pagamentos = cursor.fetchone()[0] or 0
    cursor.execute("SELECT tipo, user_name, detalhe, data FROM estatisticas ORDER BY id DESC LIMIT 20"); logs_recentes = cursor.fetchall()
    cursor.execute("SELECT user_name, detalhe, data FROM estatisticas WHERE tipo = 'Ticket' ORDER BY id DESC"); logs_tickets = cursor.fetchall()
    cursor.execute("SELECT user_name, detalhe, data FROM estatisticas WHERE tipo = 'Venda' ORDER BY id DESC"); logs_vendas = cursor.fetchall()
    cursor.execute("SELECT user_name, detalhe, data FROM estatisticas WHERE tipo = 'Pagamento' ORDER BY id DESC"); logs_pagamentos = cursor.fetchall()
    users = []
    if current_user.is_admin:
        cursor.execute("SELECT id, username, email, password_hash, token, created_at FROM users ORDER BY id DESC")
        users = cursor.fetchall()
    guilds_data = [{"id": g.id, "name": g.name, "icon": g.icon.url if g.icon else None, "members": g.member_count} for g in bot.guilds]
    conn.close()
    return render_template_string(HTML_DASHBOARD, guilds=guilds_data, total_tickets=total_tickets, total_vendas=total_vendas, total_pagamentos=total_pagamentos, users=users, logs_recentes=logs_recentes, logs_tickets=logs_tickets, logs_vendas=logs_vendas, logs_pagamentos=logs_pagamentos)

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
def keep_alive(): Thread(target=run_web).start()

# --- Bot ---
intents = discord.Intents.default(); intents.message_content = True; intents.members = True; intents.presences = True; intents.voice_states = True
class SurfTramaBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix='!', intents
