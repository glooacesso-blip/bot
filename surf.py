import discord
from discord import app_commands
from discord.ext import commands
import os
import sqlite3
import datetime
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from threading import Thread

# --- Configuração do Servidor Web ---
app = Flask(__name__)
app.secret_key = 'chave_super_secreta_trama_2026' # Necessário para o login funcionar

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Usuário Admin (Você pode mudar aqui)
ADMIN_USER = "surf157"
ADMIN_PASS = "surf"

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    if user_id == ADMIN_USER:
        return User(user_id)
    return None

# --- HTML DO SITE (DASHBOARD) ---
HTML_LOGIN = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Surf Trama | Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>body { background-color: #0a0a0a; color: #fff; font-family: sans-serif; }</style>
</head>
<body class="flex items-center justify-center h-screen">
    <div class="bg-[#171717] p-8 rounded-xl border border-[#262626] w-96 shadow-2xl">
        <div class="text-center mb-8">
            <h1 class="text-3xl font-bold text-red-600">🌊 Surf Trama</h1>
            <p class="text-gray-400 text-sm mt-2">Acesso Restrito à Administração</p>
        </div>
        {% if error %}
        <div class="bg-red-900/50 border border-red-500 text-red-300 p-3 rounded mb-4 text-sm text-center">
            {{ error }}
        </div>
        {% endif %}
        <form method="POST" action="/login">
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-400 mb-2">Usuário</label>
                <input type="text" name="username" class="w-full bg-[#0a0a0a] border border-[#333] rounded p-2 text-white focus:outline-none focus:border-red-500" required>
            </div>
            <div class="mb-6">
                <label class="block text-sm font-medium text-gray-400 mb-2">Senha</label>
                <input type="password" name="password" class="w-full bg-[#0a0a0a] border border-[#333] rounded p-2 text-white focus:outline-none focus:border-red-500" required>
            </div>
            <button type="submit" class="w-full bg-red-700 hover:bg-red-600 text-white font-bold py-2 px-4 rounded transition duration-200">
                Entrar no Painel
            </button>
        </form>
    </div>
</body>
</html>
"""

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Surf Trama | Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #0a0a0a; color: #e5e7eb; }
        .card { background-color: #171717; border: 1px solid #262626; border-radius: 12px; padding: 20px; transition: 0.2s; }
        .card:hover { border-color: #8B0000; transform: translateY(-2px); }
        .stat-value { font-size: 28px; font-weight: 600; color: #fff; }
        .stat-label { font-size: 13px; color: #a3a3a3; }
        .server-icon { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; border: 2px solid #262626; }
    </style>
</head>
<body class="p-8">
    <div class="max-w-6xl mx-auto">
        <!-- Header -->
        <div class="flex justify-between items-center mb-10 pb-6 border-b border-[#262626]">
            <div class="flex items-center gap-4">
                <div class="w-12 h-12 rounded-full bg-red-700 flex items-center justify-center font-bold text-white text-xl">T</div>
                <div>
                    <h1 class="text-2xl font-bold text-white">Surf Trama Dashboard</h1>
                    <p class="text-sm text-gray-400">Bem-vindo, Administrador</p>
                </div>
            </div>
            <a href="/logout" class="bg-[#262626] hover:bg-red-900 text-white px-4 py-2 rounded-lg text-sm transition">Sair do Painel</a>
        </div>

        <!-- Servidores -->
        <h2 class="text-xl font-semibold text-white mb-4">📡 Servidores Conectados ({{ guilds|length }})</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-10">
            {% for guild in guilds %}
            <div class="card">
                <div class="flex items-center gap-4 mb-4">
                    {% if guild.icon %}
                        <img src="{{ guild.icon }}" alt="Logo" class="server-icon">
                    {% else %}
                        <div class="server-icon bg-gray-700 flex items-center justify-center text-xs">TRAMA</div>
                    {% endif %}
                    <div>
                        <h3 class="font-bold text-white text-lg truncate w-40">{{ guild.name }}</h3>
                        <p class="text-xs text-gray-500">ID: {{ guild.id }}</p>
                    </div>
                </div>
                
                <div class="grid grid-cols-2 gap-4 mt-4">
                    <div class="bg-[#0a0a0a] p-3 rounded-lg text-center border border-[#262626]">
                        <p class="stat-label">👥 Membros</p>
                        <p class="stat-value">{{ guild.members }}</p>
                    </div>
                    <div class="bg-[#0a0a0a] p-3 rounded-lg text-center border border-[#262626]">
                        <p class="stat-label">🎧 Em Call</p>
                        <p class="stat-value text-green-500">{{ guild.in_call }}</p>
                    </div>
                </div>
            </div>
            {% else %}
            <div class="card text-center col-span-3">
                <p class="text-gray-400">O bot ainda não foi adicionado a nenhum servidor.</p>
            </div>
            {% endfor %}
        </div>

        <!-- Status do Bot -->
        <div class="card bg-gradient-to-r from-[#171717] to-[#1a0000]">
            <h3 class="text-white font-semibold mb-2">🤖 Status do Bot</h3>
            <p class="text-sm text-gray-400">O bot está online e operando em {{ guilds|length }} servidor(es).</p>
            <div class="mt-4 flex gap-2">
                <span class="bg-green-900/50 text-green-400 text-xs px-2 py-1 rounded border border-green-800">Online</span>
                <span class="bg-gray-800 text-gray-300 text-xs px-2 py-1 rounded">Versão 2.0</span>
            </div>
        </div>
    </div>
</body>
</html>
"""

# --- Configuração do Banco de Dados ---
def setup_database():
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS estatisticas_mensagens (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, guild_id TEXT, guild_name TEXT, data TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS estatisticas_call (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, guild_id TEXT, channel_name TEXT, tempo_segundos INTEGER, data TEXT)''')
    conn.commit()
    conn.close()

setup_database()

# --- Rotas do Site ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USER and password == ADMIN_PASS:
            user = User(username)
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            return render_template_string(HTML_LOGIN, error="Usuário ou senha incorretos.")
            
    return render_template_string(HTML_LOGIN)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    if not bot.is_ready(): return "Iniciando bot... Recarregue em 10 segundos.", 200
    
    guilds_data = []
    for guild in bot.guilds:
        # Conta quantos estão em call (voice)
        in_call = sum(1 for member in guild.members if member.voice and member.voice.channel)
        
        guilds_data.append({
            "id": guild.id,
            "name": guild.name,
            "icon": guild.icon.url if guild.icon else None,
            "members": guild.member_count,
            "in_call": in_call
        })
    
    # Ordena pelo servidor com mais membros
    guilds_data.sort(key=lambda x: x['members'], reverse=True)
    
    return render_template_string(HTML_DASHBOARD, guilds=guilds_data)

@app.route('/sair')
@login_required
def sair_servidor():
    os._exit(0)

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web); t.start()

# --- Configuração do Bot ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True

class SurfTramaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.COR_TRAMA = 0x8B0000
        self.COR_PRETA = 0x000000
        self.call_timers = {}

    async def setup_hook(self):
        try:
            await self.load_extension("cogs.moderacao")
            await self.load_extension("cogs.suporte")
            await self.load_extension("cogs.seguranca")
            await self.load_extension("cogs.membros")
            await self.load_extension("cogs.atendimento")
            await self.load_extension("cogs.redes_sociais")
            await self.load_extension("cogs.utilitarios")
            await self.load_extension("cogs.automacao")
            print("✅ Módulos carregados com sucesso.")
        except Exception as e:
            print(f"❌ ERRO AO CARREGAR MÓDULOS: {e}")
        
        await self.tree.sync()
        print("✅ Comandos sincronizados.")

bot = SurfTramaBot()

@bot.event
async def on_ready():
    print(f'✅ Surf Trama v2.0 online como {bot.user}')
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="a TRAMA | /ajuda"))

@bot.event
async def on_message(message):
    if not message.author.bot and message.guild:
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO estatisticas_mensagens (user_id, guild_id, guild_name, data) VALUES (?, ?, ?, ?)", 
                       (str(message.author.id), str(message.guild.id), message.guild.name, agora))
        conn.commit()
        conn.close()
    
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel is None and after.channel is not None:
        bot.call_timers[member.id] = datetime.datetime.now()
    elif before.channel is not None and after.channel is None:
        if member.id in bot.call_timers:
            entrada = bot.call_timers.pop(member.id)
            tempo = (datetime.datetime.now() - entrada).total_seconds()
            conn = sqlite3.connect('tickets.db')
            cursor = conn.cursor()
            agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO estatisticas_call (user_id, guild_id, channel_name, tempo_segundos, data) VALUES (?, ?, ?, ?, ?)", 
                           (str(member.id), str(member.guild.id), before.channel.name, int(tempo), agora))
            conn.commit()
            conn.close()

@bot.tree.command(name="ajuda", description="Mostra o painel de ajuda do Surf Trama")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(title="🌊 Central de Ajuda: Surf Trama", description="Use os comandos `/` para interagir.", color=bot.COR_TRAMA)
    await interaction.response.send_message(embed=embed, ephemeral=True)

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("⚠️ Defina a variável DISCORD_TOKEN no painel do Render.")
    else:
        keep_alive()
        bot.run(TOKEN)
