import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import asyncio
import aiohttp

class Automacao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('tickets.db')
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS gatilhos (
                guild_id TEXT, palavra TEXT, resposta TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS reacoes_auto (
                guild_id TEXT, palavra TEXT, emoji TEXT
            )
        ''')
        self.conn.commit()

    # ==========================================
    # GRUPO DE COMANDOS: /gatilhos
    # ==========================================
    gatilhos_group = app_commands.Group(name="gatilhos", description="Gerencia as respostas automáticas do bot.")

    @gatilhos_group.command(name="adicionar", description="Cria uma resposta automática quando alguém falar uma palavra.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(palavra="A palavra que vai ativar o gatilho", resposta="O que o bot deve responder")
    async def gatilhos_adicionar(self, interaction: discord.Interaction, palavra: str, resposta: str):
        self.cursor.execute("INSERT INTO gatilhos VALUES (?, ?, ?)", (str(interaction.guild_id), palavra.lower(), resposta))
        self.conn.commit()
        await interaction.response.send_message(f"✅ Gatilho criado! Se alguém falar `{palavra}`, eu respondo `{resposta}`.", ephemeral=True)

    @gatilhos_group.command(name="remover", description="Remove uma resposta automática.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(palavra="A palavra do gatilho que você quer remover")
    async def gatilhos_remover(self, interaction: discord.Interaction, palavra: str):
        self.cursor.execute("DELETE FROM gatilhos WHERE guild_id = ? AND palavra = ?", (str(interaction.guild_id), palavra.lower()))
        self.conn.commit()
        
        if self.cursor.rowcount > 0:
            await interaction.response.send_message(f"✅ Gatilho da palavra `{palavra}` removido com sucesso!", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Nenhum gatilho encontrado para a palavra `{palavra}`.", ephemeral=True)

    @gatilhos_group.command(name="listar", description="Mostra todos os gatilhos ativos no servidor.")
    @app_commands.checks.has_permissions(administrator=True)
    async def gatilhos_listar(self, interaction: discord.Interaction):
        self.cursor.execute("SELECT palavra, resposta FROM gatilhos WHERE guild_id = ?", (str(interaction.guild_id),))
        gatilhos = self.cursor.fetchall()
        
        if not gatilhos:
            await interaction.response.send_message("❌ Nenhum gatilho configurado neste servidor.", ephemeral=True)
            return
            
        embed = discord.Embed(title="⚙️ Gatilhos Automáticos", color=self.bot.COR_TRAMA)
        for palavra, resposta in gatilhos:
            embed.add_field(name=f"Palavra: {palavra}", value=f"Resposta: {resposta}", inline=False)
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==========================================
    # COMANDO: /reacoes-automaticas
    # ==========================================
    @app_commands.command(name="reacoes-automaticas", description="O bot reage automaticamente a uma palavra.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(palavra="A palavra que vai ativar a reação", emoji="O emoji que o bot vai reagir")
    async def reacoes_automaticas(self, interaction: discord.Interaction, palavra: str, emoji: str):
        self.cursor.execute("INSERT INTO reacoes_auto VALUES (?, ?, ?)", (str(interaction.guild_id), palavra.lower(), emoji))
        self.conn.commit()
        await interaction.response.send_message(f"✅ Reação criada! Quando alguém falar `{palavra}`, eu reajo com {emoji}.", ephemeral=True)

    # ==========================================
    # COMANDO: /figurinhas
    # ==========================================
    @app_commands.command(name="figurinhas", description="Mostra as figurinhas disponíveis no servidor.")
    async def figurinhas(self, interaction: discord.Interaction):
        stickers = interaction.guild.stickers
        if not stickers:
            await interaction.response.send_message("❌ Este servidor não tem figurinhas personalizadas.", ephemeral=True)
            return
        embed = discord.Embed(title="🎨 Figurinhas do Servidor", color=self.bot.COR_TRAMA)
        for sticker in stickers[:5]:
            embed.add_field(name=sticker.name, value=f"ID: `{sticker.id}`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==========================================
    # COMANDO: /valorant-tracker
    # ==========================================
    @app_commands.command(name="valorant-tracker", description="Mostra as estatísticas de um jogador de Valorant.")
    @app_commands.describe(nome="Nome de usuário (ex: TenZ#NA1)")
    async def valorant_tracker(self, interaction: discord.Interaction, nome: str):
        await interaction.response.defer()
        if "#" not in nome:
            await interaction.followup.send("❌ O nome deve estar no formato `Nome#TAG` (ex: TenZ#NA1).")
            return
        nome_formatado = nome.replace("#", "/")
        url = f"https://api.henrikdev.xyz/valorant/v1/mmr/na/{nome_formatado}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    await interaction.followup.send("❌ Jogador não encontrado ou API indisponível.")
                    return
                data = await response.json()
                
        try:
            elo = data["data"]["currenttierpatched"]
            pontos = data["data"]["ranking_in_tier"]
            embed = discord.Embed(title=f"🎯 Valorant: {nome}", color=0xFF4655)
            embed.add_field(name="Rank Atual", value=f"**{elo}**", inline=True)
            embed.add_field(name="Pontos (RR)", value=f"**{pontos}**", inline=True)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao ler os dados: {e}")

    # ==========================================
    # EVENTO: OUVIR AS MENSAGENS (Gatilhos e Reações)
    # ==========================================
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        guild_id = str(message.guild.id)
        content = message.content.lower()

        # Verifica Gatilhos
        self.cursor.execute("SELECT palavra, resposta FROM gatilhos WHERE guild_id = ?", (guild_id,))
        for palavra, resposta in self.cursor.fetchall():
            if palavra in content:
                await message.reply(resposta)
                break # Para não mandar várias respostas

        # Verifica Reações
        self.cursor.execute("SELECT palavra, emoji FROM reacoes_auto WHERE guild_id = ?", (guild_id,))
        for palavra, emoji in self.cursor.fetchall():
            if palavra in content:
                try: await message.add_reaction(emoji)
                except: pass

async def setup(bot):
    await bot.add_cog(Automacao(bot))
