import discord
from discord import app_commands
from discord.ext import commands
from sonora import SonoraClient
import os

class Musica(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Configura a conexão com o servidor Lavalink
        # Você precisará substituir o 'host' pelo endereço do seu Lavalink (se for externo)
        self.sonora = SonoraClient(
            lavalink_nodes=[{
                "host": os.getenv("LAVALINK_HOST", "127.0.0.1"), 
                "port": int(os.getenv("LAVALINK_PORT", 2333)), 
                "password": os.getenv("LAVALINK_PASSWORD", "youshallnotpass")
            }],
            node_pooling=True,
            reconnect_policy={"max_retries": 5, "backoff": "exponential"}
        )

    async def cog_load(self):
        # Inicia a conexão com o Lavalink quando o módulo for carregado
        await self.sonora.start()
        print("🎵 Módulo de música conectado ao Lavalink.")

    async def cog_unload(self):
        # Fecha a conexão ao descarregar o módulo
        await self.sonora.close()

    @app_commands.command(name="play", description="Toca uma música do YouTube, Spotify ou SoundCloud.")
    @app_commands.describe(busca="Nome da música ou link")
    async def play(self, interaction: discord.Interaction, busca: str):
        # Verifica se o usuário está em um canal de voz
        if not interaction.user.voice:
            await interaction.response.send_message("❌ Você precisa estar em um canal de voz para usar este comando.", ephemeral=True)
            return

        await interaction.response.defer()

        canal = interaction.user.voice.channel
        
        # Conecta ao canal de voz se o bot ainda não estiver nele
        if not interaction.guild.voice_client:
            try:
                await canal.connect()
            except Exception as e:
                await interaction.followup.send(f"❌ Erro ao conectar no canal de voz: {e}")
                return

        # Obtém o player do Sonora para este servidor
        player = await self.sonora.get_player(interaction.guild.id)
        
        try:
            # Toca a música (o Sonora busca a fonte automaticamente)
            track = await player.play(busca)
            await interaction.followup.send(f"🎶 Tocando agora: **{track.title}**")
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao buscar/tocar a música: {e}")

    @app_commands.command(name="skip", description="Pula para a próxima música da fila.")
    async def skip(self, interaction: discord.Interaction):
        player = await self.sonora.get_player(interaction.guild.id)
        if player and player.current:
            await player.skip()
            await interaction.response.send_message("⏭️ Música pulada.")
        else:
            await interaction.response.send_message("❌ Não há música tocando no momento.", ephemeral=True)

    @app_commands.command(name="stop", description="Para a música e limpa a fila.")
    async def stop(self, interaction: discord.Interaction):
        player = await self.sonora.get_player(interaction.guild.id)
        if player:
            await player.stop()
            if interaction.guild.voice_client:
                await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("⏹️ Música parada e bot desconectado.")
        else:
            await interaction.response.send_message("❌ Não há música tocando.", ephemeral=True)

    @app_commands.command(name="pause", description="Pausa a música atual.")
    async def pause(self, interaction: discord.Interaction):
        player = await self.sonora.get_player(interaction.guild.id)
        if player and player.current:
            await player.pause()
            await interaction.response.send_message("⏸️ Música pausada.")
        else:
            await interaction.response.send_message("❌ Não há música tocando.", ephemeral=True)

    @app_commands.command(name="resume", description="Retoma a música pausada.")
    async def resume(self, interaction: discord.Interaction):
        player = await self.sonora.get_player(interaction.guild.id)
        if player and player.current:
            await player.resume()
            await interaction.response.send_message("▶️ Música retomada.")
        else:
            await interaction.response.send_message("❌ Não há música pausada.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Musica(bot))
