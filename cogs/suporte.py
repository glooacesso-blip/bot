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

    @app_commands.command(name="painel-ticket", description="Cria um painel de atendimento personalizado.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        titulo="Título do painel",
        descricao="O texto que vai dentro do painel",
        texto_botao="O que vai escrito no botão verde (ex: Abrir Ticket)",
        cor="Cor da barra lateral (Vermelho, Preto, Azul, Verde, Roxo, Amarelo)",
        imagem="Link da imagem do banner (opcional)"
    )
    async def painel_ticket(self, interaction: discord.Interaction, titulo: str, descricao: str, texto_botao: str, cor: str, imagem: str = None):
        
        # Mapeamento de cores
        cores = {
            "vermelho": discord.Color.red(),
            "preto": discord.Color.from_rgb(0, 0, 0),
            "azul": discord.Color.blue(),
            "verde": discord.Color.green(),
            "roxo": discord.Color.purple(),
            "amarelo": discord.Color.gold(),
            "trama": discord.Color.from_rgb(139, 0, 0) # Vermelho escuro
        }
        
        # Define a cor (padrão é a cor da TRAMA se digitar errado)
        cor_escolhida = cores.get(cor.lower(), self.bot.COR_TRAMA)

        embed = discord.Embed(
            title=titulo,
            description=descricao,
            color=cor_escolhida
        )
        
        if imagem:
            embed.set_image(url=imagem)
            
        embed.set_footer(text="TRAMA • Segurança e Acolhimento")
        
        await interaction.response.send_message("Painel criado com sucesso!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=BotaoAbrirTicket(texto_botao=texto_botao))

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
    def __init__(self, texto_botao: str):
        super().__init__(timeout=None)
        # Atualiza o texto do botão dinamicamente
        self.children[0].label = texto_botao

    @discord.ui.button(label="Iniciar Atendimento", style=discord.ButtonStyle.success, emoji="🎗️", custom_id="btn_abrir_v4")
    async def abrir(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("Suporte")
        await cog.criar_ticket(interaction)

class BotaoFecharTicket(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_fechar_v4")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Fechando...")
        await asyncio.sleep(3)
        await interaction.channel.delete()

async def setup(bot):
    await bot.add_cog(Suporte(bot))
