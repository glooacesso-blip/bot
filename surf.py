import discord
from discord import app_commands
from discord.ext import commands
import os
import sqlite3
import datetime
from flask import Flask, request, jsonify, render_template_string
from threading import Thread

# --- Configuração do Servidor Web ---
app = Flask('')
SENHA_ADMIN = "trama123"

# --- HTML DO SITE (DASHBOARD FUNCIONAL) ---
HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Surf Trama | Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #0a0a0a; color: #e5e7eb; }
        .card { background-color: #171717; border: 1px solid #262626; border-radius: 12px; padding: 20px; }
        .stat-value { font-size: 32px; font-weight: 600; color: #fff; }
        .stat-label { font-size: 14px; color: #a3a3a3; }
        .sidebar-item { display: flex; align-items: center; padding: 10px 15px; border-radius: 8px; color: #a3a3a3; transition: 0.2s; cursor: pointer; }
        .sidebar-item:hover { background-color: #262626; color: #fff; }
        .sidebar-item.active { background-color: #8B0000; color: #fff; }
    </style>
</head>
<body class="flex h-screen overflow-hidden">
    <!-- Sidebar -->
    <aside class="w-64 bg-[#0a0a0a] border-r border-[#262626] flex flex-col p-4">
        <div class="flex items-center gap-3 mb-8 px-2">
            <div class="w-8 h-8 rounded-full bg-[#8B0000] flex items-center justify-center font-bold text-white">T</div>
            <div>
                <h1 class="text-white font-bold">TRAMA</h1>
                <p class="text-xs text-gray-500">Tools</p>
            </div>
        </div>
        
        <div class="mb-6">
            <p class="text-xs font-semibold text-gray-500 mb-2 px-2">CONTA SELECIONADA</p>
            <div class="sidebar-item active">
                <div class="w-6 h-6 rounded-full bg-gray-600 mr-2"></div>
                <span>@SurfTramaBot</span>
            </div>
        </div>

        <nav class="flex-1 space-y-1">
            <p class="text-xs font-semibold text-gray-500 mb-2 px-2 mt-4">VISÃO GERAL</p>
            <div class="sidebar-item"><span>📊 Inicio</span></div>
            <div class="sidebar-item"><span>⏱️ Presença</span></div>
            <div class="sidebar-item"><span>🎮 Atividade</span></div>
            
            <p class="text-xs font-semibold text-gray-500 mb-2 px-2 mt-4">CONTA</p>
            <div class="sidebar-item"><span>👥 Contas</span></div>
            <div class="sidebar-item"><span>🚀 HypeSquad</span></div>
        </nav>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto p-8">
        <div class="flex justify-between items-center mb-8">
            <div>
                <h2 class="text-2xl font-bold text-white">Visão geral</h2>
                <p class="text-sm text-gray-400">Atividade registrada do servidor TRAMA.</p>
            </div>
            <div class="flex items-center gap-4">
                <a href="/sair" class="text-sm text-red-500 hover:text-red-400">Sair do Servidor</a>
                <div class="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center">👑</div>
            </div>
        </div>

        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="card">
                <p class="stat-label flex items-center gap-2">💬 Mensagens Registradas</p>
                <p class="stat-value mt-2">{{ total_mensagens }}</p>
            </div>
            <div class="card">
                <p class="stat-label flex items-center gap-2">💬 Mensagens - 30 dias</p>
                <p class="stat-value mt-2">{{ mensagens_30d }}</p>
            </div>
            <div class="card">
                <p class="stat-label flex items-center gap-2">🎧 Tempo em call (Total)</p>
                <p class="stat-value mt-2">{{ tempo_call }}</p>
            </div>
        </div>

        <!-- Gráfico -->
        <div class="card mb-8">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-white font-semibold">Atividade (Mensagens/Dia)</h3>
            </div>
            <div class="h-64">
                <canvas id="activityChart"></canvas>
            </div>
        </div>

        <!-- Onde você mais fica em call -->
        <div class="card mb-8">
            <h3 class="text-white font-semibold mb-4">Canais mais usados (Call)</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {% for canal in canais_top %}
                <div class="bg-[#262626] p-4 rounded-lg flex items-center justify-between">
                    <div>
                        <p class="text-xs text-gray-400">{{ canal.nome }}</p>
                        <p class="text-white font-bold text-sm">{{ canal.tempo }}</p>
                    </div>
                    <span class="text-xl">🎧</span>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- Top Servidores -->
        <div class="card">
            <h3 class="text-white font-semibold mb-2">Top Servidores</h3>
            <div class="flex justify-between items-center py-2 border-b border-[#262626]">
                <span class="text-sm text-gray-300">{{ top_server_nome }}</span>
                <span class="text-sm font-bold text-white">{{ total_mensagens }}</span>
            </div>
        </div>
    </main>

    <script>
        // Puxa os dados reais da API do Flask
        fetch('/api/chart_data')
            .then(response => response.json())
            .then(data => {
                const ctx = document.getElementById('activityChart').getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            label: 'Mensagens',
                            data: data.values,
                            borderColor: '#8B0000',
                            backgroundColor: 'rgba(139, 0, 0, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { grid: { color: '#262626' }, ticks: { color: '#a3a3a3' } },
                            y: { grid: { color: '#262626' }, ticks: { color: '#a3a3a3' }, beginAtZero: true }
                        }
                    }
                });
            });
    </script>
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
@app.route('/')
def home():
    if not bot.is_ready(): return "Iniciando bot... Recarregue em 10 segundos.", 200
    
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    
    # 1. Total de mensagens
    cursor.execute("SELECT COUNT(*) FROM estatisticas_mensagens")
    total_msgs = cursor.fetchone()[0] or 0
    
    # 2. Mensagens nos últimos 30 dias
    cursor.execute("SELECT COUNT(*) FROM estatisticas_mensagens WHERE data >= date('now', '-30 days')")
    msgs_30d = cursor.fetchone()[0] or 0
    
    # 3. Tempo total em call
    cursor.execute("SELECT SUM(tempo_segundos) FROM estatisticas_call")
    total_segundos = cursor.fetchone()[0] or 0
    horas = total_segundos // 3600
    minutos = (total_segundos % 3600) // 60
    tempo_call = f"{horas}h {minutos}m"

    # 4. Canais mais usados
    cursor.execute("SELECT channel_name, SUM(tempo_segundos) as total FROM estatisticas_call GROUP BY channel_name ORDER BY total DESC LIMIT 4")
    canais_raw = cursor.fetchall()
    canais_top = []
    for nome, segundos in canais_raw:
        h = segundos // 3600
        m = (segundos % 3600) // 60
        canais_top.append({"nome": nome, "tempo": f"{h}h {m}m"})
    
    # Se não tiver dados, mostra um padrão
    if not canais_top:
        canais_top = [{"nome": "Nenhum registro ainda", "tempo": "0h 0m"}]

    # 5. Nome do servidor
    top_server_nome = bot.guilds[0].name if bot.guilds else "Desconhecido"
    
    conn.close()
    
    return render_template_string(
        HTML_DASHBOARD, 
        total_mensagens=total_msgs, 
        mensagens_30d=msgs_30d,
        tempo_call=tempo_call,
        canais_top=canais_top,
        top_server_nome=top_server_nome
    )

@app.route('/api/chart_data')
def chart_data():
    # Rota que alimenta o gráfico com os últimos 10 dias de mensagens
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    
    labels = []
    values = []
    
    for i in range(9, -1, -1): # Pega os últimos 10 dias
        data_alvo = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        labels.append(data_alvo[8:10] + "/" + data_alvo[5:7]) # Formato DD/MM
        
        cursor.execute("SELECT COUNT(*) FROM estatisticas_mensagens WHERE data LIKE ?", (f"{data_alvo}%",))
        count = cursor.fetchone()[0] or 0
        values.append(count)
        
    conn.close()
    return jsonify({"labels": labels, "values": values})

@app.route('/sair')
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
