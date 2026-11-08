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
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS usernames (
                guild_id TEXT, user_id TEXT, custom_name TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS lives (
                guild_id TEXT, twitch_user TEXT, channel_id TEXT
            )
        ''')
        # NOVA TABELA: Tellonym
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tellonym_config (
                guild_id TEXT PRIMARY KEY,
                channel_id TEXT
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

    @tellonym_group.command(name="definir-canal", description="Define o canal onde as perguntas anônimas vão aparecer.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tellonym_canal(self, interaction: discord.Interaction, canal: discord.TextChannel):
        self.cursor.execute("INSERT OR REPLACE INTO tellonym_config VALUES (?, ?)", (str(interaction.guild_id), str(canal.id)))
        self.conn.commit()
        await interaction.response.send_message(f"✅ Canal de perguntas definido para {canal.mention}.", ephemeral=True)

    @tellonym_group.command(name="enviar", description="Envia uma pergunta anônima para o canal configurado.")
    @app_commands.describe(pergunta="O que você quer perguntar? (Sua identidade não será revelada)")
    async def tellonym_enviar(self, interaction: discord.Interaction, pergunta: str):
        # Busca o canal configurado
        self.cursor.execute("SELECT channel_id FROM tellonym_config WHERE guild_id = ?", (str(interaction.guild_id),))
        result = self.cursor.fetchone()
        
        if not result:
            await interaction.response.send_message("❌ O canal de perguntas não foi configurado. Avise a Staff.", ephemeral=True)
            return
            
        canal = self.bot.get_channel(int(result[0]))
        if not canal:
            await interaction.response.send_message("❌ O canal de perguntas foi deletado. Avise a Staff.", ephemeral=True)
            return

        # Cria o Embed anônimo
        embed = discord.Embed(
            description=f"**Anônimo:**\n{pergunta}",
            color=self.bot.COR_TRAMA
        )
        embed.set_footer(text="Tellonym • TRAMA")
        
        # Envia a mensagem no canal e cria uma Thread (Tópico) para comentários
        mensagem = await canal.send(embed=embed)
        thread = await mensagem.create_thread(name="Comentários", auto_archive_duration=1440)
        
        # Adiciona o autor original na thread para ele poder responder sem revelar quem é
        await thread.add_user(interaction.user)
        
        await interaction.response.send_message(f"✅ Sua pergunta foi enviada anonimamente! Você pode acompanhar os comentários na thread.", ephemeral=True)

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
        await interaction.response.send_message(f"✅ Monitorando a Twitch **{twitch}**. Avisos em {canal.mention}.", ephemeral=True)

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
        except Exception as e:
            print(f"Erro ao checar lives: {e}")

async def setup(bot):
    await bot.add_cog(Utilitarios(bot))
