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
        
        # Tabelas de Automação
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
    # COMANDO: /gatilhos (Respostas Automáticas)
    # ==========================================
    @app_commands.command(name="gatilhos", description="Cria uma resposta automática quando alguém falar uma palavra.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(palavra="A palavra que vai ativar o gatilho", resposta="O que o bot deve responder")
    async def gatilhos(self, interaction: discord.Interaction, palavra: str, resposta: str):
        self.cursor.execute("INSERT INTO gatilhos VALUES (?, ?, ?)", (str(interaction.guild_id), palavra.lower(), resposta))
        self.conn.commit()
        await interaction.response.send_message(f"✅ Gatilho criado! Se alguém falar `{palavra}`, eu respondo `{resposta}`.", ephemeral=True)

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
    # COMANDO: /figurinhas (Sistema de Stickers)
    # ==========================================
    @app_commands.command(name="figurinhas", description="Mostra as figurinhas (stickers) disponíveis no servidor.")
    async def figurinhas(self, interaction: discord.Interaction):
        stickers = interaction.guild.stickers
        if not stickers:
            await interaction.response.send_message("❌ Este servidor não tem figurinhas personalizadas.", ephemeral=True)
            return
            
        embed = discord.Embed(title="🎨 Figurinhas do Servidor", color=self.bot.COR_TRAMA)
        for sticker in stickers[:5]: # Mostra as 5 primeiras
            embed.add_field(name=sticker.name, value=f"ID: `{sticker.id}`", inline=False)
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==========================================
    # COMANDO: /banner-contador (Banner Dinâmico)
    # ==========================================
    @app_commands.command(name="banner-contador", description="Cria um banner dinâmico com a contagem de membros no seu perfil.")
    @app_commands.checks.has_permissions(administrator=True)
    async def banner_contador(self, interaction: discord.Interaction):
        # O Discord exige que o link da imagem seja gerado por uma API externa para ser dinâmico.
        # Aqui usamos um serviço de exemplo de gerador de banners.
        guild = interaction.guild
        membros = guild.member_count
        
        # Cria um link fictício de API (você precisaria de um serviço real para isso funcionar 100%)
        url_banner = f"https://api.example.com/banner?text=TRAMA+{membros}+Membros"
        
        embed = discord.Embed(title="🖼️ Banner Contador", color=self.bot.COR_TRAMA)
        embed.description = f"Para usar no seu perfil, coloque este link na sua bio:\n`{url_banner}`\n\n*(Nota: Requer um serviço externo de geração de imagens para funcionar 100%)*"
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==========================================
    # COMANDO: /valorant-tracker (Estatísticas)
    # ==========================================
    @app_commands.command(name="valorant-tracker", description="Mostra as estatísticas de um jogador de Valorant.")
    @app_commands.describe(nome="Nome de usuário (ex: TenZ#NA1)")
    async def valorant_tracker(self, interaction: discord.Interaction, nome: str):
        await interaction.response.defer()
        
        # Usa a API pública e gratuita do valorant-api.com (HenrikDev API)
        # Formato esperado: Nome#TAG
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
            
            embed = discord.Embed(title=f"🎯 Valorant: {nome}", color=0xFF4655) # Vermelho Valorant
            embed.add_field(name="Rank Atual", value=f"**{elo}**", inline=True)
            embed.add_field(name="Pontos (RR)", value=f"**{pontos}**", inline=True)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao ler os dados: {e}")

    # ==========================================
    # EVENTO: OUVIR AS MENSAGENS PARA GATILHOS
    # ==========================================
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        guild_id = str(message.guild.id)
        content = message.content.lower()

        # Verifica Gatilhos (Respostas)
        self.cursor.execute("SELECT palavra, resposta FROM gatilhos WHERE guild_id = ?", (guild_id,))
        for palavra, resposta in self.cursor.fetchall():
            if palavra in content:
                await message.reply(resposta)
                break # Para não mandar várias respostas de uma vez

        # Verifica Reações Automáticas
        self.cursor.execute("SELECT palavra, emoji FROM reacoes_auto WHERE guild_id = ?", (guild_id,))
        for palavra, emoji in self.cursor.fetchall():
            if palavra in content:
                try:
                    await message.add_reaction(emoji)
                except:
                    pass

async def setup(bot):
    await bot.add_cog(Automacao(bot))
