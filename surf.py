import discord
from discord import app_commands
from discord.ext import commands
import os
import sqlite3
from flask import Flask, request
from threading import Thread

# --- Configuração do Servidor Web ---
app = Flask('')
SENHA_ADMIN = "trama123"

HTML_PAGE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Surf Trama | Dashboard</title>
    <style>
        body {{ background-color: #0a0a0a; color: #fff; font-family: 'Segoe UI', sans-serif; display: flex; justify-content: center; padding: 20px; margin: 0; }}
        .container {{ background-color: #1a1a1a; border: 1px solid #8B0000; border-radius: 12px; padding: 30px; max-width: 800px; width: 100%; box-shadow: 0 0 20px rgba(139, 0, 0, 0.4); }}
        h1, h2 {{ color: #ff3333; }}
        .status {{ display: inline-block; background-color: #00ff00; color: #000; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 12px; text-transform: uppercase; }}
        .info-box {{ background-color: #0a0a0a; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ color: #ff3333; }}
        .btn-leave {{ background-color: #8B0000; color: white; text-decoration: none; padding: 5px 10px; border-radius: 5px; font-size: 12px; float: right; }}
        .btn-leave:hover {{ background-color: #ff3333; }}
        ul {{ list-style: none; padding: 0; }}
        li {{ padding: 8px 0; border-bottom: 1px solid #222; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌊 Surf Trama</h1>
        <div class="status">Online</div>
        <p><strong>👑 Dono:</strong> DS BOYZAO</p>
        <div class="info-box">
            <h2>📡 Servidores ({guild_count})</h2>
            <ul>{guild_list}</ul>
        </div>
        <div class="info-box">
            <h2>🎫 Tickets Abertos ({ticket_count})</h2>
            <table>
                <tr><th>Usuário</th><th>Servidor</th><th>Horário</th></tr>
                {ticket_list}
            </table>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    if not bot.is_ready(): return "Iniciando bot... Recarregue em 10 segundos.", 200
    guilds = []
    for guild in bot.guilds:
        btn = f'<a href="/sair/{guild.id}?senha={SENHA_ADMIN}" class="btn-leave">Sair</a>'
        guilds.append(f"<li>{guild.name} {btn}</li>")
    tickets = []
    try:
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_name, guild_name, created_at FROM tickets ORDER BY id DESC LIMIT 10")
        for row in cursor.fetchall():
            tickets.append(f"<tr><td>@{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td></tr>")
        conn.close()
    except: tickets.append(f"<tr><td colspan='3'>Erro no banco.</td></tr>")
    return HTML_PAGE.format(guild_count=len(bot.guilds), guild_list="".join(guilds) if guilds else "<li>Nenhum</li>", ticket_count=len(tickets), ticket_list="".join(tickets) if tickets else "<tr><td colspan='3'>Nenhum ticket.</td></tr>")

@app.route('/sair/<int:guild_id>')
def sair_servidor(guild_id):
    if request.args.get('senha') != SENHA_ADMIN: return "Acesso negado", 403
    guild = bot.get_guild(guild_id)
    if guild:
        import asyncio
        asyncio.run_coroutine_threadsafe(guild.leave(), bot.loop)
        return f"<body style='background:#0a0a0a; color:white; text-align:center; padding:50px;'><h2 style='color:#ff3333;'>✅ Saiu de: {guild.name}</h2><a href='/' style='color:#00ff00;'>Voltar</a></body>"
    return "Não encontrado", 404

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

class SurfTramaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.COR_TRAMA = 0x8B0000
        self.COR_PRETA = 0x000000

    async def setup_hook(self):
        print("⏳ Carregando módulos...")
        try:
            await self.load_extension("cogs.moderacao")
            await self.load_extension("cogs.suporte")
            await self.load_extension("cogs.seguranca")
            await self.load_extension("cogs.membros")
            await self.load_extension("cogs.atendimento")
            await self.load_extension("cogs.redes_sociais")
            await self.load_extension("cogs.utilitarios")
            print("✅ Módulos carregados com sucesso.")
        except Exception as e:
            print(f"❌ ERRO AO CARREGAR MÓDULOS: {e}")
        
        # Limpa comandos antigos do cache e sincroniza os novos
        try:
            print("🧹 Limpando cache de comandos antigos...")
            await self.tree.sync()
            print("✅ Comandos sincronizados com o Discord!")
        except Exception as e:
            print(f"❌ Erro ao sincronizar comandos: {e}")

bot = SurfTramaBot()

@bot.event
async def on_ready():
    print(f'✅ Surf Trama v2.0 online como {bot.user}')
    print(f'📡 Conectado a {len(bot.guilds)} servidor(es).')
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="a TRAMA | /ajuda"))

@bot.tree.command(name="ajuda", description="Mostra o painel de ajuda do Surf Trama")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(title="🌊 Central de Ajuda: Surf Trama", description="Use os comandos `/` para interagir.\n\n**Módulos:** Moderação, Suporte, Segurança, Membros, Atendimento, Redes Sociais e Utilitários.", color=bot.COR_TRAMA)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("🚫 Você não tem permissão para usar este comando.", ephemeral=True)
    elif isinstance(error, app_commands.BotMissingPermissions):
        await interaction.response.send_message("🤖 Eu não tenho permissão suficiente.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Ocorreu um erro: `{error}`", ephemeral=True)

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("⚠️ Defina a variável DISCORD_TOKEN no painel do Render.")
    else:
        keep_alive()
        bot.run(TOKEN)
