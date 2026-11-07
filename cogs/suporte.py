import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random
import sqlite3
import datetime

class Suporte(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cria o banco de dados se não existir
        self.conn = sqlite3.connect('tickets.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                user_name TEXT,
                guild_name TEXT,
                channel_name TEXT,
                created_at TEXT
            )
        ''')
        self.conn.commit()

    @app_commands.command(name="painel-ticket", description="Cria o painel de atendimento com botão e imagem.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(imagem="Cole o link direto da imagem (ex: imgur, prnt.sc)")
    async def painel_ticket(self, interaction: discord.Interaction, imagem: str = None):
        texto = (
            "**CENTRAL DE AJUDA E ACOLHIMENTO**\n\n"
            "Estamos aqui para acolher e ajudar no que precisar. Este é um espaço seguro, onde você pode falar abertamente, sem julgamentos.\n\n"
            "Quando se sentir à vontade, é só chamar!\n\n"
            "Estamos com você."
        )
        embed = discord.Embed(description=texto, color=self.bot.COR_TRAMA)
        if imagem: embed.set_image(url=imagem)
        
        await interaction.response.send_message("Painel criado!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=BotaoAbrirTicket())

    async def criar_ticket(self, interaction: discord.Interaction):
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
        
        # SALVA NO BANCO DE DADOS
        agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        self.cursor.execute(
            "INSERT INTO tickets (user_id, user_name, guild_name, channel_name, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(interaction.user.id), str(interaction.user.name), str(guild.name), str(canal.name), agora)
        )
        self.conn.commit()

        embed = discord.Embed(title="🎫 Ticket Aberto", description=f"Olá {interaction.user.mention}, a equipe foi notificada.\nDescreva o que precisa abaixo.", color=self.bot.COR_TRAMA)
        await canal.send(embed=embed, view=BotaoFecharTicket())
        await interaction.response.send_message(f"✅ Ticket criado em {canal.mention}", ephemeral=True)

    @app_commands.command(name="sorteio", description="Cria um sorteio no canal.")
    @app_commands.describe(premio="O que será sorteado", segundos="Duração em segundos")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def sorteio(self, interaction: discord.Interaction, premio: str, segundos: int):
        embed = discord.Embed(title="🎉 SORTEIO!", description=f"Prêmio: **{premio}**\nReaja com 🎉 para participar!", color=self.bot.COR_TRAMA)
        await interaction.response.send_message("Sorteio iniciado!", ephemeral=True)
        mensagem = await interaction.channel.send(embed=embed)
        await mensagem.add_reaction("🎉")
        await asyncio.sleep(segundos)
        
        mensagem = await interaction.channel.fetch_message(mensagem.id)
        reacao = discord.utils.get(mensagem.reactions, emoji="🎉")
        usuarios = [user async for user in reacao.users() if not user.bot]
        
        if not usuarios: await interaction.channel.send(f"❌ Nenhum participante.")
        else:
            vencedor = random.choice(usuarios)
            await interaction.channel.send(f"🏆 Parabéns {vencedor.mention}! Você ganhou **{premio}**!")

class BotaoAbrirTicket(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Iniciar Atendimento", style=discord.ButtonStyle.success, emoji="🎗️", custom_id="btn_abrir_v3")
    async def abrir(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("Suporte")
        await cog.criar_ticket(interaction)

class BotaoFecharTicket(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_fechar_v3")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Fechando...")
        await asyncio.sleep(3)
        await interaction.channel.delete()

async def setup(bot):
    await bot.add_cog(Suporte(bot))
