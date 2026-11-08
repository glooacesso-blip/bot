import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import requests
import datetime

class Pagamentos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('tickets.db')
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS gateway_config (
                guild_id TEXT PRIMARY KEY,
                api_key TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS vips (
                user_id TEXT PRIMARY KEY,
                guild_id TEXT,
                expira_em TEXT
            )
        ''')
        self.conn.commit()

    @app_commands.command(name="configurar-pagamento", description="Configura a API Key da Atenas Pay para este servidor.")
    @app_commands.checks.has_permissions(administrator=True)
    async def configurar_pagamento(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalConfigurarAPI())

    @app_commands.command(name="painel-vip", description="Cria o painel de vendas do VIP no canal.")
    @app_commands.checks.has_permissions(administrator=True)
    async def painel_vip(self, interaction: discord.Interaction, imagem: str = None, texto: str = "Adquira o VIP e tenha benefícios exclusivos!"):
        self.cursor.execute("SELECT api_key FROM gateway_config WHERE guild_id = ?", (str(interaction.guild_id),))
        result = self.cursor.fetchone()
        
        if not result:
            await interaction.response.send_message("❌ Este servidor ainda não configurou a API Key da Atenas Pay. Use `/configurar-pagamento` primeiro.", ephemeral=True)
            return

        embed = discord.Embed(
            title="💎 Torne-se VIP na TRAMA!",
            description=texto,
            color=discord.Color.gold()
        )
        if imagem:
            embed.set_image(url=imagem)
        embed.add_field(name="Benefícios:", value="✅ Cargo exclusivo\n✅ Canais privados\n✅ Sorteios exclusivos", inline=False)
        embed.set_footer(text="Clique no botão abaixo para comprar")
        
        await interaction.response.send_message("Painel VIP criado!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=BotaoComprarVIP())

    async def criar_cobranca_pix(self, interaction: discord.Interaction, api_key: str):
        payload = {
            "amount": 29.90,
            "external_id": str(interaction.user.id),
            "webhook_url": "https://seu-site.onrender.com/webhook" # Troque pelo link do seu site
        }
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post("https://atenaspay.com.br/api/pix/create", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            print(f"Erro na API da Atenas: {e}")
            return None

class ModalConfigurarAPI(discord.ui.Modal, title="Configurar Atenas Pay"):
    api_key = discord.ui.TextInput(
        label="API Key da Atenas Pay",
        placeholder="Cole sua chave aqui (x-api-key)...",
        required=True,
        style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Pagamentos")
        if not cog:
            await interaction.response.send_message("❌ Módulo de pagamentos não carregado.", ephemeral=True)
            return
            
        cog.cursor.execute("INSERT OR REPLACE INTO gateway_config VALUES (?, ?)", (str(interaction.guild_id), self.api_key.value))
        cog.conn.commit()
        
        await interaction.response.send_message("✅ API Key da Atenas Pay configurada com sucesso para este servidor!", ephemeral=True)

class BotaoComprarVIP(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Comprar VIP", style=discord.ButtonStyle.success, emoji="💎", custom_id="btn_comprar_vip_v5")
    async def comprar(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("Pagamentos")
        if not cog:
            await interaction.response.send_message("❌ Módulo de pagamentos não carregado.", ephemeral=True)
            return

        # 1. Verifica se a API Key está configurada
        cog.cursor.execute("SELECT api_key FROM gateway_config WHERE guild_id = ?", (str(interaction.guild_id),))
        result = cog.cursor.fetchone()
        
        if not result:
            await interaction.response.send_message("❌ O administrador deste servidor ainda não configurou a API Key da Atenas Pay.", ephemeral=True)
            return

        api_key = result[0]
        
        # 2. Cria o canal privado para a venda
        guild = interaction.guild
        nome_canal = f"venda-vip-{interaction.user.name.lower()}"
        
        # Verifica se a pessoa já tem um canal de venda aberto
        canal_existente = discord.utils.get(guild.text_channels, name=nome_canal)
        if canal_existente:
            await interaction.response.send_message(f"❌ Você já tem uma venda em andamento: {canal_existente.mention}", ephemeral=True)
            return

        # Cria o canal com permissões (só o usuário, a staff e o bot veem)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        canal = await guild.create_text_channel(nome_canal, overwrites=overwrites, category=None)
        
        # 3. Avisa o usuário que o canal foi criado
        await interaction.response.send_message(f"✅ Seu canal de compra foi criado: {canal.mention}", ephemeral=True)
        
        # 4. Gera o Pix
        dados_pix = await cog.criar_cobranca_pix(interaction, api_key)
        
        # 5. Envia a mensagem com o QR Code dentro do canal criado
        if not dados_pix:
            await canal.send("❌ Erro ao gerar o Pix. A Staff foi notificada.")
            return

        # Tenta pegar o código de várias formas diferentes
        qr_code_texto = (
            dados_pix.get("qr_code") or 
            dados_pix.get("pix_code") or 
            dados_pix.get("emv") or 
            dados_pix.get("brcode") or 
            "Código não encontrado."
        )

        # Tenta pegar o link da imagem do QR Code
        qr_code_imagem = (
            dados_pix.get("qr_code_image") or 
            dados_pix.get("qr_code_url") or 
            dados_pix.get("image_url")
        )

        embed = discord.Embed(
            title="💎 Pagamento VIP via Pix",
            description=f"**Valor:** R$ 29,90\n\n**Pix Copia e Cola:**\n```{qr_code_texto}```\n\nApós o pagamento, seu VIP será liberado automaticamente e a Staff irá fechar este canal.",
            color=discord.Color.gold()
        )
        
        if qr_code_imagem:
            embed.set_image(url=qr_code_imagem)
            
        embed.set_footer(text="Obrigado por apoiar a TRAMA!")
        
        await canal.send(embed=embed)
