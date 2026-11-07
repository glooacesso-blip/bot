import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import asyncio

class Membros(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('tickets.db')
        self.cursor = self.conn.cursor()
        # Tabela para guardar os cargos de reação
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS reaction_roles (
                message_id TEXT,
                emoji TEXT,
                role_id TEXT,
                guild_id TEXT
            )
        ''')
        self.conn.commit()

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

    # --- COMANDO PORTARIA (BOAS-VINDAS) ---
    @app_commands.command(name="portaria", description="Cria a mensagem de boas-vindas no canal atual.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(imagem="Link do banner de boas-vindas (Opcional)")
    async def portaria(self, interaction: discord.Interaction, imagem: str = None):
        embed = discord.Embed(
            title="👋 Bem-vindo(a) à TRAMA!",
            description="Estamos muito felizes em ter você aqui. Leia as regras, pegue seus cargos e divirta-se!\n\nSe precisar de ajuda, abra um ticket.",
            color=self.bot.COR_TRAMA
        )
        if imagem:
            embed.set_image(url=imagem)
        embed.set_footer(text="Surf Trama • Comunidade")
        
        await interaction.response.send_message("Painel de boas-vindas criado!", ephemeral=True)
        await interaction.channel.send(embed=embed)

    # --- COMANDO CARGOS (LISTAR) ---
    @app_commands.command(name="cargos", description="Lista todos os cargos do servidor.")
    async def cargos(self, interaction: discord.Interaction):
        cargos = [role.mention for role in interaction.guild.roles if role.name != "@everyone"]
        if not cargos:
            await interaction.response.send_message("Este servidor não tem cargos.", ephemeral=True)
            return
            
        # Divide em blocos para não passar do limite do Discord
        lista_formatada = "\n".join(cargos)
        if len(lista_formatada) > 4000:
            lista_formatada = lista_formatada[:4000] + "\n... (muitos cargos)"
            
        embed = discord.Embed(title="📋 Cargos do Servidor", description=lista_formatada, color=self.bot.COR_TRAMA)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- COMANDO CARGO-REAÇÃO ---
    @app_commands.command(name="cargo-reacao", description="Cria uma mensagem para ganhar cargos por reação.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        cargo="O cargo que será dado",
        emoji="O emoji que a pessoa deve reagir (ex: 🎮)",
        texto="O texto que vai aparecer acima do emoji"
    )
    async def cargo_reacao(self, interaction: discord.Interaction, cargo: discord.Role, emoji: str, texto: str):
        embed = discord.Embed(
            title="🎭 Pegue seu Cargo!",
            description=f"Reaja com {emoji} para ganhar o cargo **{cargo.name}**.\n\n{texto}",
            color=self.bot.COR_TRAMA
        )
        
        await interaction.response.send_message("Mensagem de reação criada!", ephemeral=True)
        mensagem = await interaction.channel.send(embed=embed)
        await mensagem.add_reaction(emoji)
        
        # Salva no banco de dados para o bot saber o que fazer quando alguém reagir
        self.cursor.execute(
            "INSERT INTO reaction_roles (message_id, emoji, role_id, guild_id) VALUES (?, ?, ?, ?)",
            (str(mensagem.id), str(emoji), str(cargo.id), str(interaction.guild_id))
        )
        self.conn.commit()

    # --- COMANDO CARGO-MASSA ---
    @app_commands.command(name="cargo-massa", description="Adiciona ou remove um cargo de todos os membros.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(cargo="O cargo a ser dado/removido", acao="Adicionar ou Remover")
    @app_commands.choices(acao=[
        app_commands.Choice(name="Adicionar a todos", value="add"),
        app_commands.Choice(name="Remover de todos", value="remove")
    ])
    async def cargo_massa(self, interaction: discord.Interaction, cargo: discord.Role, acao: app_commands.Choice[str]):
        await interaction.response.send_message("⏳ Iniciando processo em massa... (Isso pode demorar)", ephemeral=True)
        
        count = 0
        for membro in interaction.guild.members:
            if membro.bot: continue # Ignora bots
            
            try:
                if acao.value == "add":
                    if cargo not in membro.roles:
                        await membro.add_roles(cargo)
                        count += 1
                elif acao.value == "remove":
                    if cargo in membro.roles:
                        await membro.remove_roles(cargo)
                        count += 1
                # Pequeno delay para não ser bloqueado pelo Discord (Rate Limit)
                await asyncio.sleep(1)
            except discord.Forbidden:
                await interaction.followup.send("❌ Erro: Não tenho permissão ou o cargo é maior que o meu.", ephemeral=True)
                break
                
        verbo = "adicionado a" if acao.value == "add" else "removido de"
        await interaction.followup.send(f"✅ O cargo **{cargo.name}** foi {verbo} **{count}** membros.")

    # --- EVENTO: O QUE ACONTECE QUANDO ALGUÉM REAGE ---
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member.bot: return # Ignora bots
        
        self.cursor.execute(
            "SELECT role_id FROM reaction_roles WHERE message_id = ? AND emoji = ?",
            (str(payload.message_id), str(payload.emoji))
        )
        result = self.cursor.fetchone()
        
        if result:
            role_id = int(result[0])
            guild = self.bot.get_guild(payload.guild_id)
            role = guild.get_role(role_id)
            if role:
                try:
                    await payload.member.add_roles(role)
                except discord.Forbidden:
                    pass

    # --- EVENTO: O QUE ACONTECE QUANDO ALGUÉM REMOVE A REAÇÃO ---
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        self.cursor.execute(
            "SELECT role_id FROM reaction_roles WHERE message_id = ? AND emoji = ?",
            (str(payload.message_id), str(payload.emoji))
        )
        result = self.cursor.fetchone()
        
        if result:
            role_id = int(result[0])
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            role = guild.get_role(role_id)
            
            if member and role:
                try:
                    await member.remove_roles(role)
                except discord.Forbidden:
                    pass

async def setup(bot):
    await bot.add_cog(Membros(bot))
