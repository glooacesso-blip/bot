    # ==========================================
    # COMANDO: /valorant-tracker (ATUALIZADO)
    # ==========================================
    @app_commands.command(name="valorant-tracker", description="Mostra as estatísticas de um jogador de Valorant.")
    @app_commands.describe(nome="Nome de usuário (ex: TenZ#NA1)")
    async def valorant_tracker(self, interaction: discord.Interaction, nome: str):
        await interaction.response.defer()
        
        if "#" not in nome:
            await interaction.followup.send("❌ O nome deve estar no formato `Nome#TAG` (ex: TenZ#NA1).")
            return
            
        nome_formatado = nome.replace("#", "/")
        
        # Usando a versão v2 da API do HenrikDev (mais estável)
        url = f"https://api.henrikdev.xyz/valorant/v2/mmr/na/{nome_formatado}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    # Tenta a versão v1 se a v2 falhar
                    url_v1 = f"https://api.henrikdev.xyz/valorant/v1/mmr/na/{nome_formatado}"
                    async with session.get(url_v1) as response_v1:
                        if response_v1.status != 200:
                            await interaction.followup.send("❌ Jogador não encontrado ou API indisponível no momento.")
                            return
                        data = await response_v1.json()
                else:
                    data = await response.json()
                
        try:
            # A estrutura da resposta v2 é um pouco diferente
            if "data" in data and "current" in data["data"]:
                elo = data["data"]["current"]["tier"]["name"]
                pontos = data["data"]["current"]["rr"]
            else:
                # Formato antigo (v1)
                elo = data["data"]["currenttierpatched"]
                pontos = data["data"]["ranking_in_tier"]
                
            embed = discord.Embed(title=f"🎯 Valorant: {nome}", color=0xFF4655)
            embed.add_field(name="Rank Atual", value=f"**{elo}**", inline=True)
            embed.add_field(name="Pontos (RR)", value=f"**{pontos}**", inline=True)
            embed.set_footer(text="Dados via HenrikDev API")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao ler os dados: {e}")
