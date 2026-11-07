import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os

class Seguranca(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('tickets.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                guild_id TEXT PRIMARY KEY,
                anti_raid INTEGER DEFAULT 0,
                anti_link INTEGER DEFAULT 0,
                protecao_arq INTEGER DEFAULT 0,
                canal_honeypot TEXT DEFAULT NULL
            )
        ''')
        self.conn.commit()

    def get_config(self, guild_id):
        self.cursor.execute("SELECT anti_raid, anti_link, protecao_arq, canal_honeypot FROM settings WHERE guild_id = ?", (str(guild_id),))
        result = self.cursor.fetchone()
        if result:
            return {"anti_raid": bool(result[0]), "anti_link": bool(result[1]), "protecao_arq": bool(result[2]), "canal_honeypot": result[3]}
        else:
            self.cursor.execute("INSERT INTO settings (guild_id) VALUES (?)", (str(guild_id),))
            self.conn.commit()
            return {"anti_raid": False, "anti_link": False, "protecao_arq": False, "canal_honeypot": None}

    def set_config(self, guild_id, key, value):
        self.cursor.execute(f"UPDATE settings SET {key} = ? WHERE guild_id = ?", (value, str(guild_id)))
        self.conn.commit()

    # --- COMANDOS DE CONFIGURAÇÃO ---

    @app_commands.command(name="anti-raid", description="Ativa/desativa a proteção contra contas novas.")
    @app_commands.choices(status=[app_commands.Choice(name="Ativar", value="on"), app_commands.Choice(name="Desativar", value="off")])
    @app_commands.checks.has_permissions(administrator=True)
    async def anti_raid(self, interaction: discord.Interaction, status: app_commands.Choice[str]):
        ativo = status.value == "on"
        self.set_config(interaction.guild_id, "anti_raid", int(ativo))
        await interaction.response.send_message(f"{'🛡️ **Anti-Raid ATIVADO**' if ativo else '⚠️ **Anti-Raid DESATIVADO**'}", ephemeral=True)

    @app_commands.command(name="anti-link", description="Ativa/desativa o bloqueio de links.")
    @app_commands.choices(status=[app_commands.Choice(name="Ativar", value="on"), app_commands.Choice(name="Desativar", value="off")])
    @app_commands.checks.has_permissions(administrator=True)
    async def anti_link(self, interaction: discord.Interaction, status: app_commands.Choice[str]):
        ativo = status.value == "on"
        self.set_config(interaction.guild_id, "anti_link", int(ativo))
        await interaction.response.send_message(f"{'🔗 **Anti-Link ATIVADO**' if ativo else '🔓 **Anti-Link DESATIVADO**'}", ephemeral=True)

    @app_commands.command(name="protecao-arquivos", description="Ativa/desativa o bloqueio de arquivos perigosos.")
    @app_commands.choices(status=[app_commands.Choice(name="Ativar", value="on"), app_commands.Choice(name="Desativar", value="off")])
    @app_commands.checks.has_permissions(administrator=True)
    async def protecao_arquivos(self, interaction: discord.Interaction, status: app_commands.Choice[str]):
        ativo = status.value == "on"
        self.set_config(interaction.guild_id, "protecao_arq", int(ativo))
        await interaction.response.send_message(f"{'📁 **Proteção de Arquivos ATIVADA**' if ativo else '📂 **Proteção de Arquivos DESATIVADA**'}", ephemeral=True)

    @app_commands.command(name="honeypot", description="Transforma o canal atual em um Honeypot (bane quem falar aqui).")
    @app_commands.checks.has_permissions(administrator=True)
    async def honeypot(self, interaction: discord.Interaction):
        self.set_config(interaction.guild_id, "canal_honeypot", str(interaction.channel_id))
        
        embed = discord.Embed(title="🍯 HONEYPOT ATIVO", description="⚠️ **CUIDADO:** Qualquer mensagem enviada neste canal resultará em banimento imediato.", color=0xFF0000)
        await interaction.response.send_message("Canal configurado como Honeypot!", ephemeral=True)
        await interaction.channel.send(embed=embed)

    @app_commands.command(name="verificacao", description="Envia o painel de verificação para novos membros.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(cargo="O cargo que a pessoa vai ganhar ao clicar no botão.")
    async def verificacao(self, interaction: discord.Interaction, cargo: discord.Role):
        embed = discord.Embed(
            title="✅ Verificação TRAMA",
            description="Clique no botão abaixo para provar que você não é um robô e liberar o acesso ao servidor.",
            color=self.bot.COR_TRAMA
        )
        embed.set_footer(text="Segurança TRAMA")
        await interaction.response.send_message("Painel de verificação enviado!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=BotaoVerificacao(cargo.id))

    # --- COMANDO DE TRANCAR/DESTRANCAR ---
    @app_commands.command(name="trancar", description="Tranca o canal atual.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def trancar(self, interaction: discord.Interaction):
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message("🔒 Canal Trancado.")

    @app_commands.command(name="destrancar", description="Destranca o canal atual.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def destrancar(self, interaction: discord.Interaction):
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = True
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message("🔓 Canal Destrancado.")

    # --- EVENTOS DE MONITORAMENTO ---

    @commands.Cog.listener()
    async def on_member_join(self, member):
        config = self.get_config(member.guild.id)
        
        # 1. Anti-Raid (Contas com menos de 7 dias)
        if config["anti_raid"]:
            idade_conta = (discord.utils.utcnow() - member.created_at).days
            if idade_conta < 7:
                try:
                    await member.ban(reason="Anti-Raid: Conta muito recente.")
                except discord.Forbidden:
                    pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        config = self.get_config(message.guild.id)

        # 2. Honeypot (Banir quem falar no canal)
        if config["canal_honeypot"] and str(message.channel.id) == str(config["canal_honeypot"]):
            if not message.author.guild_permissions.administrator:
                try:
                    await message.author.ban(reason="Ativou o Honeypot.")
                    await message.guild.kick(message.author, reason="Honeypot") # Caso não consiga banir
                except discord.Forbidden:
                    pass
                return

        # Se for adm, ignora as próximas regras
        if message.author.guild_permissions.administrator: return

        # 3. Anti-Link
        if config["anti_link"]:
            if "http://" in message.content or "https://" in message.content or "www." in message.content:
                try:
                    await message.delete()
                    aviso = await message.channel.send(f"⚠️ {message.author.mention}, links não são permitidos.")
                    await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=5))
                    await aviso.delete()
                except discord.Forbidden: pass

        # 4. Proteção de Arquivos
        if config["protecao_arq"] and message.attachments:
            extensoes_perigosas = ['.exe', '.bat', '.cmd', '.scr', '.vbs', '.js', '.jar', '.msi', '.ps1']
            for anexo in message.attachments:
                if any(anexo.filename.lower().endswith(ext) for ext in extensoes_perigosas):
                    try:
                        await message.delete()
                        aviso = await message.channel.send(f"⚠️ {message.author.mention}, arquivos **{anexo.filename}** são perigosos e foram bloqueados.")
                        await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=5))
                        await aviso.delete()
                    except discord.Forbidden: pass
                    break

# --- BOTÃO DE VERIFICAÇÃO ---
class BotaoVerificacao(discord.ui.View):
    def __init__(self, cargo_id: int):
        super().__init__(timeout=None)
        self.cargo_id = cargo_id

    @discord.ui.button(label="Verificar-se", style=discord.ButtonStyle.success, emoji="✅", custom_id="btn_verificacao")
    async def verificar(self, interaction: discord.Interaction, button: discord.ui.Button):
        cargo = interaction.guild.get_role(self.cargo_id)
        if cargo:
            try:
                await interaction.user.add_roles(cargo)
                await interaction.response.send_message(f"✅ Você foi verificado e recebeu o cargo **{cargo.name}**!", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("❌ Não tenho permissão para te dar esse cargo. Avise a Staff.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ O cargo de verificação não existe mais. Avise a Staff.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Seguranca(bot))
