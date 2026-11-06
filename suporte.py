import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random

class Suporte(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- SISTEMA DE TICKETS ---
    @app_commands.command(name="tickets", description="Abre um ticket de suporte privado.")
    async def abrir_ticket(self, interaction: discord.Interaction):
        guild = interaction.guild
        
        nome_canal = f"ticket-{interaction.user.name.lower()}"
        canal_existente = discord.utils.get(guild.text_channels, name=nome_canal)
        
        if canal_existente:
            await interaction.response.send_message(f"❌ Você já tem um ticket aberto: {canal_existente.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        canal = await guild.create_text_channel(nome_canal, overwrites=overwrites)
        
        embed = discord.Embed(title="🎫 Ticket Aberto", description=f"Olá {interaction.user.mention}, a equipe da TRAMA foi notificada.\nDescreva seu problema abaixo.", color=self.bot.COR_TRAMA)
        await canal.send(embed=embed, view=BotaoFecharTicket())
        await interaction.response.send_message(f"✅ Ticket criado em {canal.mention}", ephemeral=True)

    # --- SISTEMA DE SORTEIO ---
    @app_commands.command(name="sorteio", description="Cria um sorteio no canal.")
    @app_commands.describe(premio="O que será sorteado", segundos="Duração em segundos")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def sorteio(self, interaction: discord.Interaction, premio: str, segundos: int):
        embed = discord.Embed(title="🎉 SORTEIO!", description=f"Prêmio: **{premio}**\nReaja com 🎉 para participar!", color=self.bot.COR_TRAMA)
        embed.set_footer(text=f"Termina em {segundos} segundos.")
        
        await interaction.response.send_message("Sorteio iniciado!", ephemeral=True)
        mensagem = await interaction.channel.send(embed=embed)
        await mensagem.add_reaction("🎉")
        
        await asyncio.sleep(segundos)
        
        mensagem = await interaction.channel.fetch_message(mensagem.id)
        reacao = discord.utils.get(mensagem.reactions, emoji="🎉")
        usuarios = [user async for user in reacao.users() if not user.bot]
        
        if not usuarios:
            await interaction.channel.send(f"❌ O sorteio de **{premio}** terminou sem participantes.")
        else:
            vencedor = random.choice(usuarios)
            await interaction.channel.send(f"🏆 Parabéns {vencedor.mention}! Você ganhou **{premio}**!")

class BotaoFecharTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.red, emoji="🔒")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Fechando ticket em 5 segundos...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

async def setup(bot):
    await bot.add_cog(Suporte(bot))
