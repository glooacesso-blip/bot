import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlite3
import asyncio
import datetime

class Membros(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('tickets.db')
        self.cursor = self.conn.cursor()
        
        # Tabelas
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
        # Tabela para a Portaria
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS portaria_config (
                guild_id TEXT PRIMARY KEY,
                channel_id TEXT,
                imagem_url TEXT,
                texto_custom TEXT
            )
        ''')
        self.conn.commit()
        
        self.update_counters.start()

    # ==========================================
    # COMANDO: /limpar
    # ==========================================
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

    # ==========================================
    # GRUPO DE COMANDOS: /portaria
    # ==========================================
    portaria_group = app_commands.Group(name="portaria", description="Configurações do sistema de boas-vindas.")

    @portaria_group.command(name="definir-canal", description="Define o canal onde as boas-vindas serão enviadas.")
    @app_commands.checks.has_permissions(administrator=True)
    async def portaria_canal(self, interaction: discord.Interaction, canal: discord.TextChannel):
        self.cursor.execute("INSERT OR IGNORE INTO portaria_config (guild_id) VALUES (?)", (str(interaction.guild_id),))
        self.cursor.execute("UPDATE portaria_config SET channel_id = ? WHERE guild_id = ?", (str(canal.id), str(interaction.guild_id)))
        self.conn.commit()
        await interaction.response.send_message(f"✅ Canal de boas-vindas definido para {canal.mention}.", ephemeral=True)

    @portaria_group.command(name="imagem", description="Define a imagem (banner) que aparece na mensagem de boas-vindas.")
    @app_commands.checks.has_permissions(administrator=True)
    async def portaria_imagem(self, interaction: discord.Interaction, link_imagem: str):
        self.cursor.execute("INSERT OR IGNORE INTO portaria_config (guild_id) VALUES (?)", (str(interaction.guild_id),))
        self.cursor.execute("UPDATE portaria_config SET imagem_url = ? WHERE guild_id = ?", (link_imagem, str(interaction.guild_id)))
        self.conn.commit()
        await interaction.response.send_message("✅ Imagem de boas-vindas atualizada!", ephemeral=True)

    @portaria_group.command(name="texto", description="Define o texto personalizado da mensagem de boas-vindas.")
    @app_commands.checks.has_permissions(administrator=True)
    async def portaria_texto(self, interaction: discord.Interaction, texto: str):
        self.cursor.execute("INSERT OR IGNORE INTO portaria_config (guild_id) VALUES (?)", (str(interaction.guild_id),))
        self.cursor.execute("UPDATE portaria_config SET texto_custom = ? WHERE guild_id = ?", (texto, str(interaction.guild_id)))
        self.conn.commit()
        await interaction.response.send_message("✅ Texto de boas-vindas atualizado!", ephemeral=True)

    # Evento de entrada de membro
    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        self.cursor.execute("SELECT channel_id, imagem_url, texto_custom FROM portaria_config WHERE guild_id = ?", (str(guild.id),))
        result = self.cursor.fetchone()
        
        if not result or not result[0]:
            return
            
        canal_id, imagem_url, texto_custom = result
        canal = guild.get_channel(int(canal_id))
        if not canal: return

        texto = texto_custom if texto_custom else f"Olá {member.mention}, estamos muito felizes em ter você aqui!\n\nLeia as regras, pegue seus cargos e divirta-se."

        embed = discord.Embed(
            title="🌊 Bem-vindo(a) à TRAMA!",
            description=texto,
            color=self.bot.COR_TRAMA
        )
        
        if imagem_url:
            embed.set_image(url=imagem_url)
        else:
            embed.set_thumbnail(url=member.display_avatar.url)
            
        embed.set_footer(text="Surf Trama • Comunidade")
        embed.timestamp = discord.utils.utcnow()

        try:
            await canal.send(content=member.mention, embed=embed)
        except discord.Forbidden:
            pass

        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            pass

    # ==========================================
    # COMANDO: /cargos
    # ==========================================
    @app_commands.command(name="cargos", description="Lista todos os cargos do servidor.")
    async def cargos(self, interaction: discord.Interaction):
        cargos = [role.mention for role in interaction.guild.roles if role.name != "@everyone"]
        lista = "\n".join(cargos) if cargos else "Nenhum cargo."
        if len(lista) > 4000: lista = lista[:4000] + "..."
        await interaction.response.send_message(embed=discord.Embed(title="📋 Cargos", description=lista, color=self.bot.COR_TRAMA), ephemeral=True)

    # ==========================================
    # COMANDO: /cargo-reacao
    # ==========================================
    @app_commands.command(name="cargo-reacao", description="Cria uma mensagem para ganhar cargos por reação.")
    @app_commands.checks.has_permissions(administrator=True)
    async def cargo_reacao(self, interaction: discord.Interaction, cargo: discord.Role, emoji: str, texto: str):
        embed = discord.Embed(title="🎭 Pegue seu Cargo!", description=f"Reaja com {emoji} para ganhar **{cargo.name}**.\n\n{texto}", color=self.bot.COR_TRAMA)
        await interaction.response.send_message("Criado!", ephemeral=True)
        mensagem = await interaction.channel.send(embed=embed)
        await mensagem.add_reaction(emoji)
        self.cursor.execute("INSERT INTO reaction_roles VALUES (?, ?, ?, ?)", (str(mensagem.id), str(emoji), str(cargo.id), str(interaction.guild_id)))
        self.conn.commit()

    # ==========================================
    # COMANDO: /cargo-massa
    # ==========================================
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
                await asyncio.sleep(1)
            except: pass
        await interaction.followup.send(f"✅ Cargo alterado para **{count}** membros.")

    # ==========================================
    # COMANDO: /cargo-por-bio
    # ==========================================
    @app_commands.command(name="cargo-por-bio", description="Dá um cargo para quem tem uma palavra específica na bio.")
    @app_commands.checks.has_permissions(administrator=True)
    async def cargo_por_bio(self, interaction: discord.Interaction, palavra: str, cargo: discord.Role):
        await interaction.response.send_message(f"⏳ Lendo as bios...", ephemeral=True)
        self.cursor.execute("INSERT INTO bio_roles VALUES (?, ?, ?)", (str(interaction.guild_id), palavra.lower(), str(cargo.id)))
        self.conn.commit()
        count = 0
        async for membro in interaction.guild.fetch_members(limit=None):
            if membro.bot: continue
            try:
                if membro.bio and palavra.lower() in membro.bio.lower() and cargo not in membro.roles:
                    await membro.add_roles(cargo)
                    count += 1
                    await asyncio.sleep(1)
            except: pass
        await interaction.followup.send(f"✅ **{count}** membros receberam o cargo {cargo.mention}.")

    # ==========================================
    # COMANDO: /primeira-dama
    # ==========================================
    @app_commands.command(name="primeira-dama", description="Dá o cargo especial de destaque.")
    @app_commands.checks.has_permissions(administrator=True)
    async def primeira_dama(self, interaction: discord.Interaction, usuario: discord.Member):
        cargo = discord.utils.get(interaction.guild.roles, name="👑 Primeira Dama")
        if not cargo:
            cargo = await interaction.guild.create_role(name="👑 Primeira Dama", color=discord.Color.gold(), hoist=True)
        await usuario.add_roles(cargo)
        embed = discord.Embed(title="👑 Nova Primeira Dama!", description=f"{usuario.mention} agora é a **Primeira Dama** da TRAMA!", color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)

    # ==========================================
    # COMANDO: /contadores
    # ==========================================
    @app_commands.command(name="contadores", description="Cria canais de voz que mostram a contagem do servidor.")
    @app_commands.checks.has_permissions(administrator=True)
    async def contadores(self, interaction: discord.Interaction):
        guild = interaction.guild
        await interaction.response.send_message("Criando canais...", ephemeral=True)
        cat = await guild.create_category("📊 Estatísticas")
        await guild.create_voice_channel(f"👥 Membros: {guild.member_count}", category=cat)
        online = sum(1 for m in guild.members if m.status != discord.Status.offline)
        await guild.create_voice_channel(f"🟢 Online: {online}", category=cat)
        for channel in cat.channels:
            await channel.set_permissions(guild.default_role, connect=False)
        await interaction.followup.send("✅ Canais criados!")

    @tasks.loop(minutes=10)
    async def update_counters(self):
        for guild in self.bot.guilds:
            try:
                membros_channel = discord.utils.get(guild.voice_channels, name=f"👥 Membros: {guild.member_count}")
                online_count = sum(1 for m in guild.members if m.status != discord.Status.offline)
                online_channel = discord.utils.get(guild.voice_channels, name=lambda c: c.startswith("🟢 Online:"))
                if membros_channel:
                    await membros_channel.edit(name=f"👥 Membros: {guild.member_count}")
                for channel in guild.voice_channels:
                    if channel.name.startswith("🟢 Online:"):
                        await channel.edit(name=f"🟢 Online: {online_count}")
                        break
            except: pass

    # ==========================================
    # EVENTOS DE REAÇÃO
    # ==========================================
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
