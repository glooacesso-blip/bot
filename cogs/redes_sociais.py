import discord
from discord import app_commands
from discord.ext import commands
import os
from instagrapi import Client

class RedesSociais(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Credenciais do Instagram (configuradas no painel do Render)
        self.ig_usuario = os.getenv("IG_USER") 
        self.ig_senha = os.getenv("IG_PASS")
        self.cliente_ig = None

    @app_commands.command(name="instagram", description="Mostra o último post do Instagram de um usuário.")
    @app_commands.describe(usuario="O @ do perfil do Instagram (sem o @)")
    async def instagram(self, interaction: discord.Interaction, usuario: str):
        await interaction.response.defer()
        
        if not self.ig_usuario or not self.ig_senha:
            await interaction.followup.send("❌ O dono do bot não configurou as credenciais do Instagram (IG_USER e IG_PASS) no Render.")
            return

        # Faz o login na primeira vez
        if self.cliente_ig is None:
            try:
                self.cliente_ig = Client()
                # O login pode falhar se o Instagram bloquear o IP do Render
                self.cliente_ig.login(self.ig_usuario, self.ig_senha)
            except Exception as e:
                await interaction.followup.send(f"❌ Erro ao logar no Instagram. O Instagram pode estar bloqueando o IP do Render. Erro: {e}")
                return

        try:
            # Pega o ID do usuário e a última mídia
            user_id = self.cliente_ig.user_id_from_username(usuario)
            medias = self.cliente_ig.user_medias(user_id, amount=1)
            
            if not medias:
                await interaction.followup.send(f"❌ Nenhuma postagem encontrada para @{usuario}.")
                return

            post = medias[0]
            
            # VERIFICA SE É FOTO OU VÍDEO
            if post.media_type == 1: # 1 = Foto
                filename = f"igpost{post.pk}.jpg" # Nome sem underline para o Discord aceitar
                self.cliente_ig.photo_download(post.pk, folder=".", filename=filename)
                file = discord.File(filename, filename="igpost.jpg")
                embed_image_url = "attachment://igpost.jpg"
                
            elif post.media_type == 2: # 2 = Vídeo
                filename = f"igpost{post.pk}.mp4"
                self.cliente_ig.video_download(post.pk, folder=".", filename=filename)
                file = discord.File(filename, filename="igpost.mp4")
                embed_image_url = None # Vídeo não vai no embed, vai como arquivo solto
                
            else:
                await interaction.followup.send("❌ Este tipo de mídia (álbum/carrossel) não é suportado no momento.")
                return

            embed = discord.Embed(
                title=f"📸 @{usuario}",
                description=post.caption if post.caption else "Sem legenda.",
                color=self.bot.COR_TRAMA
            )
            
            if embed_image_url:
                embed.set_image(url=embed_image_url)
                
            embed.set_footer(text=f"❤️ {post.like_count} curtidas • 💬 {post.comment_count} comentários")

            await interaction.followup.send(embed=embed, file=file)
            
            # Limpa o arquivo do servidor após enviar
            os.remove(filename)

        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao buscar Instagram. O perfil pode ser privado ou o post é um carrossel. Erro: {e}")

async def setup(bot):
    await bot.add_cog(RedesSociais(bot))
