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
        self.conn = sqlite3.connect('tickets.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT, user_name TEXT, guild_name TEXT, channel_name TEXT, created_at TEXT
            )
        ''')
        self.conn.commit()

    @app_commands.command(name="painel-ticket", description="Cria o painel de atendimento (já vem configurado com o visual TRAMA).")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        imagem="Link da imagem do banner (Opcional. Se não colocar, usará o padrão).",
        titulo="Título do painel (Opcional. Padrão: CENTRAL DE AJUDA)",
        texto_botao="Texto do botão (Opcional. Padrão: Abrir Ticket)"
    )
    async def painel_ticket(self, interaction: discord.Interaction, imagem: str = None, titulo: str = "CENTRAL DE AJUDA E ACOLHIMENTO", texto_botao: str = "Abrir Ticket"):
        
        # Texto padrão bonito
        texto = (
            "Estamos aqui para acolher e ajudar no que precisar. Este é um espaço seguro, onde você pode falar abertamente, sem julgamentos.\n\n"
            "Se preferir, também podemos conversar por call, às vezes falar é mais leve do que escrever. Quando se sentir à vontade, é só chamar!\n\n"
            "Estamos com você."
        )
        
        embed = discord.Embed(
            title=titulo,
            description=texto,
            color=self.bot.COR_TRAMA # Sempre Vermelho Escuro
        )
        
        # Se você colocar o link da imagem, ele adiciona
        if imagem:
            embed.set_image(url=imagem)
            
        embed.set_footer(text="TRAMA • Segurança e Acolhimento")
        
        await interaction.response.send_message("Painel criado com sucesso!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=BotaoAbrirTicket(texto_botao))

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
        
        agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        self.cursor.execute(
            "INSERT INTO tickets (user_id, user_name, guild_name, channel_name, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(interaction.user.id), str(interaction.user.name), str(guild.name), str(canal.name), agora)
        )
        self.conn.commit()

        embed = discord.Embed(title="🎫 Ticket Aberto", description=f"Olá {interaction.user.mention}, a equipe foi notificada.\nDescreva o que precisa abaixo.", color=self.bot.COR_TRAMA)
        await canal.send(embed=embed, view=BotaoFecharTicket())
        await interaction.response.send_message(f"✅ Ticket criado em {canal.mention}", ephemeral=True)

class BotaoAbrirTicket(discord.ui.View):
    def __init__(self, texto_botao: str):
        super().__init__(timeout=None)
        self.children[0].label = texto_botao

    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.success, emoji="🎗️", custom_id="btn_abrir_v5")
    async def abrir(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("Suporte")
        await cog.criar_ticket(interaction)

class BotaoFecharTicket(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_fechar_v5")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Fechando...")
        await asyncio.sleep(3)
        await interaction.channel.delete()

async def setup(bot):
    await bot.add_cog(Suporte(bot))
