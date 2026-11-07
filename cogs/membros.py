import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlite3
import asyncio

class Membros(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('tickets.db')
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS reaction_roles (
                message_id TEXT, emoji TEXT, role_id TEXT, guild_id TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bio_roles (
                guild_id TEXT, palavra TEXT, role_id TEXT
            )
        ''')
        self.conn.commit()
        
        # Inicia o loop dos contadores
        self.update_counters.start()

    # --- COMANDO LIMPAR ---
    @app_commands.command(name="limpar", description="Apaga mensagens em massa do canal.")
    @app_commands.describe(quantidade="Número de mensagens para apagar (1-100)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def limpar(self, interaction: discord.Interaction, quantidade: int):
        if quantidade < 1 or quantidade > 100:
            await interaction.response.send_message("❌ A quantidade deve ser entre 1 e 100.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=quantidade)
        await interaction.followup.send(f"✅ `{len(deleted)}` mensagens foram apagadas.", ephemeral=True)

    # --- COMANDO PORTARIA ---
    @app_commands.command(name="portaria", description="Cria a mensagem de boas-vindas no canal atual.")
    @app_commands.checks.has_permissions(administrator=True)
    async def portaria(self, interaction: discord.Interaction, imagem: str = None):
        embed = discord.Embed(
            title="👋 Bem-vindo(a) à TRAMA!",
            description="Leia as regras, pegue seus cargos e divirta-se!",
            color=self.bot.COR_TRAMA
        )
        if imagem: embed.set_image(url=imagem)
        await interaction.response.send_message("Painel criado!", ephemeral=True)
        await interaction.channel.send(embed=embed)

    # --- COMANDO CARGOS ---
    @app_commands.command(name="cargos", description="Lista todos os cargos do servidor.")
    async def cargos(self, interaction: discord.Interaction):
        cargos = [role.mention for role in interaction.guild.roles if role.name != "@everyone"]
        lista = "\n".join(cargos) if cargos else "Nenhum cargo."
        if len(lista) > 4000: lista = lista[:4000] + "..."
        await interaction.response.send_message(embed=discord.Embed(title="📋 Cargos", description=lista, color=self.bot.COR_TRAMA), ephemeral=True)

    # --- COMANDO CARGO-REAÇÃO ---
    @app_commands.command(name="cargo-reacao", description="Cria uma mensagem para ganhar cargos por reação.")
    @app_commands.checks.has_permissions(administrator=True)
    async def cargo_reacao(self, interaction: discord.Interaction, cargo: discord.Role, emoji: str, texto: str):
        embed = discord.Embed(title="🎭 Pegue seu Cargo!", description=f"Reaja com {emoji} para ganhar **{cargo.name}**.\n\n{texto}", color=self.bot.COR_TRAMA)
        await interaction.response.send_message("Criado!", ephemeral=True)
        mensagem = await interaction.channel.send(embed=embed)
        await mensagem.add_reaction(emoji)
        self.cursor.execute("INSERT INTO reaction_roles VALUES (?, ?, ?, ?)", (str(mensagem.id), str(emoji), str(cargo.id), str(interaction.guild_id)))
        self.conn.commit()

    # --- COMANDO CARGO-MASSA ---
    @app_commands.command(name="cargo-massa", description="Adiciona ou remove um cargo de todos.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(acao=[app_commands.Choice(name="Adicionar", value="add"), app_commands.Choice(name="Remover", value="remove")])
    async def cargo_massa(self, interaction: discord.Interaction, cargo: discord.Role, acao: app_commands.Choice[str]):
        await interaction.response.send_message("⏳ Processando...", ephemeral=True)
        count = 0
        for membro in interaction.guild.members:
            if membro.bot: continue
            try:
                if acao.value == "add" and cargo not in membro.roles:
                    await membro.add_roles(cargo); count += 1
                elif acao.value == "remove" and cargo in membro.roles:
                    await membro.remove_roles(cargo); count += 1
                await asyncio.sleep(1) # Evita bloqueio do Discord
            except: pass
        await interaction.followup.send(f"✅ Cargo alterado para **{count}** membros.")

    # --- NOVO: COMANDO CARGO POR BIO ---
    @app_commands.command(name="cargo-por-bio", description="Dá um cargo para quem tem uma palavra específica na bio.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(palavra="A palavra que deve estar na bio", cargo="O cargo a ser dado")
    async def cargo_por_bio(self, interaction: discord.Interaction, palavra: str, cargo: discord.Role):
        await interaction.response.send_message(f"⏳ Lendo as bios de todos os membros... Isso pode demorar.", ephemeral=True)
        
        # Salva a regra no banco (para podermos rodar de novo no futuro)
        self.cursor.execute("INSERT INTO bio_roles VALUES (?, ?, ?)", (str(interaction.guild_id), palavra.lower(), str(cargo.id)))
        self.conn.commit()

        count = 0
        # O Discord exige que busquemos os membros um por um para ler a bio
        async for membro in interaction.guild.fetch_members(limit=None):
            if membro.bot: continue
            
            # A API do Discord pode não retornar a bio de todos por privacidade, então usamos try
            try:
                bio = membro.bio if membro.bio else ""
                if palavra.lower() in bio.lower() and cargo not in membro.roles:
                    await membro.add_roles(cargo)
                    count += 1
                    await asyncio.sleep(1)
            except: pass
            
        await interaction.followup.send(f"✅ **{count}** membros tinham a palavra `{palavra}` na bio e receberam o cargo {cargo.mention}.")

    # --- NOVO: COMANDO PRIMEIRA DAMA ---
    @app_commands.command(name="primeira-dama", description="Dá o cargo especial de destaque (Primeira Dama).")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(usuario="A pessoa que receberá o cargo especial")
    async def primeira_dama(self, interaction: discord.Interaction, usuario: discord.Member):
        # Tenta achar um cargo chamado "Primeira Dama" ou cria um novo
        cargo = discord.utils.get(interaction.guild.roles, name="👑 Primeira Dama")
        
        if not cargo:
            # Cria o cargo com cor rosa/dourada, separado dos outros
            cargo = await interaction.guild.create_role(name="👑 Primeira Dama", color=discord.Color.gold(), hoist=True)
        
        await usuario.add_roles(cargo)
        
        embed = discord.Embed(
            title="👑 Nova Primeira Dama!",
            description=f"{usuario.mention} agora é a **Primeira Dama** da TRAMA!\nEla tem permissões especiais e o cargo de maior destaque.",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)
        await interaction.channel.send(f"Parabéns, {usuario.mention}! 🎉")

    # --- NOVO: SISTEMA DE CONTADORES (CANAIS DE VOZ) ---
    @app_commands.command(name="contadores", description="Cria canais de voz que mostram a contagem do servidor.")
    @app_commands.checks.has_permissions(administrator=True)
    async def contadores(self, interaction: discord.Interaction):
        guild = interaction.guild
        await interaction.response.send_message("Criando canais de contagem...", ephemeral=True)
        
        # Cria os canais de voz (eles vão ser trancados para ninguém entrar)
        cat = await guild.create_category("📊 Estatísticas")
        
        await guild.create_voice_channel(f"👥 Membros: {guild.member_count}", category=cat)
        online = sum(1 for m in guild.members if m.status != discord.Status.offline)
        await guild.create_voice_channel(f"🟢 Online: {online}", category=cat)
        
        # Verifica se a categoria ficou visível e tranca os canais para ninguém entrar
        for channel in cat.channels:
            await channel.set_permissions(guild.default_role, connect=False)

        await interaction.followup.send("✅ Canais criados! Eles vão atualizar sozinhos a cada 10 minutos.")

    # Loop que roda a cada 10 minutos para atualizar o nome dos contadores
    @tasks.loop(minutes=10)
    async def update_counters(self):
        for guild in self.bot.guilds:
            try:
                # Busca os canais de voz que começam com os emojis
                membros_channel = discord.utils.get(guild.voice_channels, name=f"👥 Membros: {guild.member_count}")
                online_count = sum(1 for m in guild.members if m.status != discord.Status.offline)
                online_channel = discord.utils.get(guild.voice_channels, name=lambda c: c.startswith("🟢 Online:")) # Precisa buscar por prefixo
                
                # Atualiza o canal de membros
                if membros_channel:
                    await membros_channel.edit(name=f"👥 Membros: {guild.member_count}")
                
                # Atualiza o canal de online (precisa buscar todos e ver qual começa com 🟢)
                for channel in guild.voice_channels:
                    if channel.name.startswith("🟢 Online:"):
                        await channel.edit(name=f"🟢 Online: {online_count}")
                        break
            except Exception:
                pass

    # --- EVENTOS DE REAÇÃO ---
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member.bot: return
        self.cursor.execute("SELECT role_id FROM reaction_roles WHERE message_id = ? AND emoji = ?", (str(payload.message_id), str(payload.emoji)))
        result = self.cursor.fetchone()
        if result:
            role = payload.member.guild.get_role(int(result[0]))
            if role:
                try: await payload.member.add_roles(role)
                except: pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        self.cursor.execute("SELECT role_id FROM reaction_roles WHERE message_id = ? AND emoji = ?", (str(payload.message_id), str(payload.emoji)))
        result = self.cursor.fetchone()
        if result:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            role = guild.get_role(int(result[0]))
            if member and role:
                try: await member.remove_roles(role)
                except: pass

async def setup(bot):
    await bot.add_cog(Membros(bot))
