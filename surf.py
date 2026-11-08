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

# --- Configuração do Servidor Web ---
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
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, token TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS estatisticas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, user_id TEXT, user_name TEXT, guild_id TEXT, detalhe TEXT, data TEXT)''')
    cursor.execute("SELECT * FROM users WHERE username = 'surf157'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password_hash, token) VALUES (?, ?, ?)", ('surf157', generate_password_hash('surf'), 'ADMIN-MASTER-TOKEN'))
    conn.commit()
    conn.close()

setup_database()

# --- HTMLs ---
HTML_LANDING = """<!DOCTYPE html><html><head><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-[#0a0a0a] text-white text-center p-20"><h1 class="text-5xl font-bold text-red-600">Surf Trama</h1><br><a href="/login" class="bg-red-700 px-6 py-2 rounded">Entrar</a></body></html>"""

HTML_LOGIN = """<!DOCTYPE html><html><head><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-[#0a0a0a] text-white flex justify-center items-center h-screen"><form method="POST" class="bg-[#171717] p-8 rounded w-96"><h1 class="text-2xl mb-4">Login</h1>{% if error %}<p class="text-red-500">{{ error }}</p>{% endif %}<input name="username" placeholder="Usuário" class="w-full p-2 mb-2 bg-black border border-gray-700 rounded"><input name="password" type="password" placeholder="Senha" class="w-full p-2 mb-4 bg-black border border-gray-700 rounded"><button class="bg-red-700 w-full p-2 rounded">Entrar</button><p class="mt-4 text-sm"><a href="/cadastro">Cadastrar</a></p></form></body></html>"""

HTML_CADASTRO = """<!DOCTYPE html><html><head><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-[#0a0a0a] text-white flex justify-center items-center h-screen"><form method="POST" class="bg-[#171717] p-8 rounded w-96"><h1 class="text-2xl mb-4">Cadastro</h1>{% if error %}<p class="text-red-500">{{ error }}</p>{% endif %}<input name="username" placeholder="Usuário" class="w-full p-2 mb-2 bg-black border border-gray-700 rounded"><input name="password" type="password" placeholder="Senha" class="w-full p-2 mb-4 bg-black border border-gray-700 rounded"><button class="bg-red-700 w-full p-2 rounded">Criar Conta</button><p class="mt-4 text-sm"><a href="/login">Voltar</a></p></form></body></html>"""

HTML_VENDAS = """<!DOCTYPE html><html><head><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-[#0a0a0a] text-white text-center p-20"><h1 class="text-4xl text-red-600">Acesso Bloqueado</h1><p>Compre um token para acessar.</p><a href="/comprar" class="bg-green-600 px-6 py-2 rounded inline-block mt-4">Comprar</a><br><form method="POST" action="/validar_token" class="mt-4"><input name="token" placeholder="Token" class="p-2 bg-black border border-gray-700 rounded"><button class="bg-red-700 p-2 rounded">Ativar</button></form></body></html>"""

HTML_DASHBOARD = """<!DOCTYPE html><html><head><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-[#0a0a0a] text-white p-10"><div class="max-w-6xl mx-auto"><h1 class="text-2xl mb-4">Dashboard</h1><div class="grid grid-cols-4 gap-4 mb-10"><div class="bg-[#171717] p-4 rounded"><h2>Servidores</h2><p class="text-3xl">{{ guilds|length }}</p></div><div class="bg-[#171717] p-4 rounded"><h2>Tickets</h2><p class="text-3xl">{{ total_tickets }}</p></div><div class="bg-[#171717] p-4 rounded"><h2>Vendas</h2><p class="text-3xl">{{ total_vendas }}</p></div><div class="bg-[#171717] p-4 rounded"><h2>Pagamentos</h2><p class="text-3xl">{{ total_pagamentos }}</p></div></div><h2 class="text-xl mb-2">Atividades Recentes</h2><table class="w-full text-left bg-[#171717] rounded"><tr class="border-b border-gray-700"><th class="p-2">Tipo</th><th class="p-2">Usuário</th><th class="p-2">Detalhe</th><th class="p-2">Data</th></tr>{% for log in logs %}<tr class="border-b border-gray-700"><td class="p-2">{{ log.tipo }}</td><td class="p-2">{{ log.user_name }}</td><td class="p-2">{{ log.detalhe }}</td><td class="p-2">{{ log.data }}</td></tr>{% endfor %}</table><a href="/logout" class="text-red-500 mt-4 inline-block">Sair</a></div></body></html>"""

# --- Rotas ---
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
        username, password = request.form.get('username'), request.form.get('password')
        if username == 'surf157': return render_template_string(HTML_CADASTRO, error="Nome reservado.")
        conn = sqlite3.connect('tickets.db'); cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password_hash, token) VALUES (?, ?, ?)", (username, generate_password_hash(password), None))
            conn.commit(); conn.close(); return redirect(url_for('login'))
        except: conn.close(); return render_template_string(HTML_CADASTRO, error="Nome já existe.")
    return render_template_string(HTML_CADASTRO)

@app.route('/logout')
@login_required
def logout(): logout_user(); return redirect(url_for('landing'))

@app.route('/validar_token', methods=['POST'])
@login_required
def validar_token():
    token = request.form.get('token').upper()
    if token in CHAVES_VALIDAS:
        conn = sqlite3.connect('tickets.db'); cursor = conn.cursor()
        cursor.execute("UPDATE users SET token = ? WHERE id = ?", (token, current_user.id))
        conn.commit(); conn.close(); return redirect(url_for('dashboard'))
    return render_template_string(HTML_VENDAS, error="Token inválido.")

@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.token and not current_user.is_admin: return render_template_string(HTML_VENDAS)
    if not bot.is_ready(): return "Iniciando...", 200
    conn = sqlite3.connect('tickets.db'); cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM estatisticas WHERE tipo = 'Ticket'"); total_tickets = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM estatisticas WHERE tipo = 'Venda'"); total_vendas = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM estatisticas WHERE tipo = 'Pagamento'"); total_pagamentos = cursor.fetchone()[0] or 0
    cursor.execute("SELECT tipo, user_name, detalhe, data FROM estatisticas ORDER BY id DESC LIMIT 15"); logs = cursor.fetchall()
    guilds_data = [{"id": g.id, "name": g.name} for g in bot.guilds]
    conn.close()
    return render_template_string(HTML_DASHBOARD, guilds=guilds_data, total_tickets=total_tickets, total_vendas=total_vendas, total_pagamentos=total_pagamentos, logs=logs)

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
def keep_alive(): Thread(target=run_web).start()

# --- Bot ---
intents = discord.Intents.default(); intents.message_content = True; intents.members = True; intents.presences = True; intents.voice_states = True

class SurfTramaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents); self.COR_TRAMA = 0x8B0000
    async def setup_hook(self):
        try:
            for cog in ["moderacao", "suporte", "seguranca", "membros", "atendimento", "redes_sociais", "utilitarios", "automacao", "vip", "pagamentos", "musica"]:
                await self.load_extension(f"cogs.{cog}")
            print("✅ Módulos carregados.")
        except Exception as e: print(f"❌ ERRO: {e}")
        await self.tree.sync()

bot = SurfTramaBot()

@bot.event
async def on_ready():
    print(f'✅ Surf Trama online como {bot.user}')
    keep_alive()

@bot.tree.command(name="ajuda", description="Mostra o painel de ajuda.")
async def ajuda(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed(title="🌊 Ajuda", description="Use `/` para interagir.", color=bot.COR_TRAMA), ephemeral=True)

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN: bot.run(TOKEN)
