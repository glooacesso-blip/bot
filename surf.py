import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import sqlite3
import datetime
from flask import Flask, request, jsonify, render_template_string
from threading import Thread

# --- Configuração do Servidor Web ---
app = Flask('')
SENHA_ADMIN = "trama123"

# --- HTML DO SITE (DASHBOARD) ---
HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Surf Trama | Dashboard</title>
    <!-- Tailwind CSS para o visual igual ao da imagem -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Chart.js para o gráfico -->
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
        <!-- Header -->
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
                <p class="text-xs text-green-500 mt-1">Registros ainda disponíveis</p>
            </div>
            <div class="card">
                <p class="stat-label flex items-center gap-2">💬 Mensagens - 30 dias</p>
                <p class="stat-value mt-2">{{ mensagens_30d }}</p>
                <p class="text-xs text-gray-500 mt-1">No período selecionado</p>
            </div>
            <div class="card">
                <p class="stat-label flex items-center gap-2">🎧 Tempo em call - 30 dias</p>
                <p class="stat-value mt-2">{{ tempo_call }}</p>
                <p class="text-xs text-gray-500 mt-1">Sessões observadas em servidores</p>
            </div>
        </div>

        <!-- Gráfico -->
        <div class="card mb-8">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-white font-semibold">Atividade nos últimos 30 dias</h3>
                <div class="bg-[#262626] rounded-md p-1 flex gap-1">
                    <button class="px-3 py-1 text-xs bg-[#171717] text-white rounded">Mensagens</button>
                    <button class="px-3 py-1 text-xs text-gray-400">Voz</button>
                </div>
            </div>
            <div class="h-64">
                <canvas id="activityChart"></canvas>
            </div>
        </div>

        <!-- Onde você mais fica em call -->
        <div class="card mb-8">
            <h3 class="text-white font-semibold mb-4">Onde mais fica em call</h3>
            <p class="text-xs text-gray-400 mb-4">Tempo registrado por canal nos últimos 30 dias.</p>
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

        <!-- Top Servidores e DMs -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="card">
                <h3 class="text-white font-semibold mb-2">Top Servidores</h3>
                <p class="text-xs text-gray-400 mb-4">Mensagens registradas nos últimos 30 dias.</p>
                {% for server in top_servers %}
                <div class="flex justify-between items-center py-2 border-b border-[#262626]">
                    <span class="text-sm text-gray-300">{{ server.nome }}</span>
                    <span class="text-sm font-bold text-white">{{ server.qtd }}</span>
                </div>
                {% endfor %}
            </div>
            <div class="card">
                <h3 class="text-white font-semibold mb-2">Top DMs</h3>
                <p class="text-xs text-gray-400 mb-4">Conversas privadas</p>
                <div class="flex flex-col items-center justify-center h-32 text-gray-500">
                    <span class="text-2xl mb-2">💬</span>
                    <p class="text-sm">Histórico indisponível</p>
                </div>
            </div>
        </div>
    </main>

    <script>
        // Gráfico de linha simulado (você pode puxar os dados reais do banco depois)
        const ctx = document.getElementById('activityChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['10/10', '24/10', '08/11'],
                datasets: [{
                    label: 'Mensagens',
                    data: [0, 0, 16],
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
                    y: { grid: { color: '#262626' }, ticks: { color: '#a3a3a3' } }
                }
            }
        });
    </script>
</body>
</html>
"""

# --- Configuração do Banco de Dados ---
def setup_database():
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    # Tabela de mensagens
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estatisticas_mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT, guild_id TEXT, data TEXT
        )
    ''')
    # Tabela de call
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estatisticas_call (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT, guild_id TEXT, channel_name TEXT, tempo_segundos INTEGER, data TEXT
        )
    ''')
    conn.commit()
    conn.close()

setup_database()

# --- Rotas do Site ---
@app.route('/')
def home():
    if not bot.is_ready(): return "Iniciando bot... Recarregue em 10 segundos.", 200
    
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    
    # Pega os dados reais
    cursor.execute("SELECT COUNT(*) FROM estatisticas_mensagens")
    total_msgs = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM estatisticas_mensagens WHERE data >= date('now', '-30 days')")
    msgs_30d = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(tempo_segundos) FROM estatisticas_call")
    total_segundos = cursor.fetchone()[0] or 0
    horas = total_segundos // 3600
    minutos = (total_segundos % 3600) // 60
    tempo_call = f"{horas}h {minutos}m"
    
    # Dados para o gráfico e tops (simulados por enquanto para ficar igual ao print)
    canais_top = [
        {"nome": "#EM-BREVE", "tempo": "13h 25m"},
        {"nome": "#EM-BREVE", "tempo": "5h 43m"},
        {"nome": "#EM-BREVE", "tempo": "4h 55m"},
        {"nome": "#EM-BREVE", "tempo": "4h 30m"}
    ]
    top_servers = [{"nome": "TRAMA #EM-BREVE", "qtd": msgs_30d}]
    
    conn.close()
    
    return render_template_string(
        HTML_DASHBOARD, 
        total_mensagens=total_msgs, 
        mensagens_30d=msgs_30d,
        tempo_call=tempo_call,
        canais_top=canais_top,
        top_servers=top_servers
    )

@app.route('/sair')
def sair_servidor():
    # Função simples para derrubar o bot (você pode proteger com senha)
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

# --- EVENTOS PARA ESTATÍSTICAS ---
@bot.event
async def on_ready():
    print(f'✅ Surf Trama v2.0 online como {bot.user}')
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="a TRAMA | /ajuda"))

@bot.event
async def on_message(message):
    if not message.author.bot:
        # Registrar mensagem no banco
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO estatisticas_mensagens (user_id, guild_id, data) VALUES (?, ?, ?)", (str(message.author.id), str(message.guild.id), agora))
        conn.commit()
        conn.close()
    
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    # Se entrou na call
    if before.channel is None and after.channel is not None:
        bot.call_timers[member.id] = datetime.datetime.now()
    # Se saiu da call
    elif before.channel is not None and after.channel is None:
        if member.id in bot.call_timers:
            entrada = bot.call_timers.pop(member.id)
            tempo = (datetime.datetime.now() - entrada).total_seconds()
            # Salva o tempo no banco
            conn = sqlite3.connect('tickets.db')
            cursor = conn.cursor()
            agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO estatisticas_call (user_id, guild_id, channel_name, tempo_segundos, data) VALUES (?, ?, ?, ?, ?)", 
                           (str(member.id), str(member.guild.id), before.channel.name, int(tempo), agora))
            conn.commit()
            conn.close()

@bot.tree.command(name="ajuda", description="Mostra o painel de ajuda.")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(title="🌊 Central de Ajuda: Surf Trama", description="Use os comandos `/` para interagir.", color=bot.COR_TRAMA)
    await interaction.response.send_message(embed=embed, ephemeral=True)

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("⚠️ Defina a variável DISCORD_TOKEN.")
    else:
        keep_alive()
        bot.run(TOKEN)
