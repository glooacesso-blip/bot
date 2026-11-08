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
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, token TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS estatisticas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, user_id TEXT, user_name TEXT, guild_id TEXT, detalhe TEXT, data TEXT)''')
    cursor.execute("SELECT * FROM users WHERE username = 'surf157'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password_hash, token) VALUES (?, ?, ?)", ('surf157', generate_password_hash('surf'), 'ADMIN-MASTER-TOKEN'))
    conn.commit()
    conn.close()

setup_database()

# --- ESTILOS E ANIMAÇÕES GLOBAIS ---
GLOBAL_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    * { font-family: 'Outfit', sans-serif; }
    
    body { 
        background-color: #050505; 
        color: #e5e7eb; 
        margin: 0; 
        overflow-x: hidden; 
    }

    /* Fundo Animado */
    .bg-blobs {
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -1; overflow: hidden;
    }
    .blob {
        position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.4;
        animation: move 20s infinite alternate;
    }
    .blob-1 { width: 400px; height: 400px; background: #8B0000; top: -100px; left: -100px; }
    .blob-2 { width: 300px; height: 300px; background: #ff3333; bottom: -50px; right: -50px; animation-delay: -5s; }
    .blob-3 { width: 200px; height: 200px; background: #4a0000; top: 40%; left: 40%; animation-delay: -10s; }

    @keyframes move {
        0% { transform: translate(0, 0) scale(1); }
        100% { transform: translate(100px, 50px) scale(1.2); }
    }

    /* Glassmorphism */
    .glass {
        background: rgba(23, 23, 23, 0.6);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
    }

    /* Animações de Entrada */
    .fade-up {
        animation: fadeUp 0.8s ease-out forwards;
        opacity: 0; transform: translateY(20px);
    }
    @keyframes fadeUp {
        to { opacity: 1; transform: translateY(0); }
    }

    /* Botões */
    .btn-primary {
        background: linear-gradient(135deg, #8B0000, #ff3333);
        color: white; padding: 12px 24px; border-radius: 10px; font-weight: 600;
        transition: all 0.3s ease; border: none; cursor: pointer;
    }
    .btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(139, 0, 0, 0.4);
    }
</style>
"""

# --- HTML: LANDING PAGE ---
HTML_LANDING = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Surf Trama | O Futuro do seu Servidor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    {GLOBAL_STYLE}
</head>
<body>
    <div class="bg-blobs"><div class="blob blob-1"></div><div class="blob blob-2"></div><div class="blob blob-3"></div></div>

    <nav class="flex justify-between items-center p-6 max-w-7xl mx-auto fade-up">
        <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-red-700 to-red-500 flex items-center justify-center font-bold text-white text-xl shadow-lg shadow-red-900/50">T</div>
            <span class="text-2xl font-extrabold tracking-tight text-white">Surf Trama</span>
        </div>
        <a href="/login" class="btn-primary text-sm">Acessar Painel</a>
    </nav>

    <header class="text-center py-32 px-6 max-w-4xl mx-auto fade-up" style="animation-delay: 0.2s;">
        <div class="inline-block glass px-4 py-1 rounded-full text-xs font-semibold text-red-400 mb-6 border-red-900/30">
            ✨ A nova era da gestão no Discord
        </div>
        <h1 class="text-6xl md:text-7xl font-extrabold mb-6 leading-tight tracking-tight">
            Domine seu servidor com <span class="text-transparent bg-clip-text bg-gradient-to-r from-red-500 to-red-800">inteligência</span>.
        </h1>
        <p class="text-gray-400 text-lg md:text-xl mb-10 max-w-2xl mx-auto">
            Moderação impecável, engajamento automatizado, vendas integradas e uma dashboard linda. Tudo em um único bot.
        </p>
        <a href="/login" class="btn-primary text-lg px-10 py-4">Começar Agora</a>
    </header>
</body>
</html>
"""

# --- HTML: LOGIN ---
HTML_LOGIN = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Surf Trama | Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
    {GLOBAL_STYLE}
</head>
<body class="flex items-center justify-center h-screen">
    <div class="bg-blobs"><div class="blob blob-1"></div><div class="blob blob-2"></div></div>
    
    <div class="glass p-10 w-[400px] fade-up">
        <div class="text-center mb-8">
            <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-red-700 to-red-500 flex items-center justify-center font-bold text-white text-3xl mx-auto mb-4 shadow-lg shadow-red-900/50">T</div>
            <h1 class="text-2xl font-bold text-white">Bem-vindo de volta</h1>
            <p class="text-gray-400 text-sm mt-1">Insira suas credenciais para continuar.</p>
        </div>

        {{% if error %}}
        <div class="bg-red-900/30 border border-red-500/50 text-red-300 p-3 rounded-lg mb-6 text-sm text-center">{{{{ error }}}}</div>
        {{% endif %}}

        <form method="POST" action="/login">
            <div class="mb-5">
                <label class="block text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wide">Usuário</label>
                <input type="text" name="username" class="w-full bg-black/50 border border-gray-700 rounded-xl p-3 text-white focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-all outline-none" placeholder="seu_usuario" required>
            </div>
            <div class="mb-8">
                <label class="block text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wide">Senha</label>
                <input type="password" name="password" class="w-full bg-black/50 border border-gray-700 rounded-xl p-3 text-white focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-all outline-none" placeholder="••••••••" required>
            </div>
            <button type="submit" class="btn-primary w-full py-3">Entrar no Painel</button>
        </form>
        
        <p class="text-center text-sm text-gray-500 mt-6">Ainda não tem conta? <a href="/cadastro" class="text-red-500 hover:text-red-400 font-semibold transition">Criar conta</a></p>
    </div>
</body>
</html>
"""

# --- HTML: CADASTRO ---
HTML_CADASTRO = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Surf Trama | Cadastro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    {GLOBAL_STYLE}
</head>
<body class="flex items-center justify-center h-screen">
    <div class="bg-blobs"><div class="blob blob-1"></div><div class="blob blob-2"></div></div>
    
    <div class="glass p-10 w-[400px] fade-up">
        <h1 class="text-2xl font-bold text-white text-center mb-2">Crie sua conta</h1>
        <p class="text-gray-400 text-sm text-center mb-8">Junte-se à elite dos servidores.</p>

        {{% if error %}}
        <div class="bg-red-900/30 border border-red-500/50 text-red-300 p-3 rounded-lg mb-6 text-sm text-center">{{{{ error }}}}</div>
        {{% endif %}}

        <form method="POST" action="/cadastro">
            <div class="mb-5">
                <label class="block text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wide">Usuário</label>
                <input type="text" name="username" class="w-full bg-black/50 border border-gray-700 rounded-xl p-3 text-white focus:border-red-500 outline-none" required>
            </div>
            <div class="mb-8">
                <label class="block text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wide">Senha</label>
                <input type="password" name="password" class="w-full bg-black/50 border border-gray-700 rounded-xl p-3 text-white focus:border-red-500 outline-none" required>
            </div>
            <button type="submit" class="btn-primary w-full py-3">Criar Conta</button>
        </form>
        
        <p class="text-center text-sm text-gray-500 mt-6">Já possui conta? <a href="/login" class="text-red-500 hover:text-red-400 font-semibold transition">Fazer Login</a></p>
    </div>
</body>
</html>
"""

# --- HTML: PÁGINA DE VENDAS (CASO NÃO TENHA TOKEN) ---
HTML_VENDAS = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Surf Trama | Acesso Bloqueado</title>
    <script src="https://cdn.tailwindcss.com"></script>
    {GLOBAL_STYLE}
</head>
<body class="flex items-center justify-center h-screen">
    <div class="bg-blobs"><div class="blob blob-1"></div></div>
    <div class="glass p-10 w-[450px] text-center fade-up">
        <h1 class="text-3xl font-bold text-red-500 mb-4">Acesso Restrito</h1>
        <p class="text-gray-400 mb-8">Você precisa de um Token de Licença válido para acessar a Dashboard.</p>
        
        <a href="/comprar" class="btn-primary block w-full py-3 mb-6">Comprar Token de Acesso</a>

        <form method="POST" action="/validar_token">
            <p class="text-xs text-gray-500 mb-2 uppercase tracking-wide">Já comprou? Ative aqui:</p>
            <input type="text" name="token" placeholder="TRAMA-XXXX-XXXX" class="w-full bg-black/50 border border-gray-700 rounded-xl p-3 text-white text-center focus:border-red-500 outline-none mb-4 uppercase" required>
            <button type="submit" class="w-full bg-gray-800 hover:bg-gray-700 text-white font-bold py-3 rounded-xl transition">Ativar Token</button>
        </form>
        <a href="/logout" class="block mt-6 text-sm text-gray-600 hover:text-white transition">Sair da Conta</a>
    </div>
</body>
</html>
"""

# --- HTML: DASHBOARD PRINCIPAL ---
HTML_DASHBOARD = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Surf Trama | Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    {GLOBAL_STYLE}
</head>
<body class="p-8">
    <div class="bg-blobs"><div class="blob blob-1"></div><div class="blob blob-2"></div></div>
    
    <div class="max-w-6xl mx-auto fade-up">
        <!-- Header -->
        <div class="flex justify-between items-center mb-10 glass p-4 rounded-2xl">
            <div class="flex items-center gap-4">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-red-700 to-red-500 flex items-center justify-center font-bold text-white">T</div>
                <div>
                    <h1 class="text-lg font-bold text-white">Dashboard</h1>
                    <p class="text-xs text-gray-400">Olá, {{{{ current_user.username }}}} {{% if current_user.is_admin %}}<span class="text-red-400 font-bold">(Admin)</span>{{% endif %}}</p>
                </div>
            </div>
            <a href="/logout" class="bg-white/5 hover:bg-red-900/50 border border-white/10 text-white px-4 py-2 rounded-lg text-sm transition">Sair</a>
        </div>

        <!-- Estatísticas -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div class="glass p-6 text-center border-t-2 border-red-600">
                <p class="text-xs text-gray-400 uppercase tracking-wider mb-1">Servidores</p>
                <p class="text-4xl font-extrabold text-white">{{{{ guilds|length }}}}</p>
            </div>
            <div class="glass p-6 text-center border-t-2 border-green-600">
                <p class="text-xs text-gray-400 uppercase tracking-wider mb-1">Tickets Abertos</p>
                <p class="text-4xl font-extrabold text-green-500">{{{{ total_tickets }}}}</p>
            </div>
            <div class="glass p-6 text-center border-t-2 border-yellow-600">
                <p class="text-xs text-gray-400 uppercase tracking-wider mb-1">Cliques em VIP</p>
                <p class="text-4xl font-extrabold text-yellow-500">{{{{ total_vendas }}}}</p>
            </div>
            <div class="glass p-6 text-center border-t-2 border-blue-600">
                <p class="text-xs text-gray-400 uppercase tracking-wider mb-1">Pix Gerados</p>
                <p class="text-4xl font-extrabold text-blue-500">{{{{ total_pagamentos }}}}</p>
            </div>
        </div>

        <!-- Lista de Servidores -->
        <h2 class="text-lg font-bold text-white mb-4">📡 Seus Servidores</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
            {{% for guild in guilds %}}
            <div class="glass p-4 flex items-center gap-4 hover:border-red-500/50 transition cursor-default">
                {{% if guild.icon %}}
                    <img src="{{{{ guild.icon }}}}" class="w-12 h-12 rounded-full border border-gray-600">
                {{% else %}}
                    <div class="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center text-xs font-bold text-gray-400">TRAMA</div>
                {{% endif %}}
                <div>
                    <h3 class="font-bold text-white text-md truncate w-40">{{{{ guild.name }}}}</h3>
                    <p class="text-xs text-gray-400">{{{{ guild.members }}}} membros • {{{{ guild.in_call }}}} em call</p>
                </div>
            </div>
            {{% else %}}
            <div class="glass p-4 text-center col-span-3 text-gray-400">Nenhum servidor conectado.</div>
            {{% endfor %}}
        </div>

        <!-- Logs Recentes -->
        <h2 class="text-lg font-bold text-white mb-4">📋 Atividades Recentes</h2>
        <div class="glass overflow-hidden rounded-xl">
            <table class="w-full text-left text-sm text-gray-300">
                <thead class="text-xs text-gray-400 uppercase bg-white/5 border-b border-white/10">
                    <tr>
                        <th class="px-6 py-4 font-semibold">Tipo</th>
                        <th class="px-6 py-4 font-semibold">Usuário</th>
                        <th class="px-6 py-4 font-semibold">Detalhe</th>
                        <th class="px-6 py-4 font-semibold">Data</th>
                    </tr>
                </thead>
                <tbody>
                    {{% for log in logs %}}
                    <tr class="border-b border-white/5 hover:bg-white/5 transition">
                        <td class="px-6 py-4 font-bold 
                            {{% if log.tipo == 'Ticket' %}}text-green-500
                            {{% elif log.tipo == 'Venda' %}}text-yellow-500
                            {{% elif log.tipo == 'Pagamento' %}}text-blue-500
                            {{% else %}}text-gray-300{{% endif %}}">
                            {{{{ log.tipo }}}}
                        </td>
                        <td class="px-6 py-4">{{{{ log.user_name }}}}</td>
                        <td class="px-6 py-4">{{{{ log.detalhe }}}}</td>
                        <td class="px-6 py-4">{{{{ log.data }}}}</td>
                    </tr>
                    {{% else %}}
                    <tr><td colspan="4" class="px-6 py-8 text-center text-gray-500">Nenhuma atividade registrada.</td></tr>
                    {{% endfor %}}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

# --- ROTAS DO SITE ---
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
    if not bot.is_ready(): return "Iniciando... Recarregue.", 200
    conn = sqlite3.connect('tickets.db'); cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM estatisticas WHERE tipo = 'Ticket'"); total_tickets = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM estatisticas WHERE tipo = 'Venda'"); total_vendas = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM estatisticas WHERE tipo = 'Pagamento'"); total_pagamentos = cursor.fetchone()[0] or 0
    cursor.execute("SELECT tipo, user_name, detalhe, data FROM estatisticas ORDER BY id DESC LIMIT 10"); logs = cursor.fetchall()
    guilds_data = [{"id": g.id, "name": g.name, "icon": g.icon.url if g.icon else None, "members": g.member_count, "in_call": sum(1 for m in g.members if m.voice and m.voice.channel)} for g in bot.guilds]
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
