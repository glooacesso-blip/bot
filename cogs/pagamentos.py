import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import requests
import json

class Pagamentos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('tickets.db')
        self.cursor = self.conn.cursor()
        
        # Configuração da SyncPay
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS syncpay_config (
                guild_id TEXT PRIMARY KEY,
                public_token TEXT,
                secret_token TEXT
            )
        ''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS mensagens_vip (guild_id TEXT PRIMARY KEY, titulo_painel TEXT, desc_painel TEXT, msg_canal TEXT, texto_botao TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS vips (user_id TEXT PRIMARY KEY, guild_id TEXT, expira_em TEXT)''')
        self.conn.commit()

    def get_textos(self, guild_id):
        self.cursor.execute("SELECT titulo_painel, desc_painel, msg_canal, texto_botao FROM mensagens_vip WHERE guild_id = ?", (str(guild_id),))
        row = self.cursor.fetchone()
        if row:
            return {"titulo": row[0] or "💎 Torne-se VIP na TRAMA!", "desc": row[1] or "Adquira o VIP!", "msg_canal": row[2] or "Escolha seu plano:", "botao": row[3] or "Comprar VIP"}
        return {"titulo": "💎 Torne-se VIP na TRAMA!", "desc": "Adquira o VIP!", "msg_canal": "Escolha seu plano:", "botao": "Comprar VIP"}

    @app_commands.command(name="configurar-syncpay", description="Configura as chaves (Public e Secret) da SyncPay.")
    @app_commands.checks.has_permissions(administrator=True)
    async def configurar_syncpay(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalConfigurarSyncPay())

    @app_commands.command(name="configurar-mensagens", description="Muda os textos do painel VIP.")
    @app_commands.checks.has_permissions(administrator=True)
    async def configurar_mensagens(self, interaction: discord.Interaction):
        atuais = self.get_textos(interaction.guild_id)
        await interaction.response.send_modal(ModalConfigurarMensagens(atuais))

    @app_commands.command(name="painel-vip", description="Cria o painel de vendas.")
    @app_commands.checks.has_permissions(administrator=True)
    async def painel_vip(self, interaction: discord.Interaction, imagem: str = None):
        self.cursor.execute("SELECT 1 FROM syncpay_config WHERE guild_id = ?", (str(interaction.guild_id),))
        if not self.cursor.fetchone():
            await interaction.response.send_message("❌ Configure as chaves da SyncPay primeiro com `/configurar-syncpay`.", ephemeral=True)
            return

        textos = self.get_textos(interaction.guild_id)
        embed = discord.Embed(title=textos["titulo"], description=textos["desc"], color=discord.Color.gold())
        if imagem: embed.set_image(url=imagem)
        
        await interaction.response.send_message("Painel criado!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=BotaoComprarVIP())

    async def gerar_pix_syncpay(self, interaction: discord.Interaction, public_token: str, secret_token: str, valor: float):
        # URL baseada nos exemplos da comunidade: https://api.syncpay.pro/v1/gateway/api/
        url = "https://api.syncpay.pro/v1/gateway/api/pix/cashIn"
        
        # Payload baseado na estrutura da biblioteca syncpay [citation:3][citation:5]
        payload = {
            "amount": valor,
            "client": {
                "name": interaction.user.name,
                "email": f"{interaction.user.id}@discord.com",
                "cpf": "00000000000" # CPF fictício, pois o Discord não fornece
            },
            "webhook_url": "https://seu-site.onrender.com/webhook"
        }
        
        # Headers: Vamos testar o padrão mais comum para APIs que usam Public/Secret
        # Algumas usam Bearer, outras usam headers customizados. Vamos tentar o mais comum.
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {secret_token}",
            "x-public-key": public_token
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            dados = response.json()
            
            # DIAGNÓSTICO POR DM
            try:
                await interaction.user.send(f"🔍 **Diagnóstico SyncPay:**\n```json\n{json.dumps(dados, indent=2)}\n```")
            except: pass
            
            return dados
        except Exception as e:
            print(f"Erro SyncPay: {e}")
            try:
                # Tenta capturar a resposta de erro da API para mostrar no DM
                erro_detalhado = e.response.text if hasattr(e, 'response') else str(e)
                await interaction.user.send(f"❌ **Erro SyncPay:**\n```{erro_detalhado}```")
            except: pass
            return None

# --- MODAIS ---
class ModalConfigurarSyncPay(discord.ui.Modal, title="Configurar SyncPay"):
    public_token = discord.ui.TextInput(label="Public Token", placeholder="Cole o Public Token aqui...", required=True)
    secret_token = discord.ui.TextInput(label="Secret Token", placeholder="Cole o Secret Token aqui...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Pagamentos")
        cog.cursor.execute("INSERT OR REPLACE INTO syncpay_config VALUES (?, ?, ?)", 
                           (str(interaction.guild_id), self.public_token.value, self.secret_token.value))
        cog.conn.commit()
        await interaction.response.send_message("✅ Chaves da SyncPay configuradas com sucesso!", ephemeral=True)

class ModalConfigurarMensagens(discord.ui.Modal, title="Personalizar Mensagens VIP"):
    def __init__(self, atuais):
        super().__init__()
        self.titulo = discord.ui.TextInput(label="Título do Painel", default=atuais["titulo"], max_length=100)
        self.desc = discord.ui.TextInput(label="Descrição do Painel", default=atuais["desc"], style=discord.TextStyle.paragraph)
        self.msg_canal = discord.ui.TextInput(label="Mensagem dentro do Canal", default=atuais["msg_canal"], style=discord.TextStyle.paragraph)
        self.texto_botao = discord.ui.TextInput(label="Texto do Botão (Comprar)", default=atuais["botao"], max_length=40)
        self.add_item(self.titulo)
        self.add_item(self.desc)
        self.add_item(self.msg_canal)
        self.add_item(self.texto_botao)

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Pagamentos")
        cog.cursor.execute('''
            INSERT OR REPLACE INTO mensagens_vip (guild_id, titulo_painel, desc_painel, msg_canal, texto_botao)
            VALUES (?, ?, ?, ?, ?)
        ''', (str(interaction.guild_id), self.titulo.value, self.desc.value, self.msg_canal.value, self.texto_botao.value))
        cog.conn.commit()
        await interaction.response.send_message("✅ Mensagens personalizadas!", ephemeral=True)

# --- BOTÕES ---
class BotaoComprarVIP(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="Comprar VIP", style=discord.ButtonStyle.success, emoji="💎", custom_id="btn_comprar_vip_v12")
    async def comprar(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("Pagamentos")
        textos = cog.get_textos(interaction.guild_id)
        button.label = textos["botao"]
        
        nome_canal = f"venda-vip-{interaction.user.name.lower()}"
        canal_existente = discord.utils.get(interaction.guild.text_channels, name=nome_canal)
        if canal_existente:
            await interaction.response.send_message(f"❌ Você já tem uma venda aberta: {canal_existente.mention}", ephemeral=True)
            return

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        canal = await interaction.guild.create_text_channel(nome_canal, overwrites=overwrites)
        embed = discord.Embed(title="💎 Escolha seu Plano VIP", description=textos["msg_canal"], color=discord.Color.gold())
        await canal.send(content=f"{interaction.user.mention}", embed=embed, view=MenuPlanos())
        await interaction.response.send_message(f"✅ Canal criado: {canal.mention}", ephemeral=True)

class MenuPlanos(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="VIP Básico - R$ 9,90", style=discord.ButtonStyle.secondary, emoji="🥉", custom_id="btn_plano_basico_v12")
    async def plano_basico(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.processar_pagamento(interaction, 9.90, "Básico")

    @discord.ui.button(label="VIP Premium - R$ 19,90", style=discord.ButtonStyle.primary, emoji="🥈", custom_id="btn_plano_premium_v12")
    async def plano_premium(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.processar_pagamento(interaction, 19.90, "Premium")

    @discord.ui.button(label="VIP Master - R$ 29,90", style=discord.ButtonStyle.success, emoji="🥇", custom_id="btn_plano_master_v12")
    async def plano_master(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.processar_pagamento(interaction, 29.90, "Master")

    async def processar_pagamento(self, interaction: discord.Interaction, valor: float, nome_plano: str):
        cog = interaction.client.get_cog("Pagamentos")
        
        cog.cursor.execute("SELECT public_token, secret_token FROM syncpay_config WHERE guild_id = ?", (str(interaction.guild_id),))
        syncpay = cog.cursor.fetchone()

        if not syncpay:
            await interaction.response.send_message("❌ Nenhum gateway SyncPay configurado.", ephemeral=True)
            return

        await interaction.response.defer()
        
        dados_pix = await cog.gerar_pix_syncpay(interaction, syncpay[0], syncpay[1], valor)
        
        if not dados_pix:
            await interaction.followup.send("❌ Erro ao gerar o Pix na SyncPay. Verifique seu privado (DM) para ver o diagnóstico.")
            return

        qr_code_texto = (
            dados_pix.get("qr_code") or dados_pix.get("pix_code") or dados_pix.get("emv") or 
            dados_pix.get("brcode") or dados_pix.get("code") or dados_pix.get("qrcode") or 
            dados_pix.get("pixCopiaECola") or dados_pix.get("copia_e_cola") or
            "Código não encontrado. Verifique o DM."
        )

        qr_code_imagem = dados_pix.get("qr_code_image") or dados_pix.get("qr_code_url") or dados_pix.get("image_url") or dados_pix.get("qrCodeImage")

        embed = discord.Embed(
            title=f"💎 Pagamento: Plano {nome_plano}",
            description=f"**Valor:** R$ {valor:.2f}\n\n**Pix Copia e Cola:**\n```{qr_code_texto}```\n\nApós o pagamento, seu VIP será liberado.",
            color=discord.Color.gold()
        )
        if qr_code_imagem: embed.set_image(url=qr_code_imagem)
        embed.set_footer(text="Método escolhido: Pix (SyncPay)")
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Pagamentos(bot))
