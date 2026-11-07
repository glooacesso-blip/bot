import discord
from discord import app_commands
from discord.ext import commands
import os
from instagrapi import Client

# Tenta importar o tweepy (pode não estar configurado)
try:
    import tweepy
    TWEEPY_DISPONIVEL = True
except ImportError:
    TWEEPY_DISPONIVEL = False

class RedesSociais(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # --- CONFIGURAÇÃO DO INSTAGRAM ---
        # É recomendável usar variáveis de ambiente, mas para teste você pode colocar aqui
        self.ig_usuario = os.getenv("IG_USER") 
        self.ig_senha = os.getenv("IG_PASS")
        self.cliente_ig = None
        
        # --- CONFIGURAÇÃO DO TWITTER ---
        self.twitter_bearer = os.getenv("TWITTER_BEARER_TOKEN")
        self.cliente_twitter = None
        if TWEEPY_DISPONIVEL and self.twitter_bearer:
            try:
                self.cliente_twitter = tweepy.Client(bearer_token=self.twitter_bearer)
            except Exception as e:
                print(f"Erro ao configurar Twitter: {e}")

    # --- COMANDO /INSTAGRAM ---
    @app_commands.command(name="instagram", description="Mostra as últimas fotos do Instagram de um usuário.")
    @app_commands.describe(usuario="O @ do perfil do Instagram (sem o @)")
    async def instagram(self, interaction: discord.Interaction, usuario: str):
        await interaction.response.defer()
        
        if not self.ig_usuario or not self.ig_senha:
            await interaction.followup.send("❌ O dono do bot não configurou as credenciais do Instagram (IG_USER e IG_PASS).")
            return

        # Faz o login na primeira vez (para não precisar fazer sempre)
        if self.cliente_ig is None:
            try:
                self.cliente_ig = Client()
                self.cliente_ig.login(self.ig_usuario, self.ig_senha)
            except Exception as e:
                await interaction.followup.send(f"❌ Erro ao logar no Instagram: {e}")
                return

        try:
            # Pega o ID do usuário e as últimas 5 mídias
            user_id = self.cliente_ig.user_id_from_username(usuario)
            medias = self.cliente_ig.user_medias(user_id, amount=5)
            
            if not medias:
                await interaction.followup.send(f"❌ Nenhuma postagem encontrada para @{usuario}.")
                return

            embed = discord.Embed(
                title=f"📸 Instagram: @{usuario}",
                description="Últimas 5 postagens:",
                color=self.bot.COR_TRAMA
            )
            
            # Adiciona a primeira foto como destaque
            primeira_foto = medias[0]
            embed.set_image(url=str(primeira_foto.thumbnail_url))
            
            # Lista as outras como links
            for i, media in enumerate(medias):
                embed.add_field(
                    name=f"Post {i+1}", 
                    value=f"[Clique para ver](https://www.instagram.com/p/{media.code}/)", 
                    inline=True
                )
                
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao buscar Instagram. O perfil pode ser privado ou inexistente. Erro: {e}")

    # --- COMANDO /TWITTER ---
    @app_commands.command(name="twitter", description="Mostra os últimos tweets de um usuário.")
    @app_commands.describe(usuario="O @ do perfil do Twitter (sem o @)")
    async def twitter(self, interaction: discord.Interaction, usuario: str):
        await interaction.response.defer()
        
        if not TWEEPY_DISPONIVEL:
            await interaction.followup.send("❌ A biblioteca `tweepy` não está instalada corretamente.")
            return

        if not self.cliente_twitter:
            await interaction.followup.send("❌ O dono do bot não configurou a chave de API do Twitter (TWITTER_BEARER_TOKEN).")
            return

        try:
            # Busca o usuário pelo username
            user = self.cliente_twitter.get_user(username=usuario)
            if not user.data:
                await interaction.followup.send(f"❌ Usuário @{usuario} não encontrado.")
                return
            
            # Pega os últimos 5 tweets
            tweets = self.cliente_twitter.get_users_tweets(
                id=user.data.id, 
                max_results=5,
                tweet_fields=['created_at', 'public_metrics']
            )
            
            if not tweets.data:
                await interaction.followup.send(f"❌ Nenhum tweet recente de @{usuario}.")
                return

            embed = discord.Embed(
                title=f"🐦 Twitter: @{usuario}",
                description="Últimos tweets:",
                color=self.bot.COR_TRAMA
            )
            
            for tweet in tweets.data:
                data_formatada = tweet.created_at.strftime("%d/%m/%Y") if tweet.created_at else "Data desconhecida"
                curtidas = tweet.public_metrics.get('like_count', 0) if tweet.public_metrics else 0
                
                # Limita o texto do tweet para não estourar o embed
                texto = tweet.text if len(tweet.text) < 150 else tweet.text[:147] + "..."
                
                embed.add_field(
                    name=f"📅 {data_formatada} • ❤️ {curtidas}",
                    value=texto,
                    inline=False
                )
                
            embed.set_footer(text="Fonte: Twitter API v2")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao buscar Twitter. Verifique se a API Key é válida. Erro: {e}")

async def setup(bot):
    await bot.add_cog(RedesSociais(bot))
