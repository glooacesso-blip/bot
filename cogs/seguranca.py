import discord
from discord import app_commands
from discord.ext import commands
import sqlite3

class Seguranca(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Conecta ao banco de dados (o mesmo dos tickets)
        self.conn = sqlite3.connect('tickets.db')
        self.cursor = self.conn.cursor()
        # Cria a tabela de configurações
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                guild_id TEXT PRIMARY KEY,
                anti_raid INTEGER DEFAULT 0,
                anti_link INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()

    def get_config(self, guild_id):
        self.cursor.execute("SELECT anti_raid, anti_link FROM settings WHERE guild_id = ?", (str(guild_id),))
        result = self.cursor.fetchone()
        if result:
            return {"anti_raid": bool(result[0]), "anti_link": bool(result[1])}
        else:
            # Se não existir, cria a configuração zerada
            self.cursor.execute("INSERT INTO settings (guild_id) VALUES (?)", (str(guild_id),))
            self.conn.commit()
            return {"anti_raid": False, "anti_link": False}

    def set_config(self, guild_id, key, value):
        self.cursor.execute(f"UPDATE settings SET {key} = ? WHERE guild_id = ?", (int(value), str(guild_id)))
        self.conn.commit()

    # --- COMANDO ANTI-RAID ---
    @app_commands.command(name="anti-raid", description="Ativa ou desativa a proteção contra contas recentes (raid).")
    @app_commands.describe(status="Escolha se quer Ativar ou Desativar")
    @app_commands.choices(status=[
        app_commands.Choice(name="Ativar", value="on"),
        app_commands.Choice(name="Desativar", value="off")
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def anti_raid(self, interaction: discord.Interaction, status: app_commands.Choice[str]):
        ativo = status.value == "on"
        self.set_config(interaction.guild_id, "anti_raid", ativo)
        
        emoji = "🛡️" if ativo else "⚠️"
        estado = "ATIVADO" if ativo else "DESATIVADO"
        await interaction.response.send_message(f"{emoji} **Anti-Raid {estado}**\nContas criadas há menos de 7 dias serão banidas ao entrar.", ephemeral=True)

    # --- COMANDO ANTI-LINK ---
    @app_commands.command(name="anti-link", description="Ativa ou desativa o bloqueio de links externos.")
    @app_commands.describe(status="Escolha se quer Ativar ou Desativar")
    @app_commands.choices(status=[
        app_commands.Choice(name="Ativar", value="on"),
        app_commands.Choice(name="Desativar", value="off")
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def anti_link(self, interaction: discord.Interaction, status: app_commands.Choice[str]):
        ativo = status.value == "on"
        self.set_config(interaction.guild_id, "anti_link", ativo)
        
        emoji = "🔗" if ativo else "🔓"
        estado = "ATIVADO" if ativo else "DESATIVADO"
        await interaction.response.send_message(f"{emoji} **Anti-Link {estado}**\nMensagens com links serão deletadas.", ephemeral=True)

    # --- COMANDO TRANcar CANAL ---
    @app_commands.command(name="trancar", description="Tranca o canal atual para que ninguém possa falar.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def trancar(self, interaction: discord.Interaction):
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        
        embed = discord.Embed(title="🔒 Canal Trancado", description="Apenas administradores podem falar aqui agora.", color=0x8B0000)
        await interaction.response.send_message(embed=embed)

    # --- COMANDO DESTRANcar CANAL ---
    @app_commands.command(name="destrancar", description="Destranca o canal atual.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def destrancar(self, interaction: discord.Interaction):
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = True
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        
        embed = discord.Embed(title="🔓 Canal Destrancado", description="Todos podem voltar a falar.", color=0x00FF00)
        await interaction.response.send_message(embed=embed)

    # --- EVENTOS DE MONITORAMENTO (O que acontece quando alguém entra ou manda mensagem) ---
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        config = self.get_config(member.guild.id)
        
        # Se o Anti-Raid estiver ativado
        if config["anti_raid"]:
            # Pega a idade da conta do usuário em dias
            idade_conta = (discord.utils.utcnow() - member.created_at).days
            
            if idade_conta < 7: # Se a conta for muito nova (menos de 7 dias)
                try:
                    await member.ban(reason="Anti-Raid: Conta muito recente.")
                    # Avisa no canal de logs (se você tiver um, troque o ID)
                    print(f"🛡️ Anti-Raid: Banido {member.name} (Conta criada há {idade_conta} dias).")
                except discord.Forbidden:
                    print(f"❌ Anti-Raid: Sem permissão para banir {member.name}.")

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignora mensagens de bots e DMs
        if message.author.bot or not message.guild:
            return
            
        # Ignora se for administrador (para você poder mandar links)
        if message.author.guild_permissions.administrator:
            return

        config = self.get_config(message.guild.id)
        
        # Se o Anti-Link estiver ativado
        if config["anti_link"]:
            # Verifica se a mensagem tem um link (http ou www)
            if "http://" in message.content or "https://" in message.content or "www." in message.content:
                try:
                    await message.delete()
                    aviso = await message.channel.send(f"⚠️ {message.author.mention}, links não são permitidos neste servidor.")
                    await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=5))
                    await aviso.delete()
                except discord.Forbidden:
                    pass

async def setup(bot):
    await bot.add_cog(Seguranca(bot))
