import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import sqlite3
import datetime

class Suporte(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('tickets.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS tickets (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, user_name TEXT, guild_name TEXT, channel_name TEXT, created_at TEXT)''')
        self.conn.commit()

    @app_commands.command(name="painel-ticket", description="Cria o painel de atendimento.")
    @app_commands.checks.has_permissions(administrator=True)
    async def painel_ticket(self, interaction: discord.Interaction, imagem: str = None):
        embed = discord.Embed(title="🎫 Central de Atendimento", description="Selecione o motivo do contato abaixo.", color=self.bot.COR_TRAMA)
        if imagem: embed.set_image(url=imagem)
        await interaction.response.send_message("Painel criado!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=MenuAbrirTicket())

    async def criar_ticket(self, interaction: discord.Interaction, assunto: str):
        guild = interaction.guild
        nome_canal = f"ticket-{interaction.user.name.lower()}"
        if discord.utils.get(guild.text_channels, name=nome_canal): return await interaction.response.send_message(f"❌ Você já tem um ticket aberto.", ephemeral=True)

        # REGISTRA NO BANCO DE DADOS (ESTATÍSTICA)
        agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        self.cursor.execute("INSERT INTO estatisticas (tipo, user_id, user_name, guild_id, detalhe, data) VALUES (?, ?, ?, ?, ?, ?)",
                       ('Ticket', str(interaction.user.id), interaction.user.name, str(interaction.guild_id), f'Assunto: {assunto}', agora))
        self.conn.commit()

        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), interaction.user: discord.PermissionOverwrite(read_messages=True), guild.me: discord.PermissionOverwrite(read_messages=True)}
        canal = await guild.create_text_channel(nome_canal, overwrites=overwrites)
        
        embed = discord.Embed(title=f"🎫 Ticket: {assunto}", description=f"Olá {interaction.user.mention}, aguarde um membro da equipe.", color=self.bot.COR_TRAMA)
        await canal.send(content=interaction.user.mention, embed=embed, view=BotaoFecharTicket())
        await interaction.response.send_message(f"✅ Ticket criado em {canal.mention}", ephemeral=True)

class MenuAbrirTicket(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.select(placeholder="Selecione o tipo de atendimento", options=[discord.SelectOption(label="Dúvidas", value="Dúvidas"), discord.SelectOption(label="Suporte", value="Suporte"), discord.SelectOption(label="Produtos", value="Produtos")])
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        cog = interaction.client.get_cog("Suporte")
        await cog.criar_ticket(interaction, select.values[0])

class BotaoFecharTicket(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_fechar_v16")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Fechando...")
        await asyncio.sleep(3)
        await interaction.channel.delete()

async def setup(bot):
    await bot.add_cog(Suporte(bot))
