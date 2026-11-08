import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import requests
import json
import datetime

class Pagamentos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('tickets.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS syncpay_config (guild_id TEXT PRIMARY KEY, public_token TEXT, secret_token TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS mensagens_vip (guild_id TEXT PRIMARY KEY, titulo_painel TEXT, desc_painel TEXT, msg_canal TEXT, texto_botao TEXT)''')
        self.conn.commit()

    def get_textos(self, guild_id):
        self.cursor.execute("SELECT titulo_painel, desc_painel, msg_canal, texto_botao FROM mensagens_vip WHERE guild_id = ?", (str(guild_id),))
        row = self.cursor.fetchone()
        return {"titulo": row[0] if row and row[0] else "💎 Torne-se VIP!", "desc": row[1] if row and row[1] else "Adquira o VIP!", "msg_canal": row[2] if row and row[2] else "Escolha seu plano:", "botao": row[3] if row and row[3] else "Comprar VIP"}

    @app_commands.command(name="configurar-syncpay", description="Configura a SyncPay.")
    @app_commands.checks.has_permissions(administrator=True)
    async def configurar_syncpay(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalConfigurarSyncPay())

    @app_commands.command(name="configurar-mensagens", description="Muda os textos do painel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def configurar_mensagens(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalConfigurarMensagens(self.get_textos(interaction.guild_id)))

    @app_commands.command(name="painel-vip", description="Cria o painel de vendas.")
    @app_commands.checks.has_permissions(administrator=True)
    async def painel_vip(self, interaction: discord.Interaction, imagem: str = None):
        self.cursor.execute("SELECT 1 FROM syncpay_config WHERE guild_id = ?", (str(interaction.guild_id),))
        if not self.cursor.fetchone(): return await interaction.response.send_message("❌ Configure a SyncPay primeiro com `/configurar-syncpay`.", ephemeral=True)
        
        textos = self.get_textos(interaction.guild_id)
        def is_old_panel(msg): return msg.author == self.bot.user and msg.embeds and msg.embeds[0].title == textos["titulo"]
        try: await interaction.channel.purge(limit=50, check=is_old_panel)
        except: pass

        embed = discord.Embed(title=textos["titulo"], description=textos["desc"], color=discord.Color.gold())
        if imagem: embed.set_image(url=imagem)
        await interaction.response.send_message("Painel criado!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=BotaoComprarVIP())

class ModalConfigurarSyncPay(discord.ui.Modal, title="Configurar SyncPay"):
    public_token = discord.ui.TextInput(label="Public Token", required=True)
    secret_token = discord.ui.TextInput(label="Secret Token", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Pagamentos")
        cog.cursor.execute("INSERT OR REPLACE INTO syncpay_config VALUES (?, ?, ?)", (str(interaction.guild_id), self.public_token.value, self.secret_token.value))
        cog.conn.commit()
        await interaction.response.send_message("✅ SyncPay configurada!", ephemeral=True)

class ModalConfigurarMensagens(discord.ui.Modal, title="Personalizar Mensagens"):
    def __init__(self, atuais):
        super().__init__()
        self.t = discord.ui.TextInput(label="Título", default=atuais["titulo"]); self.d = discord.ui.TextInput(label="Descrição", default=atuais["desc"], style=discord.TextStyle.paragraph)
        self.m = discord.ui.TextInput(label="Mensagem no Canal", default=atuais["msg_canal"], style=discord.TextStyle.paragraph); self.b = discord.ui.TextInput(label="Texto do Botão", default=atuais["botao"])
        self.add_item(self.t); self.add_item(self.d); self.add_item(self.m); self.add_item(self.b)
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Pagamentos")
        cog.cursor.execute("INSERT OR REPLACE INTO mensagens_vip VALUES (?, ?, ?, ?, ?)", (str(interaction.guild_id), self.t.value, self.d.value, self.m.value, self.b.value))
        cog.conn.commit()
        await interaction.response.send_message("✅ Mensagens atualizadas!", ephemeral=True)

class BotaoComprarVIP(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="Comprar VIP", style=discord.ButtonStyle.success, emoji="💎", custom_id="btn_comprar_v15")
    async def comprar(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("Pagamentos")
        textos = cog.get_textos(interaction.guild_id)
        
        nome_canal = f"venda-vip-{interaction.user.name.lower()}"
        if discord.utils.get(interaction.guild.text_channels, name=nome_canal):
            return await interaction.response.send_message(f"❌ Você já tem uma venda aberta.", ephemeral=True)

        # REGISTRA CLIQUE NO BANCO (ESTATÍSTICA)
        agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        cog.cursor.execute("INSERT INTO estatisticas (tipo, user_id, user_name, guild_id, detalhe, data) VALUES (?, ?, ?, ?, ?, ?)",
                       ('Venda', str(interaction.user.id), interaction.user.name, str(interaction.guild_id), 'Clique em Comprar', agora))
        cog.conn.commit()

        overwrites = {interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False), interaction.user: discord.PermissionOverwrite(read_messages=True), interaction.guild.me: discord.PermissionOverwrite(read_messages=True)}
        canal = await interaction.guild.create_text_channel(nome_canal, overwrites=overwrites)
        
        embed = discord.Embed(title="💎 Escolha seu Plano", description=textos["msg_canal"], color=discord.Color.gold())
        await canal.send(content=f"{interaction.user.mention}", embed=embed, view=MenuPlanos())
        await interaction.response.send_message(f"✅ Canal criado: {canal.mention}", ephemeral=True)

class MenuPlanos(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="VIP Básico - R$ 9,90", style=discord.ButtonStyle.secondary, emoji="🥉", custom_id="btn_p1_v15")
    async def p1(self, interaction: discord.Interaction, button: discord.ui.Button): await self.processar(interaction, 9.90, "Básico")

    @discord.ui.button(label="VIP Premium - R$ 19,90", style=discord.ButtonStyle.primary, emoji="🥈", custom_id="btn_p2_v15")
    async def p2(self, interaction: discord.Interaction, button: discord.ui.Button): await self.processar(interaction, 19.90, "Premium")

    @discord.ui.button(label="VIP Master - R$ 29,90", style=discord.ButtonStyle.success, emoji="🥇", custom_id="btn_p3_v15")
    async def p3(self, interaction: discord.Interaction, button: discord.ui.Button): await self.processar(interaction, 29.90, "Master")

    async def processar(self, interaction: discord.Interaction, valor: float, nome: str):
        cog = interaction.client.get_cog("Pagamentos")
        cog.cursor.execute("SELECT public_token, secret_token FROM syncpay_config WHERE guild_id = ?", (str(interaction.guild_id),))
        syncpay = cog.cursor.fetchone()
        if not syncpay: return await interaction.response.send_message("❌ SyncPay não configurada.", ephemeral=True)

        await interaction.response.defer()
        
        # GERA PIX NA SYNCPAY (FUNÇÃO SIMPLIFICADA PARA O EXEMPLO)
        url = "https://api.syncpay.pro/v1/gateway/api/pix/cashIn"
        payload = {"amount": valor, "description": "VIP", "customer": {"name": interaction.user.name, "email": f"{interaction.user.id}@d.com", "cpf": "00000000000"}, "postbackUrl": "https://seu-site.onrender.com/webhook"}
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {syncpay[1]}", "x-public-key": syncpay[0]}
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            dados = response.json()
            
            # REGISTRA PAGAMENTO NO BANCO (ESTATÍSTICA)
            agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
            cog.cursor.execute("INSERT INTO estatisticas (tipo, user_id, user_name, guild_id, detalhe, data) VALUES (?, ?, ?, ?, ?, ?)",
                           ('Pagamento', str(interaction.user.id), interaction.user.name, str(interaction.guild_id), f'R$ {valor:.2f} - {nome}', agora))
            cog.conn.commit()
            
            try: await interaction.user.send(f"🔍 **Diagnóstico SyncPay:**\n```json\n{json.dumps(dados, indent=2)}\n```")
            except: pass

            qr = dados.get("qr_code") or dados.get("pix_code") or dados.get("emv") or dados.get("code") or "Código não encontrado."
            embed = discord.Embed(title=f"💎 Pagamento: {nome}", description=f"**Valor:** R$ {valor:.2f}\n\n**Pix Copia e Cola:**\n```{qr}```", color=discord.Color.gold())
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send("❌ Erro na API. Veja o DM.")
            try: await interaction.user.send(f"❌ **Erro:** {e.response.text if hasattr(e, 'response') else e}")
            except: pass

async def setup(bot):
    await bot.add_cog(Pagamentos(bot))
