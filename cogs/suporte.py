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
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT, user_name TEXT, guild_name TEXT, channel_name TEXT, created_at TEXT, assunto TEXT
            )
        ''')
        self.conn.commit()

    # --- COMANDO PARA ENVIAR O PAINEL DE TICKETS ---
    @app_commands.command(name="painel-ticket", description="Envia o painel de atendimento com menu de opções.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(imagem="Link do banner do painel (Opcional)")
    async def painel_ticket(self, interaction: discord.Interaction, imagem: str = None):
        
        embed = discord.Embed(
            title="🎫 Central de Atendimento",
            description="Por favor, selecione abaixo o motivo do seu contato para que possamos te ajudar da melhor forma possível.",
            color=self.bot.COR_TRAMA
        )
        
        if imagem:
            embed.set_image(url=imagem)
            
        embed.set_footer(text="Surf Trama • Suporte")
        
        await interaction.response.send_message("Painel criado com sucesso!", ephemeral=True)
        # Envia a mensagem com o Menu Suspenso
        await interaction.channel.send(embed=embed, view=MenuAbrirTicket())

    # --- FUNÇÃO QUE CRIA O CANAL DO TICKET ---
    async def criar_ticket(self, interaction: discord.Interaction, assunto: str):
        guild = interaction.guild
        
        # Limpa o nome do assunto para virar o nome do canal
        nome_limpo = assunto.lower().replace(" ", "-").replace("ó", "o").replace("í", "i").replace("é", "e").replace("ç", "c")
        nome_canal = f"ticket-{interaction.user.name.lower()}"
        
        # Verifica se a pessoa já tem um ticket aberto
        canal_existente = discord.utils.get(guild.text_channels, name=nome_canal)
        if canal_existente:
            await interaction.response.send_message(f"❌ Você já tem um ticket aberto: {canal_existente.mention}", ephemeral=True)
            return

        # Cria o canal privado
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        canal = await guild.create_text_channel(nome_canal, overwrites=overwrites)
        
        # Salva no banco de dados
        agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        self.cursor.execute(
            "INSERT INTO tickets (user_id, user_name, guild_name, channel_name, created_at, assunto) VALUES (?, ?, ?, ?, ?, ?)",
            (str(interaction.user.id), str(interaction.user.name), str(guild.name), str(canal.name), agora, assunto)
        )
        self.conn.commit()

        # Envia a mensagem dentro do ticket
        embed = discord.Embed(
            title=f"🎫 Ticket: {assunto}",
            description=f"Olá {interaction.user.mention}, obrigado por entrar em contato.\n\n**Assunto:** {assunto}\n\nPor favor, descreva seu problema ou dúvida abaixo e aguarde um membro da equipe.",
            color=self.bot.COR_TRAMA
        )
        embed.set_footer(text="Para fechar o ticket, clique no botão abaixo.")
        
        await canal.send(content=interaction.user.mention, embed=embed, view=BotaoFecharTicket())
        await interaction.response.send_message(f"✅ Ticket criado em {canal.mention}", ephemeral=True)


# --- MENU SUSPENSO (DROPDOWN) ---
class MenuAbrirTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
        # Aqui você adiciona as opções que quiser
        opcoes = [
            discord.SelectOption(label="Dúvidas", description="Perguntas, orientações e informações gerais", emoji="❓", value="Dúvidas"),
            discord.SelectOption(label="Suporte Técnico", description="Erros, bugs ou problemas técnicos", emoji="🎧", value="Suporte Técnico"),
            discord.SelectOption(label="Receber Produtos", description="Pedidos, entregas e acompanhamento", emoji="🚚", value="Receber Produtos")
        ]
        
        self.menu = discord.ui.Select(placeholder="Selecione o tipo de atendimento", options=opcoes)
        self.menu.callback = self.menu_callback
        self.add_item(self.menu)

    async def menu_callback(self, interaction: discord.Interaction):
        assunto_escolhido = self.menu.values[0]
        cog = interaction.client.get_cog("Suporte")
        await cog.criar_ticket(interaction, assunto_escolhido)

# --- BOTÃO DE FECHAR TICKET ---
class BotaoFecharTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_fechar_ticket_v6")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Fechando ticket em 5 segundos...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

async def setup(bot):
    await bot.add_cog(Suporte(bot))
