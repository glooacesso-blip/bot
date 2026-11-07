import discord
from discord import app_commands
from discord.ext import commands
import datetime

class Moderacao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="moderação", description="Abre o painel de comandos de moderação.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def painel_mod(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🛡️ Painel de Moderação", color=self.bot.COR_TRAMA)
        embed.description = "Comandos disponíveis:\n`/ban` `/kick` `/limpar`\n`/warn` `/mute` `/unmute` `/unban`"
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="warn", description="Aplica um aviso a um usuário.")
    @app_commands.describe(usuario="Quem receberá o aviso", motivo="Motivo do aviso")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, usuario: discord.Member, motivo: str):
        try:
            await usuario.send(f"⚠️ Você recebeu um aviso no servidor **{interaction.guild.name}**.\n**Motivo:** {motivo}")
        except discord.Forbidden:
            pass
        
        embed = discord.Embed(title="⚠️ Aviso Aplicado", color=self.bot.COR_TRAMA)
        embed.add_field(name="Usuário", value=usuario.mention)
        embed.add_field(name="Motivo", value=motivo)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="mute", description="Silencia um usuário (Timeout).")
    @app_commands.describe(usuario="Usuário a ser silenciado", minutos="Tempo em minutos", motivo="Motivo do mute")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, usuario: discord.Member, minutos: int, motivo: str):
        duracao = datetime.timedelta(minutes=minutos)
        await usuario.timeout(duracao, reason=motivo)
        
        embed = discord.Embed(title="🔇 Usuário Silenciado", color=self.bot.COR_TRAMA)
        embed.add_field(name="Usuário", value=usuario.mention)
        embed.add_field(name="Tempo", value=f"{minutos} minutos")
        embed.add_field(name="Motivo", value=motivo)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unmute", description="Remove o silenciamento de um usuário.")
    @app_commands.describe(usuario="Usuário a ter o mute removido")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, usuario: discord.Member):
        await usuario.timeout(None)
        await interaction.response.send_message(f"🔊 {usuario.mention} não está mais silenciado.", ephemeral=True)

    @app_commands.command(name="unban", description="Revoga o banimento de um usuário.")
    @app_commands.describe(id_usuario="ID do usuário banido")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, id_usuario: str):
        try:
            usuario = await self.bot.fetch_user(int(id_usuario))
            await interaction.guild.unban(usuario)
            await interaction.response.send_message(f"✅ O banimento de {usuario.name} foi revogado.")
        except discord.NotFound:
            await interaction.response.send_message("❌ Usuário não encontrado ou não está banido.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderacao(bot))
