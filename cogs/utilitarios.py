import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlite3
import os
from twitchAPI.twitch import Twitch

class Utilitarios(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('tickets.db')
        self.cursor = self.conn.cursor()
        
        # Tabelas
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS usernames (guild_id TEXT, user_id TEXT, custom_name TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS lives (guild_id TEXT, twitch_user TEXT, channel_id TEXT)''')
        
        # NOVA TABELA: Configuração do Tellonym
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tellonym_config (
                guild_id TEXT PRIMARY KEY,
                channel_envio TEXT,
                channel_aprovacao TEXT,
                role_aprovadora TEXT
            )
        ''')
        self.conn.commit()

        # Configuração da Twitch
        self.twitch_client_id = os.getenv("TWITCH_CLIENT_ID")
        self.twitch_secret = os.getenv("TWITCH_SECRET")
        self.twitch = None
        
        if self.twitch_client_id and self.twitch_secret:
            self.twitch = Twitch(self.twitch_client_id, self.twitch_secret)
            self.check_lives.start()

    # ==========================================
    # COMANDO: /usernames
    # ==========================================
    @app_commands.command(name="usernames", description="Muda o seu apelido no servidor.")
    @app_commands.describe(nome="O nome que você quer usar")
    async def usernames(self, interaction: discord.Interaction, nome: str):
        try:
            await interaction.user.edit(nick=nome)
            await interaction.response.send_message(f"✅ Seu apelido agora é **{nome}**.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Não tenho permissão para mudar seu apelido.", ephemeral=True)

    # ==========================================
    # GRUPO DE COMANDOS: /tellonym
    # ==========================================
    tellonym_group = app_commands.Group(name="tellonym", description="Sistema de perguntas anônimas.")

    @tellonym_group.command(name="configurar", description="Configura os canais e o cargo de aprovação do Tellonym.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tellonym_configurar(self, interaction: discord.Interaction, canal_envio: discord.TextChannel, canal_aprovacao: discord.TextChannel, cargo_staff: discord.Role):
        self.cursor.execute("INSERT OR REPLACE INTO tellonym_config VALUES (?, ?, ?, ?)", (str(interaction.guild_id), str(canal_envio.id), str(canal_aprovacao.id), str(cargo_staff.id)))
        self.conn.commit()
        await interaction.response.send_message(f"✅ Configurado!\n**Envio:** {canal_envio.mention}\n**Aprovação:** {canal_aprovacao.mention}\n**Cargo Staff:** {cargo_staff.mention}", ephemeral=True)

    @tellonym_group.command(name="painel", description="Cria a mensagem com o botão 'Enviar Tellonym' no canal atual.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tellonym_painel(self, interaction: discord.Interaction, imagem: str = None):
        embed = discord.Embed(
            title="📨 Envie uma mensagem anônima!",
            description="Clique no botão abaixo para enviar sua mensagem de forma 100% anônima. A Staff irá avaliar antes de ser publicada.",
            color=self.bot.COR_TRAMA
        )
        if imagem: embed.set_image(url=imagem)
            
        await interaction.response.send_message("Painel criado!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=BotaoAbrirTellonym())

    # ==========================================
    # COMANDO: /lives
    # ==========================================
    @app_commands.command(name="lives", description="Configura um aviso quando alguém começar uma live na Twitch.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(twitch="O nome do canal na Twitch", canal="O canal do Discord onde quer receber o aviso")
    async def lives(self, interaction: discord.Interaction, twitch: str, canal: discord.TextChannel):
        if not self.twitch:
            await interaction.response.send_message("❌ O dono do bot não configurou as chaves da API da Twitch.", ephemeral=True)
            return
        self.cursor.execute("INSERT INTO lives VALUES (?, ?, ?)", (str(interaction.guild_id), twitch.lower(), str(canal.id)))
        self.conn.commit()
        await interaction.response.send_message(f"✅ Monitorando a Twitch **{twitch}**.", ephemeral=True)

    @tasks.loop(minutes=5)
    async def check_lives(self):
        if not self.twitch: return
        self.cursor.execute("SELECT guild_id, twitch_user, channel_id FROM lives")
        lives = self.cursor.fetchall()
        if not lives: return
        try:
            nomes_twitch = [linha[1] for linha in lives]
            users_info = self.twitch.get_users(logins=nomes_twitch)
            for user in users_info['data']:
                streams = self.twitch.get_streams(user_login=user['login'])
                if streams['data']:
                    stream_info = streams['data'][0]
                    for linha in lives:
                        if linha[1] == user['login']:
                            canal = self.bot.get_channel(int(linha[2]))
                            if canal:
                                embed = discord.Embed(title=f"🔴 {user['display_name']} está ao vivo!", description=f"**Jogando:** {stream_info['game_name']}\n**Título:** {stream_info['title']}", url=f"https://twitch.tv/{user['login']}", color=0x9146FF)
                                embed.set_image(url=stream_info['thumbnail_url'].replace("{width}", "640").replace("{height}", "360"))
                                await canal.send(embed=embed)
        except Exception as e: print(f"Erro ao checar lives: {e}")


# ==========================================
# BOTÃO DO PAINEL (ABRIR O MODAL)
# ==========================================
class BotaoAbrirTellonym(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Enviar Tellonym", style=discord.ButtonStyle.primary, emoji="📨", custom_id="btn_tellonym_abrir")
    async def abrir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalTellonym())

# ==========================================
# MODAL (O FORMULÁRIO QUE ABRE)
# ==========================================
class ModalTellonym(discord.ui.Modal, title="Sistema de Tellonym"):
    def __init__(self):
        super().__init__()
        
    mensagem = discord.ui.TextInput(
        label="Mensagem",
        style=discord.TextStyle.paragraph,
        placeholder="Digite a mensagem que você quer enviar...",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Utilitarios")
        
        # Busca as configurações no banco
        cog.cursor.execute("SELECT channel_aprovacao, role_aprovadora FROM tellonym_config WHERE guild_id = ?", (str(interaction.guild_id),))
        result = cog.cursor.fetchone()
        
        if not result:
            await interaction.response.send_message("❌ O sistema de Tellonym não foi configurado corretamente. Avise a Staff.", ephemeral=True)
            return
            
        canal_aprovacao_id, cargo_staff_id = result
        canal = interaction.guild.get_channel(int(canal_aprovacao_id))
        
        if not canal:
            await interaction.response.send_message("❌ O canal de aprovação não existe mais. Avise a Staff.", ephemeral=True)
            return

        # Cria o Embed de Aprovação
        embed = discord.Embed(
            title="📥 Novo Tellonym para Aprovação",
            description=f"**Mensagem:**\n{self.mensagem.value}",
            color=discord.Color.yellow()
        )
        embed.set_footer(text="Use os botões abaixo para aprovar ou reprovar.")

        # Envia no canal de aprovação, marcando o cargo da staff
        await canal.send(content=f"<@&{cargo_staff_id}>", embed=embed, view=BotaoAprovarTellonym(interaction.user.id, self.mensagem.value))
        
        await interaction.response.send_message("✅ Sua mensagem foi enviada para a Staff avaliar!", ephemeral=True)


# ==========================================
# BOTÕES DE APROVAÇÃO (NA STAFF)
# ==========================================
class BotaoAprovarTellonym(discord.ui.View):
    def __init__(self, autor_id, mensagem):
        super().__init__(timeout=None)
        self.autor_id = autor_id
        self.mensagem = mensagem

    @discord.ui.button(label="Aprovar", style=discord.ButtonStyle.success, emoji="✅", custom_id="btn_aprovar")
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("Utilitarios")
        cog.cursor.execute("SELECT channel_envio FROM tellonym_config WHERE guild_id = ?", (str(interaction.guild_id),))
        result = cog.cursor.fetchone()
        
        if not result:
            await interaction.response.send_message("❌ Canal de envio não configurado.", ephemeral=True)
            return
            
        canal_envio = interaction.guild.get_channel(int(result[0]))
        
        # Cria o Embed bonito para o canal público
        embed = discord.Embed(description=f"**Anônimo:**\n{self.mensagem}", color=cog.bot.COR_TRAMA)
        embed.set_footer(text="Tellonym • TRAMA")
        
        # Envia no público e cria a Thread
        mensagem_publica = await canal_envio.send(embed=embed)
        thread = await mensagem_publica.create_thread(name="Comentários", auto_archive_duration=1440)
        
        # Tenta adicionar o autor original na thread (para ele ver os comentários)
        try:
            autor = await interaction.guild.fetch_member(self.autor_id)
            if autor: await thread.add_user(autor)
        except: pass
        
        await interaction.response.send_message("✅ Tellonym aprovado e publicado!", ephemeral=True)
        self.stop() # Desativa os botões

    @discord.ui.button(label="Reprovar", style=discord.ButtonStyle.danger, emoji="❌", custom_id="btn_reprovar")
    async def reprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ Tellonym reprovado e removido.", ephemeral=True)
        await interaction.message.delete() # Apaga a mensagem do canal de aprovação

    @discord.ui.button(label="Adicionar Comentário", style=discord.ButtonStyle.primary, emoji="💬", custom_id="btn_comentar_staff")
    async def comentar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("💬 A Staff pode adicionar comentários abaixo desta mensagem.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Utilitarios(bot))
