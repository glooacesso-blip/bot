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
        
        # Cria a tabela para guardar a API Key de cada servidor
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS gateway_config (
                guild_id TEXT PRIMARY KEY,
                api_key TEXT
            )
        ''')
        # Tabela de VIPs (já existia, mas garantimos que está aqui)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS vips (
                user_id TEXT PRIMARY KEY,
                guild_id TEXT,
                expira_em TEXT
            )
        ''')
        self.conn.commit()

    # --- COMANDO PARA CONFIGURAR A API KEY ---
    @app_commands.command(name="configurar-pagamento", description="Configura a API Key da Atenas Pay para este servidor.")
    @app_commands.checks.has_permissions(administrator=True)
    async def configurar_pagamento(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalConfigurarAPI())

    # --- COMANDO PARA CRIAR O PAINEL DE VENDAS ---
    @app_commands.command(name="painel-vip", description="Cria o painel de vendas do VIP no canal (usa a API Key do servidor).")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(imagem="Link do banner do VIP (Opcional)", texto="Texto explicativo")
    async def painel_vip(self, interaction: discord.Interaction, imagem: str = None, texto: str = "Adquira o VIP e tenha benefícios exclusivos!"):
        # Verifica se o servidor já configurou a API Key
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

    # --- FUNÇÃO AUXILIAR PARA CRIAR O PIX (Chamada pelo Botão) ---
    async def criar_cobranca_pix(self, interaction: discord.Interaction, api_key: str):
        # 1. Dados da cobrança (Valor fixo de exemplo, você pode mudar)
        payload = {
            "amount": 29.90,
            "external_id": str(interaction.user.id), # ID do usuário para identificar no webhook
            "webhook_url": "https://seu-site.onrender.com/webhook" # URL do seu site no Render
        }
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        try:
            # 2. Faz a requisição para a Atenas Pay
            response = requests.post("https://atenaspay.com.br/api/pix/create", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # 3. Retorna os dados do Pix (QR Code e Copia e Cola)
            return data
        except Exception as e:
            print(f"Erro na API da Atenas: {e}")
            return None

# --- MODAL PARA COLETAR A API KEY ---
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
            
        # Salva a chave no banco de dados
        cog.cursor.execute("INSERT OR REPLACE INTO gateway_config VALUES (?, ?)", (str(interaction.guild_id), self.api_key.value))
        cog.conn.commit()
        
        await interaction.response.send_message("✅ API Key da Atenas Pay configurada com sucesso para este servidor!", ephemeral=True)

# --- BOTÃO DE COMPRAR VIP (AGORA ELE GERA O PIX) ---
class BotaoComprarVIP(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Comprar VIP", style=discord.ButtonStyle.success, emoji="💎", custom_id="btn_comprar_vip_v3")
    async def comprar(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("Pagamentos")
        if not cog:
            await interaction.response.send_message("❌ Módulo de pagamentos não carregado.", ephemeral=True)
            return

        # Busca a API Key do servidor no banco
        cog.cursor.execute("SELECT api_key FROM gateway_config WHERE guild_id = ?", (str(interaction.guild_id),))
        result = cog.cursor.fetchone()
        
        if not result:
            await interaction.response.send_message("❌ O administrador deste servidor ainda não configurou a API Key da Atenas Pay.", ephemeral=True)
            return

        api_key = result[0]
        await interaction.response.defer(ephemeral=True) # Evita o erro de "interação falhou"

        # Chama a função que cria o Pix
        dados_pix = await cog.criar_cobranca_pix(interaction, api_key)
        
        if not dados_pix:
            await interaction.followup.send("❌ Erro ao gerar o Pix. Verifique se a API Key está correta ou tente novamente mais tarde.", ephemeral=True)
            return

        # Monta a mensagem com o Pix (QR Code e Copia e Cola)
        # A API da Atenas deve retornar algo como 'qr_code' (texto) e 'qr_code_image' (link da imagem)
        qr_code_texto = dados_pix.get("qr_code", "Código não retornado")
        qr_code_imagem = dados_pix.get("qr_code_image") # Se a API retornar a imagem

        embed = discord.Embed(
            title="💎 Pagamento VIP via Pix",
            description=f"**Valor:** R$ 29,90\n\n**Pix Copia e Cola:**\n```{qr_code_texto}```\n\nApós o pagamento, seu VIP será liberado automaticamente.",
            color=discord.Color.gold()
        )
        
        if qr_code_imagem:
            embed.set_image(url=qr_code_imagem)
            
        embed.set_footer(text="Obrigado por apoiar a TRAMA!")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Pagamentos(bot))
