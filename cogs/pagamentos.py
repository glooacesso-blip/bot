    # --- FUNÇÃO AUXILIAR PARA CRIAR O PIX ---
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


# --- BOTÃO DE COMPRAR VIP (AGORA COM QR CODE) ---
class BotaoComprarVIP(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Comprar VIP", style=discord.ButtonStyle.success, emoji="💎", custom_id="btn_comprar_vip_v4")
    async def comprar(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("Pagamentos")
        if not cog:
            await interaction.response.send_message("❌ Módulo de pagamentos não carregado.", ephemeral=True)
            return

        cog.cursor.execute("SELECT api_key FROM gateway_config WHERE guild_id = ?", (str(interaction.guild_id),))
        result = cog.cursor.fetchone()
        
        if not result:
            await interaction.response.send_message("❌ O administrador deste servidor ainda não configurou a API Key.", ephemeral=True)
            return

        api_key = result[0]
        await interaction.response.defer(ephemeral=True) # Avisa o Discord que vai demorar

        dados_pix = await cog.criar_cobranca_pix(interaction, api_key)
        
        if not dados_pix:
            await interaction.followup.send("❌ Erro ao gerar o Pix. Verifique se a API Key está correta ou tente novamente.", ephemeral=True)
            return

        # DEBUG: Imprime no console do Render o que a API retornou para sabermos os nomes exatos
        print("RESPOSTA DA API ATENAS:", dados_pix)

        # Tenta pegar o código de várias formas diferentes (dependendo de como a API responde)
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
            description=f"**Valor:** R$ 29,90\n\n**Pix Copia e Cola:**\n```{qr_code_texto}```\n\nApós o pagamento, seu VIP será liberado automaticamente.",
            color=discord.Color.gold()
        )
        
        # Se a API retornar um link direto da imagem, coloca no embed
        if qr_code_imagem:
            embed.set_image(url=qr_code_imagem)
            
        embed.set_footer(text="Obrigado por apoiar a TRAMA!")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
