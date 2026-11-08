import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import datetime

class VIP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('tickets.db')
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS vips (
                user_id TEXT PRIMARY KEY,
                guild_id TEXT,
                expira_em TEXT
            )
        ''')
        self.conn.commit()

    # --- GRUPO DE COMANDOS /VIP ---
    vip_group = app_commands.Group(name="vip", description="Sistema de gerenciamento VIP.")

    @vip_group.command(name="painel", description="Cria o painel de vendas do VIP no canal.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        imagem="Link do banner do VIP (Opcional)",
        texto="Texto explicativo sobre os benefícios do VIP"
    )
    async def vip_painel(self, interaction: discord.Interaction, imagem: str = None, texto: str = "Adquira o VIP e tenha benefícios exclusivos no servidor!"):
        embed = discord.Embed(
            title="💎 Torne-se VIP na TRAMA!",
            description=texto,
            color=discord.Color.gold()
        )
        if imagem:
            embed.set_image(url=imagem)
        embed.add_field(name="Benefícios:", value="✅ Cargo exclusivo\n✅ Canais privados\n✅ Sorteios exclusivos\n✅ Suporte prioritário", inline=False)
        embed.set_footer(text="Clique no botão abaixo para comprar")
        
        await interaction.response.send_message("Painel VIP criado!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=BotaoComprarVIP())

    @vip_group.command(name="adicionar", description="Adiciona o VIP a um usuário.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(usuario="Quem vai receber o VIP", dias="Quantos dias de VIP")
    async def vip_adicionar(self, interaction: discord.Interaction, usuario: discord.Member, dias: int):
        expiracao = datetime.datetime.now() + datetime.timedelta(days=dias)
        expiracao_str = expiracao.strftime("%d/%m/%Y")
        
        self.cursor.execute("INSERT OR REPLACE INTO vips VALUES (?, ?, ?)", (str(usuario.id), str(interaction.guild_id), expiracao_str))
        self.conn.commit()
        
        cargo_vip = discord.utils.get(interaction.guild.roles, name="💎 VIP")
        if cargo_vip:
            await usuario.add_roles(cargo_vip)
            
        await interaction.response.send_message(f"✅ VIP concedido para {usuario.mention} até **{expiracao_str}**.", ephemeral=True)

    @vip_group.command(name="remover", description="Remove o VIP de um usuário.")
    @app_commands.checks.has_permissions(administrator=True)
    async def vip_remover(self, interaction: discord.Interaction, usuario: discord.Member):
        self.cursor.execute("DELETE FROM vips WHERE user_id = ?", (str(usuario.id),))
        self.conn.commit()
        
        cargo_vip = discord.utils.get(interaction.guild.roles, name="💎 VIP")
        if cargo_vip and cargo_vip in usuario.roles:
            await usuario.remove_roles(cargo_vip)
            
        await interaction.response.send_message(f"✅ VIP removido de {usuario.mention}.", ephemeral=True)

    @vip_group.command(name="verificar", description="Verifica se um usuário é VIP.")
    async def vip_verificar(self, interaction: discord.Interaction, usuario: discord.Member = None):
        if usuario is None:
            usuario = interaction.user
            
        self.cursor.execute("SELECT expira_em FROM vips WHERE user_id = ?", (str(usuario.id),))
        result = self.cursor.fetchone()
        
        if result:
            embed = discord.Embed(title="💎 Status VIP", color=discord.Color.gold())
            embed.add_field(name="Usuário", value=usuario.mention)
            embed.add_field(name="Válido até", value=result[0])
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ {usuario.mention} não é VIP.", ephemeral=True)


# --- BOTÃO DE COMPRAR VIP ---
class BotaoComprarVIP(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Comprar VIP", style=discord.ButtonStyle.success, emoji="💎", custom_id="btn_comprar_vip_v2")
    async def comprar(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🛒 Como Comprar o VIP",
            description="Para adquirir o VIP, abra um ticket no canal de suporte ou entre em contato com a administração.\n\n**Formas de pagamento:**\n• Pix\n• Cartão de Crédito",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(VIP(bot))
