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
        
        # Tabela de Configuração da API
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS gateway_config (
                guild_id TEXT PRIMARY KEY,
                api_key TEXT
            )
        ''')
        # Tabela de Textos Personalizados
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS mensagens_vip (
                guild_id TEXT PRIMARY KEY,
                titulo_painel TEXT,
                desc_painel TEXT,
                msg_canal TEXT,
                texto_botao TEXT
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

    def get_textos(self, guild_id):
        # Busca os textos no banco, se não tiver, usa o padrão
        self.cursor.execute("SELECT titulo_painel, desc_painel, msg_canal, texto_botao FROM mensagens_vip WHERE guild_id = ?", (str(guild_id),))
        row = self.cursor.fetchone()
        if row:
            return {
                "titulo": row[0] or "💎 Torne-se VIP na TRAMA!",
                "desc": row[1] or "Adquira o VIP e tenha benefícios exclusivos!",
                "msg_canal": row[2] or "Escolha seu plano abaixo para continuar.",
                "botao": row[3] or "Comprar VIP"
            }
        return {
            "titulo": "💎 Torne-se VIP na TRAMA!",
            "desc": "Adquira o VIP e tenha benefícios exclusivos!",
            "msg_canal": "Escolha seu plano abaixo para continuar.",
            "botao": "Comprar VIP"
        }

    @app_commands.command(name="configurar-pagamento", description="Configura a API Key da Atenas Pay para este servidor.")
    @app_commands.checks.has_permissions(administrator=True)
    async def configurar_pagamento(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalConfigurarAPI())

    @app_commands.command(name="configurar-mensagens", description="Muda os textos do painel e da venda VIP.")
    @app_commands.checks.has_permissions(administrator=True)
    async def configurar_mensagens(self, interaction: discord.Interaction):
        # Busca os textos atuais para mostrar no Modal
        atuais = self.get_textos(interaction.guild_id)
        await interaction.response.send_modal(ModalConfigurarMensagens(atuais))

    @app_commands.command(name="painel-vip", description="Cria o painel de vendas do VIP no canal.")
    @app_commands.checks.has_permissions(administrator=True)
    async def painel_vip(self, interaction: discord.Interaction, imagem: str = None):
        self.cursor.execute("SELECT api_key FROM gateway_config WHERE guild_id = ?", (str(interaction.guild_id),))
        result = self.cursor.fetchone()
        
        if not result:
            await interaction.response.send_message("❌ Este servidor ainda não configurou a API Key da Atenas Pay.", ephemeral=True)
            return

        textos = self.get_textos(interaction.guild_id)

        embed = discord.Embed(
            title=textos["titulo"],
            description=textos["desc"],
            color=discord.Color.gold()
        )
        if imagem:
            embed.set_image(url=imagem)
        embed.set_footer(text="Segurança garantida pela TRAMA")
        
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
            
            # DIAGNÓSTICO NO LOG
            print("=========================================")
            print("RESPOSTA DA ATENAS PAY:", dados)
            print("=========================================")
            
            return dados
        except Exception as e:
            print(f"Erro na API da Atenas: {e}")
            return None

# --- MODAIS DE CONFIGURAÇÃO ---

class ModalConfigurarAPI(discord.ui.Modal, title="Configurar Atenas Pay"):
    api_key = discord.ui.TextInput(label="API Key da Atenas Pay", placeholder="Cole sua chave aqui...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Pagamentos")
        cog.cursor.execute("INSERT OR REPLACE INTO gateway_config VALUES (?, ?)", (str(interaction.guild_id), self.api_key.value))
        cog.conn.commit()
        await interaction.response.send_message("✅ API Key configurada!", ephemeral=True)

class ModalConfigurarMensagens(discord.ui.Modal, title="Personalizar Mensagens VIP"):
    def __init__(self, atuais):
        super().__init__()
        
        # Campo 1: Título do Painel
        self.titulo = discord.ui.TextInput(
            label="Título do Painel",
            default=atuais["titulo"],
            required=True,
            max_length=100
        )
        self.add_item(self.titulo)
        
        # Campo 2: Descrição do Painel
        self.desc = discord.ui.TextInput(
            label="Descrição do Painel",
            default=atuais["desc"],
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500
        )
        self.add_item(self.desc)
        
        # Campo 3: Texto que vai dentro do canal criado
        self.msg_canal = discord.ui.TextInput(
            label="Mensagem dentro do Canal",
            default=atuais["msg_canal"],
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500
        )
        self.add_item(self.msg_canal)
        
        # Campo 4: Texto do Botão
        self.texto_botao = discord.ui.TextInput(
            label="Texto do Botão (Comprar)",
            default=atuais["botao"],
            required=True,
            max_length=40
        )
        self.add_item(self.texto_botao)

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Pagamentos")
        
        # Salva no banco
        cog.cursor.execute('''
            INSERT OR REPLACE INTO mensagens_vip (guild_id, titulo_painel, desc_painel, msg_canal, texto_botao)
            VALUES (?, ?, ?, ?, ?)
        ''', (str(interaction.guild_id), self.titulo.value, self.desc.value, self.msg_canal.value, self.texto_botao.value))
        cog.conn.commit()
        
        await interaction.response.send_message("✅ Mensagens personalizadas com sucesso! Use `/painel-vip` para ver o resultado.", ephemeral=True)


# --- BOTÕES E MENUS DO DISCORD ---

class BotaoComprarVIP(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Comprar VIP", style=discord.ButtonStyle.success, emoji="💎", custom_id="btn_comprar_vip_v9")
    async def comprar(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        cog = interaction.client.get_cog("Pagamentos")
        textos = cog.get_textos(guild.id)
        
        # Muda o texto do botão dinamicamente
        button.label = textos["botao"]
        
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
            description=textos["msg_canal"],
            color=discord.Color.gold()
        )
        
        await canal.send(content=f"{interaction.user.mention}", embed=embed, view=MenuPlanos())
        await interaction.response.send_message(f"✅ Canal criado: {canal.mention}", ephemeral=True)

class MenuPlanos(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="VIP Básico - R$ 9,90", style=discord.ButtonStyle.secondary, emoji="🥉", custom_id="btn_plano_basico_v9")
    async def plano_basico(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.processar_pagamento(interaction, 9.90, "Básico")

    @discord.ui.button(label="VIP Premium - R$ 19,90", style=discord.ButtonStyle.primary, emoji="🥈", custom_id="btn_plano_premium_v9")
    async def plano_premium(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.processar_pagamento(interaction, 19.90, "Premium")

    @discord.ui.button(label="VIP Master - R$ 29,90", style=discord.ButtonStyle.success, emoji="🥇", custom_id="btn_plano_master_v9")
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
            embed_erro = discord.Embed(title="❌ Erro no Pagamento", description="Não foi possível gerar o Pix. Verifique se a API Key está correta.", color=discord.Color.red())
            await interaction.followup.send(embed=embed_erro, view=BotaoTentarNovamente(valor, nome_plano))
            return

        qr_code_texto = (
            dados_pix.get("qr_code") or dados_pix.get("pix_code") or dados_pix.get("emv") or 
            dados_pix.get("brcode") or dados_pix.get("code") or dados_pix.get("qrcode") or 
            dados_pix.get("pixCopiaECola") or "Código não encontrado. Verifique o Log do Render."
        )

        qr_code_imagem = dados_pix.get("qr_code_image") or dados_pix.get("qr_code_url") or dados_pix.get("image_url") or dados_pix.get("qrCodeImage")

        embed = discord.Embed(
            title=f"💎 Pagamento: Plano {nome_plano}",
            description=f"**Valor:** R$ {valor:.2f}\n\n**Pix Copia e Cola:**\n```{qr_code_texto}```\n\nApós o pagamento, seu VIP será liberado automaticamente.",
            color=discord.Color.gold()
        )
        if qr_code_imagem: embed.set_image(url=qr_code_imagem)
        embed.set_footer(text="Método escolhido: Pix")
        await interaction.followup.send(embed=embed)

class BotaoTentarNovamente(discord.ui.View):
    def __init__(self, valor, nome_plano):
        super().__init__(timeout=None)
        self.valor = valor
        self.nome_plano = nome_plano

    @discord.ui.button(label="Tentar Novamente", style=discord.ButtonStyle.primary, emoji="🔄")
    async def tentar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await MenuPlanos().processar_pagamento(interaction, self.valor, self.nome_plano)

async def setup(bot):
    await bot.add_cog(Pagamentos(bot))
