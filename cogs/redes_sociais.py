import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlite3
import asyncio
import os
import yt_dlp
import tweepy
from instagram_to_discord import DiscordInstagramPoster

class RedesSociais(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('tickets.db')
        self.cursor = self.conn.cursor()
        
        # Tabelas para lives e usernames
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS lives (
                guild_id TEXT, user_id TEXT, platform TEXT, channel_id TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS usernames (
                guild_id TEXT, user_id TEXT, custom_name TEXT
            )
        ''')
        self.conn.commit()

    # --- COMANDO /TELLONYM (Caixa de Perguntas Anônimas) ---
    @app_commands.command(name="tellonym", description="Envia uma pergunta anônima para um canal específico.")
    @app_commands.describe(pergunta="O que você quer perguntar? (Sua identidade não será revelada)")
    async def tellonym(self, interaction: discord.Interaction, pergunta: str):
        # Canal onde as perguntas vão cair (troque o ID pelo seu)
        CANAL_ID = 123456789012345678 
        canal = self.bot.get_channel(CANAL_ID)
        
        if not canal:
            await interaction.response.send_message("❌ Canal de perguntas não configurado.", ephemeral=True)
            return
            
        embed = discord.Embed(title="🕵️ Pergunta Anônima", description=pergunta, color=self.bot.COR_TRAMA)
        embed.set_footer(text="Tellonym • TRAMA")
        await canal.send(embed=embed)
        await interaction.response.send_message("✅ Sua pergunta foi enviada anonimamente!", ephemeral=True)

    # --- COMANDO /LIVES (Notificar quando alguém estiver em live) ---
    @app_commands.command(name="lives", description="Configura um canal para receber notificações de live (Twitch/YouTube).")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(usuario="Quem você quer monitorar", plataforma="Twitch ou YouTube", canal_notificacao="Onde avisar")
    async def lives(self, interaction: discord.Interaction, usuario: discord.Member, plataforma: str, canal_notificacao: discord.TextChannel):
        self.cursor.execute("INSERT INTO lives VALUES (?, ?, ?, ?)", (str(interaction.guild_id), str(usuario.id), plataforma, str(canal_notificacao.id)))
        self.conn.commit()
        await interaction.response.send_message(f"✅ Monitorando **{usuario.name}** na **{plataforma}**. Avisos em {canal_notificacao.mention}.", ephemeral=True)

    # --- COMANDO /DOWNLOADER-VIDEO (Baixar vídeos) ---
    @app_commands.command(name="downloader-video", description="Baixa um vídeo do YouTube, TikTok ou Instagram.")
    @app_commands.describe(url="Cole o link do vídeo")
    async def downloader_video(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer()
        
        # Configurações do yt-dlp para pegar o melhor vídeo em mp4
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': 'video.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
            # Envia o arquivo para o Discord
            await interaction.followup.send(file=discord.File(filename))
            
            # Apaga o arquivo do servidor após enviar
            os.remove(filename)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao baixar: O link pode ser inválido ou muito grande. Erro: {e}")

    # --- COMANDO /USERNAMES (Sistema de Nomes Personalizados) ---
    @app_commands.command(name="usernames", description="Define um nome personalizado para você no servidor.")
    @app_commands.describe(nome="O nome que você quer usar")
    async def usernames(self, interaction: discord.Interaction, nome: str):
        self.cursor.execute("INSERT OR REPLACE INTO usernames VALUES (?, ?, ?)", (str(interaction.guild_id), str(interaction.user.id), nome))
        self.conn.commit()
        await interaction.response.send_message(f"✅ Seu nome personalizado agora é **{nome}**.", ephemeral=True)

# --- TAREFA DE FUNDO PARA VERIFICAR LIVES ---
    @tasks.loop(minutes=5)
    async def check_lives(self):
        # Aqui você precisaria de APIs da Twitch/YouTube para verificar se a pessoa está online.
        # Como é complexo, deixei um exemplo de como seria a lógica.
        print("Verificando lives... (Necessário configurar API)")
        
async def setup(bot):
    await bot.add_cog(RedesSociais(bot))
