import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
from flask import Flask
from threading import Thread

# --- Configuração do Servidor Web ---
app = Flask('')

# HTML da página inicial (Dashboard)
HTML_PAGE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Surf Trama | Dashboard</title>
    <style>
        body {
            background-color: #0a0a0a;
            color: #ffffff;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .container {
            background-color: #1a1a1a;
            border: 1px solid #8B0000;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            box-shadow: 0px 0px 20px rgba(139, 0, 0, 0.4);
            max-width: 500px;
            width: 100%;
        }
        h1 {
            color: #ff3333;
            margin-bottom: 5px;
        }
        p.subtitle {
            color: #aaaaaa;
            margin-bottom: 30px;
        }
        .status {
            display: inline-block;
            background-color: #00ff00;
            color: #000;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 20px;
            text-transform: uppercase;
        }
        .info-box {
            background-color: #0a0a0a;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            text-align: left;
        }
        .info-box strong {
            color: #ff3333;
        }
        ul {
            list-style-type: none;
            padding: 0;
            margin: 0;
        }
        li {
            padding: 5px 0;
            border-bottom: 1px solid #222;
        }
        li:last-child {
            border-bottom: none;
        }
        .footer {
            margin-top: 30px;
            font-size: 12px;
            color: #555;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌊 Surf Trama</h1>
        <p class="subtitle">Gerenciamento e Engajamento TRAMA</p>
        <div class="status">Online 24/7</div>
        
        <div class="info-box">
            <strong>👑 Dono:</strong> DS BOYZAO
        </div>

        <div class="info-box">
            <strong>📡 Servidores Conectados ({guild_count}):</strong>
            <ul>
                {guild_list}
            </ul>
        </div>
        
        <div class="footer">Bot operando perfeitamente.</div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    # Pega a lista de servidores onde o bot está
    guilds = [guild.name for guild in bot.guilds]
    guild_list_html = "".join([f"<li>{g}</li>" for g in guilds])
    
    # Se não estiver em nenhum servidor
    if not guilds:
        guild_list_html = "<li>Nenhum servidor no momento.</li>"
        
    return HTML_PAGE.format(
        guild_count=len(bot.guilds),
        guild_list=guild_list_html
    )

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- Configuração do Bot ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class SurfTramaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.COR_TRAMA = 0x8B0000
        self.COR_PRETA = 0x000000

    async def setup_hook(self):
        try:
            await self.load_extension("cogs.moderacao")
            await self.load_extension("cogs.suporte")
            print("✅ Módulos carregados com sucesso.")
        except Exception as e:
            print(f"❌ Erro ao carregar módulos: {e}")
        
        await self.tree.sync()
        print(f"🔄 Comandos sincronizados para {self.user}")

bot = SurfTramaBot()

@bot.event
async def on_ready():
    print(f'✅ Surf Trama v2.0 online como {bot.user}')
    print(f'📡 Conectado a {len(bot.guilds)} servidor(es).')
    
    print("⏳ Tentando alterar status para Online...")
    await bot.change_presence(
        status=discord.Status.online, 
        activity=discord.Activity(type=discord.ActivityType.watching, name="a TRAMA | /ajuda")
    )
    print("🟢 Status alterado com sucesso!")

@bot.tree.command(name="ajuda", description="Mostra o painel de ajuda do Surf Trama")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌊 Central de Ajuda: Surf Trama",
        description="Use os comandos `/` para interagir.\n\n**Módulos Ativos:** Moderação, Suporte, Comunidade.",
        color=bot.COR_TRAMA
    )
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
