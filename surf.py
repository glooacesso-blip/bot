import discord
from discord import app_commands
from discord.ext import commands
import os
import sqlite3
import datetime

# --- Configuração Básica ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True

class SurfTramaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.COR_TRAMA = 0x8B0000

    async def setup_hook(self):
        # Carrega todos os módulos
        try:
            await self.load_extension("cogs.moderacao")
            await self.load_extension("cogs.suporte")
            await self.load_extension("cogs.seguranca")
            await self.load_extension("cogs.membros")
            await self.load_extension("cogs.atendimento")
            await self.load_extension("cogs.redes_sociais")
            await self.load_extension("cogs.utilitarios")
            await self.load_extension("cogs.automacao")
            await self.load_extension("cogs.vip")
            await self.load_extension("cogs.pagamentos")
            print("✅ Módulos carregados com sucesso.")
        except Exception as e:
            print(f"❌ ERRO AO CARREGAR MÓDULOS: {e}")
        
        # Sincroniza comandos
        await self.tree.sync()
        print("✅ Comandos sincronizados.")

bot = SurfTramaBot()

@bot.event
async def on_ready():
    print(f'✅ Surf Trama online como {bot.user}')
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="a TRAMA | /ajuda"))

@bot.tree.command(name="ajuda", description="Mostra o painel de ajuda do Surf Trama")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(title="🌊 Ajuda: Surf Trama", description="Use os comandos `/` para interagir.", color=bot.COR_TRAMA)
    await interaction.response.send_message(embed=embed, ephemeral=True)

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("⚠️ Defina a variável DISCORD_TOKEN no painel do Render.")
    else:
        bot.run(TOKEN)
