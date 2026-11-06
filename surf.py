import discord
from discord import app_commands
from discord.ext import commands
import os

# Configuração de Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class SurfTramaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.COR_TRAMA = 0x8B0000
        self.COR_PRETA = 0x000000

    async def setup_hook(self):
        # Carrega os módulos (Cogs)
        await self.load_extension("cogs.moderacao")
        await self.load_extension("cogs.comunidade")
        await self.load_extension("cogs.suporte")
        
        # Sincroniza os comandos
        await self.tree.sync()
        print(f"Comandos sincronizados para {self.user}")

bot = SurfTramaBot()

@bot.event
async def on_ready():
    print(f'✅ Surf Trama v2.0 online como {bot.user}')
    print(f'📡 Conectado a {len(bot.guilds)} servidor(es).')
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="a TRAMA | /ajuda")
    )

# --- Sistema de Ajuda Básico (Apenas para não perder a função) ---
@bot.tree.command(name="ajuda", description="Mostra o painel de ajuda do Surf Trama")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌊 Central de Ajuda: Surf Trama",
        description="Use os comandos `/` para interagir.\n\n**Módulos Ativos:** Moderação, Suporte, Comunidade.",
        color=bot.COR_TRAMA
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Tratamento de erro global
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("🚫 Você não tem permissão para usar este comando.", ephemeral=True)

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("⚠️ Defina a variável DISCORD_TOKEN.")
    else:
        bot.run(TOKEN)