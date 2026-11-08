import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import requests

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
        embed.set_footer(text="Clique no botão abaixo para abrir seu canal de compra.")
        
        await interaction.response.send_message("Painel VIP criado!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=BotaoComprarVIP())

    async def gerar_pix(self, interaction: discord.Interaction, api_key: str, valor: float):
        payload = {
            "amount": valor,
            "external_id": str(interaction.user.id),
            "webhook_url": "https://seu-site.onrender.com/webhook"
        }
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        
        try:
            response = requests.post("https://atenaspay.com.br/api/pix/create", json=payload, headers=headers)
            response.raise_for_status()
            dados = response.json()
            
            # DIAGNÓSTICO: Mostra no log do Render o que a Atenas Pay retornou
            print("=========================================")
            print("RESPOSTA DA ATENAS PAY:", dados)
            print("=========================================")
            
            return dados
        except Exception as e:
            print(f"Erro na API da Atenas: {e}")
            return None

class ModalConfigurarAPI(discord.ui.Modal, title="Configurar Atenas Pay"):
    api_key = discord.ui.TextInput(label="API Key da Atenas Pay", placeholder="Cole sua chave aqui...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Pagamentos")
        cog.cursor.execute("INSERT OR REPLACE INTO gateway_config VALUES (?, ?)", (str(interaction.guild_id), self.api_key.value))
        cog.conn.commit()
        await interaction.response.send_message("✅ API Key configurada!", ephemeral=True)

# --- BOTÃO DO PAINEL (CRIA O CANAL) ---
class BotaoComprarVIP(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Comprar VIP", style=discord.ButtonStyle.success, emoji="💎", custom_id="btn_comprar_vip_v8")
    async def comprar(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        nome_canal = f"venda-vip-{interaction.user.name.lower()}"
        
        canal_existente = discord.utils.get(guild.text_channels, name=nome_canal)
        if canal_existente:
            await interaction.response.send_message(f"❌ Você já tem uma venda aberta: {canal_existente.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        canal = await guild.create_text_channel(nome_canal, overwrites=overwrites)
        
        embed = discord.Embed(
            title="💎 Escolha seu Plano VIP",
            description="Selecione abaixo o plano que você deseja adquirir:",
            color=discord.Color.gold()
        )
        
        await canal.send(content=f"{interaction.user.mention}", embed=embed, view=MenuPlanos())
        await interaction.response.send_message(f"✅ Canal criado: {canal.mention}", ephemeral=True)

# --- MENU DE PLANOS (DENTRO DO CANAL) ---
class MenuPlanos(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="VIP Básico - R$ 9,90", style=discord.ButtonStyle.secondary, emoji="🥉", custom_id="btn_plano_basico_v8")
    async def plano_basico(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.processar_pagamento(interaction, 9.90, "Básico")

    @discord.ui.button(label="VIP Premium - R$ 19,90", style=discord.ButtonStyle.primary, emoji="🥈", custom_id="btn_plano_premium_v8")
    async def plano_premium(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.processar_pagamento(interaction, 19.90, "Premium")

    @discord.ui.button(label="VIP Master - R$ 29,90", style=discord.ButtonStyle.success, emoji="🥇", custom_id="btn_plano_master_v8")
    async def plano_master(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.processar_pagamento(interaction, 29.90, "Master")

    async def processar_pagamento(self, interaction: discord.Interaction, valor: float, nome_plano: str):
        cog = interaction.client.get_cog("Pagamentos")
        cog.cursor.execute("SELECT api_key FROM gateway_config WHERE guild_id = ?", (str(interaction.guild_id),))
        result = cog.cursor.fetchone()
        
        if not result:
            await interaction.response.send_message("❌ API Key não configurada.", ephemeral=True)
            return

        await interaction.response.defer()
        
        dados_pix = await cog.gerar_pix(interaction, result[0], valor)
        
        if not dados_pix:
            # Se der erro, manda uma mensagem com botão para tentar de novo
            embed_erro = discord.Embed(title="❌ Erro no Pagamento", description="Não foi possível gerar o Pix. Verifique se a API Key está correta.", color=discord.Color.red())
            await interaction.followup.send(embed=embed_erro, view=BotaoTentarNovamente(valor, nome_plano))
            return

        # Tenta pegar o código de TODAS as formas possíveis (para descobrir qual a Atenas usa)
        qr_code_texto = (
            dados_pix.get("qr_code") or 
            dados_pix.get("pix_code") or 
            dados_pix.get("emv") or 
            dados_pix.get("brcode") or
            dados_pix.get("code") or
            dados_pix.get("qrcode") or
            dados_pix.get("pixCopiaECola") or
            "Código não encontrado. Verifique o Log do Render."
        )

        # Tenta pegar o link da imagem do QR Code
        qr_code_imagem = (
            dados_pix.get("qr_code_image") or 
            dados_pix.get("qr_code_url") or 
            dados_pix.get("image_url") or
            dados_pix.get("qrCodeImage")
        )

        embed = discord.Embed(
            title=f"💎 Pagamento: Plano {nome_plano}",
            description=f"**Valor:** R$ {valor:.2f}\n\n**Pix Copia e Cola:**\n```{qr_code_texto}```\n\nApós o pagamento, seu VIP será liberado automaticamente.",
            color=discord.Color.gold()
        )
        
        if qr_code_imagem:
            embed.set_image(url=qr_code_imagem)
            
        embed.set_footer(text="Método escolhido: Pix")
        await interaction.followup.send(embed=embed)


# --- BOTÃO DE TENTAR NOVAMENTE (SE DER ERRO) ---
class BotaoTentarNovamente(discord.ui.View):
    def __init__(self, valor, nome_plano):
        super().__init__(timeout=None)
        self.valor = valor
        self.nome_plano = nome_plano

    @discord.ui.button(label="Tentar Novamente", style=discord.ButtonStyle.primary, emoji="🔄")
    async def tentar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Chama a função de pagamento do MenuPlanos novamente
        await MenuPlanos().processar_pagamento(interaction, self.valor, self.nome_plano)

async def setup(bot):
    await bot.add_cog(Pagamentos(bot))
