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
        
        # Tabela para usernames
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS usernames (
                guild_id TEXT, user_id TEXT, custom_name TEXT
            )
        ''')
        # Tabela para lives
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS lives (
                guild_id TEXT, twitch_user TEXT, channel_id TEXT
            )
        ''')
        self.conn.commit()

        # Configuração da Twitch (Pegue as chaves em dev.twitch.tv)
        self.twitch_client_id = os.getenv("TWITCH_CLIENT_ID")
        self.twitch_secret = os.getenv("TWITCH_SECRET")
        self.twitch = None
        
        if self.twitch_client_id and self.twitch_secret:
            # Cria a conexão com a Twitch
            self.twitch = Twitch(self.twitch_client_id, self.twitch_secret)
            self.check_lives.start() # Inicia a verificação automática

    # --- COMANDO /USERNAMES ---
    @app_commands.command(name="usernames", description="Muda o seu apelido no servidor para um nome personalizado.")
    @app_commands.describe(nome="O nome que você quer usar")
    async def usernames(self, interaction: discord.Interaction, nome: str):
        try:
            # Muda o apelido da pessoa no servidor
            await interaction.user.edit(nick=nome)
            await interaction.response.send_message(f"✅ Seu apelido agora é **{nome}**.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Não tenho permissão para mudar seu apelido. Peça para a Staff colocar meu cargo acima do seu.", ephemeral=True)

    # --- COMANDO /TELLONYM ---
    @app_commands.command(name="tellonym", description="Envia uma pergunta anônima para o canal de perguntas.")
    @app_commands.describe(pergunta="O que você quer perguntar? (Sua identidade não será revelada)")
    async def tellonym(self, interaction: discord.Interaction, pergunta: str):
        # ATENÇÃO: Troque o ID abaixo pelo ID do seu canal de perguntas
        CANAL_PERGUNTAS_ID = 123456789012345678 
        
        canal = self.bot.get_channel(CANAL_PERGUNTAS_ID)
        if not canal:
            await interaction.response.send_message("❌ O canal de perguntas não foi configurado corretamente (ID inválido).", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="🕵️ Pergunta Anônima",
            description=pergunta,
            color=self.bot.COR_TRAMA
        )
        embed.set_footer(text="Tellonym • TRAMA")
        await canal.send(embed=embed)
        
        # Responde no privado para ninguém ver
        await interaction.response.send_message("✅ Sua pergunta foi enviada anonimamente no canal!", ephemeral=True)

    # --- COMANDO /LIVES (Configurar Twitch) ---
    @app_commands.command(name="lives", description="Configura um aviso quando alguém começar uma live na Twitch.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(twitch="O nome do canal na Twitch", canal="O canal do Discord onde quer receber o aviso")
    async def lives(self, interaction: discord.Interaction, twitch: str, canal: discord.TextChannel):
        if not self.twitch:
            await interaction.response.send_message("❌ O dono do bot não configurou as chaves da API da Twitch (TWITCH_CLIENT_ID e TWITCH_SECRET).", ephemeral=True)
            return

        self.cursor.execute("INSERT INTO lives VALUES (?, ?, ?)", (str(interaction.guild_id), twitch.lower(), str(canal.id)))
        self.conn.commit()
        
        await interaction.response.send_message(f"✅ Monitorando a Twitch **{twitch}**. Avisos serão enviados em {canal.mention}.", ephemeral=True)

    # --- LOOP QUE VERIFICA AS LIVES A CADA 5 MINUTOS ---
    @tasks.loop(minutes=5)
    async def check_lives(self):
        if not self.twitch: return
        
        self.cursor.execute("SELECT guild_id, twitch_user, channel_id FROM lives")
        lives = self.cursor.fetchall()
        
        if not lives: return

        try:
            # Pega a lista de usuários da Twitch que estão online
            nomes_twitch = [linha[1] for linha in lives]
            users_info = self.twitch.get_users(logins=nomes_twitch)
            
            for user in users_info['data']:
                # Verifica se o usuário está transmitindo
                streams = self.twitch.get_streams(user_login=user['login'])
                if streams['data']:
                    stream_info = streams['data'][0]
                    
                    # Encontra no banco qual canal do Discord deve receber o aviso
                    for linha in lives:
                        if linha[1] == user['login']:
                            canal = self.bot.get_channel(int(linha[2]))
                            if canal:
                                # Evita mandar spam (verifica se já avisou recentemente)
                                # Numa versão mais avançada, guardaríamos o ID da live no banco
                                embed = discord.Embed(
                                    title=f"🔴 {user['display_name']} está ao vivo!",
                                    description=f"**Jogando:** {stream_info['game_name']}\n**Título:** {stream_info['title']}",
                                    url=f"https://twitch.tv/{user['login']}",
                                    color=0x9146FF # Cor da Twitch
                                )
                                embed.set_image(url=stream_info['thumbnail_url'].replace("{width}", "640").replace("{height}", "360"))
                                await canal.send(embed=embed)
        except Exception as e:
            print(f"Erro ao checar lives na Twitch: {e}")

async def setup(bot):
    await bot.add_cog(Utilitarios(bot))
