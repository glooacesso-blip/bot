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

# --- TOKENS DE VENDA ---
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

# --- Configuração do Banco de Dados ---
def setup_database():
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, token TEXT)''')
    
    # TABELA DE ESTATÍSTICAS (NOVO)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estatisticas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT, 
            user_id TEXT, 
            user_name TEXT, 
            guild_id TEXT,
            detalhe TEXT,
            data TEXT
        )
    ''')
    
    cursor.execute("SELECT * FROM users WHERE username = 'surf157'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password_hash, token) VALUES (?, ?, ?)", ('surf157', generate_password_hash('surf'), 'ADMIN-MASTER-TOKEN'))
    conn.commit()
    conn.close()

setup_database()

# --- HTML: PÁGINA INICIAL (LANDING PAGE) ---
# (Mantido igual ao anterior, mas com link para o dashboard de estatísticas se for admin)
HTML_LANDING = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Surf Trama | O Melhor Bot para o seu Servidor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #0a0a0a; color: #e5e7eb; scroll-behavior: smooth; }
        .hero-bg { background: radial-gradient(circle at center, #1a0000 0%, #0a0a0a 100%); }
        .card { background-color: #171717; border: 1px solid #262626; border-radius: 12px; padding: 24px; transition: 0.3s; }
        .card:hover { border-color: #8B0000; transform: translateY(-5px); }
        .gradient-text { background: linear-gradient(to right, #ff3333, #8B0000); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    </style>
</head>
<body>
    <nav class="flex justify-between items-center p-6 border-b border-[#262626] bg-[#0a0a0a]/90 backdrop-blur sticky top-0 z-50">
        <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-red-700 flex items-center justify-center font-bold text-white">T</div>
            <span class="text-xl font-bold text-white">Surf Trama</span>
        </div>
        <div class="flex gap-4">
            <a href="/login" class="bg-red-700 hover:bg-red-600 text-white px-6 py-2 rounded-lg font-semibold transition">Entrar / Cadastrar</a>
        </div>
    </nav>

    <header class="hero-bg py-24 px-6 text-center border-b border-[#262626]">
        <h1 class="text-5xl font-extrabold mb-4">Domine seu servidor com o <br><span class="gradient-text">Surf Trama</span></h1>
        <p class="text-gray-400 text-lg max-w-2xl mx-auto mb-8">O bot definitivo de moderação, segurança, engajamento e vendas para a sua comunidade.</p>
        <a href="/login" class="bg-red-700 hover:bg-red-600 text-white px-8 py-3 rounded-lg font-bold text-lg transition shadow-lg shadow-red-900/50">Adicionar ao Discord</a>
    </header>
</body>
</html>
"""

# --- HTML: PÁGINA DE LOGIN ---
# (Mantido igual)
HTML_LOGIN = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Surf Trama | Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-[#0a0a0a] text-white flex items-center justify-center h-screen font-sans">
    <div class="bg-[#171717] p-8 rounded-xl border border-[#262626] w-96 shadow-2xl">
        <h1 class="text-3xl font-bold text-red-600 text-center mb-2">🌊 Surf Trama</h1>
        <p class="text-gray-400 text-sm text-center mb-6">Entre para gerenciar o bot.</p>
        {% if error %}
        <div class="bg-red-900/50 border border-red-500 text-red-300 p-2 rounded mb-4 text-sm text-center">{{ error }}</div>
        {% endif %}
        <form method="POST" action="/login">
            <div class="mb-4">
                <label class="block text-sm text-gray-400 mb-1">Usuário</label>
                <input type="text" name="username" class="w-full bg-[#0a0a0a] border border-[#333] rounded p-2 text-white focus:border-red-500 focus:outline-none" required>
            </div>
            <div class="mb-6">
                <label class="block text-sm text-gray-400 mb-1">Senha</label>
                <input type="password" name="password" class="w-full bg-[#0a0a0a] border border-[#333] rounded p-2 text-white focus:border-red-500 focus:outline-none" required>
            </div>
            <button type="submit" class="w-full bg-red-700 hover:bg-red-600 text-white font-bold py-2 rounded transition">Entrar</button>
        </form>
        <p class="text-center text-sm text-gray-500 mt-4">É cliente novo? <a href="/cadastro" class="text-red-500 hover:underline">Cadastre-se</a></p>
        <p class="text-center text-sm text-gray-500 mt-2"><a href="/" class="text-gray-400 hover:underline">Voltar para o início</a></p>
    </div>
</body>
</html>
"""

# --- HTML: PÁGINA DE CADASTRO ---
# (Mantido igual)
HTML_CADASTRO = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Surf Trama | Cadastro</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-[#0a0a0a] text-white flex items-center justify-center h-screen font-sans">
    <div class="bg-[#171717] p-8 rounded-xl border border-[#262626] w-96 shadow-2xl">
        <h1 class="text-3xl font-bold text-red-600 text-center mb-2">Criar Conta</h1>
        <p class="text-gray-400 text-sm text-center mb-6">Crie sua conta para inserir seu token.</p>
        {% if error %}
        <div class="bg-red-900/50 border border-red-500 text-red-300 p-2 rounded mb-4 text-sm text-center">{{ error }}</div>
        {% endif %}
        <form method="POST" action="/cadastro">
            <div class="mb-4">
                <label class="block text-sm text-gray-400 mb-1">Usuário</label>
                <input type="text" name="username" class="w-full bg-[#0a0a0a] border border-[#333] rounded p-2 text-white focus:border-red-500 focus:outline-none" required>
            </div>
            <div class="mb-6">
                <label class="block text-sm text-gray-400 mb-1">Senha</label>
                <input type="password" name="password" class="w-full bg-[#0a0a0a] border border-[#333] rounded p-2 text-white focus:border-red-500 focus:outline-none" required>
            </div>
            <button type="submit" class="w-full bg-red-700 hover:bg-red-600 text-white font-bold py-2 rounded transition">Criar Conta</button>
        </form>
        <p class="text-center text-sm text-gray-500 mt-4">Já tem conta? <a href="/login" class="text-red-500 hover:underline">Faça Login</a></p>
    </div>
</body>
</html>
"""

# --- HTML: PÁGINA DE VENDAS ---
# (Mantido igual)
HTML_VENDAS = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Surf Trama | Adquirir Acesso</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-[#0a0a0a] text-white flex items-center justify-center h-screen font-sans">
    <div class="bg-[#171717] p-10 rounded-xl border border-[#262626] w-[500px] text-center shadow-2xl">
        <h1 class="text-4xl font-bold text-red-600 mb-2">Acesso Bloqueado</h1>
        <p class="text-gray-400 mb-6">Você ainda não possui um Token de Licença ativo.</p>
        <div class="bg-[#0a0a0a] p-4 rounded-lg border border-[#333] mb-6">
            <h2 class="text-xl font-bold text-white mb-2">Adquira o Bot Agora</h2>
            <p class="text-sm text-gray-400 mb-4">Pague com Pix e receba seu token na hora.</p>
            <a href="/comprar" class="block w-full bg-green-600 hover:bg-green-500 text-white font-bold py-2 rounded transition">Comprar Token</a>
        </div>
        <form method="POST" action="/validar_token">
            <p class="text-sm text-gray-400 mb-2">Já comprou? Insira seu Token aqui:</p>
            <input type="text" name="token" placeholder="TRAMA-XXXX-XXXX" class="w-full bg-[#0a0a0a] border border-[#333] rounded p-2 text-white text-center focus:border-red-500 focus:outline-none mb-4 uppercase" required>
            <button type="submit" class="w-full bg-red-700 hover:bg-red-600 text-white font-bold py-2 rounded transition">Ativar Token</button>
        </form>
        <a href="/logout" class="block mt-4 text-sm text-gray-500 hover:text-white">Sair da Conta</a>
    </div>
</body>
</html>
"""

# --- HTML: DASHBOARD DE ESTATÍSTICAS ---
HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Surf Trama | Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #0a0a0a; color: #e5e7eb; }
        .card { background-color: #171717; border: 1px solid #262626; border-radius: 12px; padding: 20px; transition: 0.2s; }
        .card:hover { border-color: #8B0000; }
        .server-icon { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; border: 2px solid #262626; }
    </style>
</head>
<body class="p-8">
    <div class="max-w-6xl mx-auto">
        <div class="flex justify-between items-center mb-10 pb-6 border-b border-[#262626]">
            <div class="flex items-center gap-4">
                <div class="w-12 h-12 rounded-full bg-red-700 flex items-center justify-center font-bold text-white text-xl">T</div>
                <div>
                    <h1 class="text-2xl font-bold text-white">Surf Trama Dashboard</h1>
                    <p class="text-sm text-gray-400">Bem-vindo, {{ current_user.username }} {% if current_user.is_admin %}(Admin){% endif %}</p>
                </div>
            </div>
            <a href="/logout" class="bg-[#262626] hover:bg-red-900 text-white px-4 py-2 rounded-lg text-sm transition">Sair</a>
        </div>

        <!-- Cards de Estatísticas (Globais) -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
            <div class="card text-center">
                <p class="text-sm text-gray-400">👥 Total de Servidores</p>
                <p class="text-3xl font-bold text-white">{{ guilds|length }}</p>
            </div>
            <div class="card text-center">
                <p class="text-sm text-gray-400">🎫 Tickets Abertos</p>
                <p class="text-3xl font-bold text-green-500">{{ total_tickets }}</p>
            </div>
            <div class="card text-center">
                <p class="text-sm text-gray-400">💎 Cliques em Comprar</p>
                <p class="text-3xl font-bold text-yellow-500">{{ total_vendas }}</p>
            </div>
            <div class="card text-center">
                <p class="text-sm text-gray-400">💰 Pagamentos Gerados</p>
                <p class="text-3xl font-bold text-blue-500">{{ total_pagamentos }}</p>
            </div>
        </div>

        <!-- Lista de Servidores -->
        <h2 class="text-xl font-semibold text-white mb-4">📡 Seus Servidores</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-10">
            {% for guild in guilds %}
            <div class="card">
                <div class="flex items-center gap-4 mb-4">
                    {% if guild.icon %}
                        <img src="{{ guild.icon }}" class="server-icon">
                    {% else %}
                        <div class="server-icon bg-gray-700 flex items-center justify-center text-xs">TRAMA</div>
                    {% endif %}
                    <div>
                        <h3 class="font-bold text-white text-lg truncate w-40">{{ guild.name }}</h3>
                        <p class="text-xs text-gray-500">ID: {{ guild.id }}</p>
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div class="bg-[#0a0a0a] p-3 rounded-lg text-center border border-[#262626]">
                        <p class="text-xs text-gray-400">👥 Membros</p>
                        <p class="text-2xl font-bold text-white">{{ guild.members }}</p>
                    </div>
                    <div class="bg-[#0a0a0a] p-3 rounded-lg text-center border border-[#262626]">
                        <p class="text-xs text-gray-400">🎧 Em Call</p>
                        <p class="text-2xl font-bold text-green-500">{{ guild.in_call }}</p>
                    </div>
                </div>
            </div>
            {% else %}
            <div class="card text-center col-span-3">
                <p class="text-gray-400">O bot ainda não foi adicionado a nenhum servidor.</p>
            </div>
            {% endfor %}
        </div>

        <!-- Tabela de Atividades Recentes -->
        <h2 class="text-xl font-semibold text-white mb-4">📋 Atividades Recentes</h2>
        <div class="card overflow-x-auto">
            <table class="w-full text-left text-sm text-gray-400">
                <thead class="text-xs text-gray-300 uppercase bg-[#0a0a0a]">
                    <tr>
                        <th class="px-6 py-3">Tipo</th>
                        <th class="px-6 py-3">Usuário</th>
                        <th class="px-6 py-3">Detalhe</th>
                        <th class="px-6 py-3">Data</th>
                    </tr>
                </thead>
                <tbody>
                    {% for log in logs %}
                    <tr class="border-b border-[#262626] hover:bg-[#262626]">
                        <td class="px-6 py-4 font-bold 
                            {% if log.tipo == 'Ticket' %}text-green-500
                            {% elif log.tipo == 'Venda' %}text-yellow-500
                            {% elif log.tipo == 'Pagamento' %}text-blue-500
                            {% else %}text-gray-300{% endif %}">
                            {{ log.tipo }}
                        </td>
                        <td class="px-6 py-4">{{ log.user_name }}</td>
                        <td class="px-6 py-4">{{ log.detalhe }}</td>
                        <td class="px-6 py-4">{{ log.data }}</td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="4" class="px-6 py-4 text-center">Nenhuma atividade registrada ainda.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

# --- ROTAS DO SITE ---
@app.route('/')
def landing():
    return render_template_string(HTML_LANDING)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password_hash, token FROM users WHERE username = ?", (username,))
        user_data = cursor.fetchone()
        conn.close()
        if user_data and check_password_hash(user_data[2], password):
            user = User(id=user_data[0], username=user_data[1], token=user_data[3], is_admin=(user_data[1] == 'surf157'))
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            return render_template_string(HTML_LOGIN, error="Usuário ou senha incorretos.")
    return render_template_string(HTML_LOGIN)

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'surf157':
            return render_template_string(HTML_CADASTRO, error="Este nome de usuário é reservado.")
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password_hash, token) VALUES (?, ?, ?)", (username, generate_password_hash(password), None))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return render_template_string(HTML_CADASTRO, error="Este nome de usuário já existe.")
    return render_template_string(HTML_CADASTRO)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('landing'))

@app.route('/validar_token', methods=['POST'])
@login_required
def validar_token():
    token = request.form.get('token').upper()
    if token in CHAVES_VALIDAS:
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET token = ? WHERE id = ?", (token, current_user.id))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    else:
        return render_template_string(HTML_VENDAS, error="Token inválido ou já utilizado.")

@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.token and not current_user.is_admin:
        return render_template_string(HTML_VENDAS)
    if not bot.is_ready(): return "Iniciando bot... Recarregue em 10 segundos.", 200
    
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    
    # Servidores
    guilds_data = []
    for guild in bot.guilds:
        in_call = sum(1 for member in guild.members if member.voice and member.voice.channel)
        guilds_data.append({"id": guild.id, "name": guild.name, "icon": guild.icon.url if guild.icon else None, "members": guild.member_count, "in_call": in_call})
    guilds_data.sort(key=lambda x: x['members'], reverse=True)

    # Contadores de Estatísticas
    cursor.execute("SELECT COUNT(*) FROM estatisticas WHERE tipo = 'Ticket'")
    total_tickets = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM estatisticas WHERE tipo = 'Venda'")
    total_vendas = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM estatisticas WHERE tipo = 'Pagamento'")
    total_pagamentos = cursor.fetchone()[0] or 0

    # Logs Recentes (últimos 15)
    cursor.execute("SELECT tipo, user_name, detalhe, data FROM estatisticas ORDER BY id DESC LIMIT 15")
    logs = cursor.fetchall()
    conn.close()

    return render_template_string(HTML_DASHBOARD, 
        guilds=guilds_data, 
        total_tickets=total_tickets, 
        total_vendas=total_vendas, 
        total_pagamentos=total_pagamentos,
        logs=logs)

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- Configuração do Bot ---
# ... (Mesma configuração de intents e classes do surf.py anterior)
