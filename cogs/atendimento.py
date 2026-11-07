import discord
from discord import app_commands
from discord.ext import commands
import asyncio

class Atendimento(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- SISTEMA DE FORMULÁRIOS ---
    @app_commands.command(name="formularios", description="Envia um formulário personalizado para o canal.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        titulo="Título do Formulário (ex: Formulário de Staff)",
        pergunta1="Primeira pergunta",
        pergunta2="Segunda pergunta (Opcional)",
        pergunta3="Terceira pergunta (Opcional)",
        pergunta4="Quarta pergunta (Opcional)",
        pergunta5="Quinta pergunta (Opcional)"
    )
    async def formularios(self, interaction: discord.Interaction, titulo: str, pergunta1: str, pergunta2: str = None, pergunta3: str = None, pergunta4: str = None, pergunta5: str = None):
        
        # Cria a lista de perguntas que não estão vazias
        perguntas = [p for p in [pergunta1, pergunta2, pergunta3, pergunta4, pergunta5] if p is not None]
        
        embed = discord.Embed(
            title=f"📝 {titulo}",
            description="Clique no botão abaixo para preencher o formulário.",
            color=self.bot.COR_TRAMA
        )
        embed.set_footer(text="Surf Trama • Formulários")
        
        await interaction.response.send_message("Formulário criado com sucesso!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=BotaoAbrirFormulario(titulo, perguntas))

    # --- SISTEMA DE MIDDLEMAN (MEDIADOR) ---
    @app_commands.command(name="middleman", description="Abre um ticket de negociação segura com um mediador.")
    @app_commands.describe(motivo="O que você vai negociar? (ex: Troca de contas, Venda de item)")
    async def middleman(self, interaction: discord.Interaction, motivo: str):
        guild = interaction.guild
        
        # Cria um canal privado para a negociação
        nome_canal = f"negociacao-{interaction.user.name.lower()}"
        canal_existente = discord.utils.get(guild.text_channels, name=nome_canal)
        
        if canal_existente:
            await interaction.response.send_message(f"❌ Você já tem uma negociação aberta: {canal_existente.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        canal = await guild.create_text_channel(nome_canal, overwrites=overwrites)
        
        embed = discord.Embed(
            title="🤝 Negociação Segura (Middleman)",
            description=f"Olá {interaction.user.mention}!\n\n**Motivo da negociação:** {motivo}\n\nUm **Middleman** (Mediador) da equipe TRAMA foi chamado para garantir que ninguém seja enganado.\n\n**Como funciona:**\n1. Vocês combinam os detalhes.\n2. O Middleman recebe os itens/dinheiro de ambas as partes.\n3. O Middleman entrega para cada um o que foi combinado.\n\n⚠️ *Aguarde a Staff entrar no canal.*",
            color=self.bot.COR_TRAMA
        )
        embed.set_footer(text="Segurança garantida pela TRAMA")
        
        await canal.send(embed=embed)
        await interaction.response.send_message(f"✅ Negociação criada em {canal.mention}", ephemeral=True)

# --- BOTÃO DO FORMULÁRIO ---
class BotaoAbrirFormulario(discord.ui.View):
    def __init__(self, titulo, perguntas):
        super().__init__(timeout=None)
        self.titulo = titulo
        self.perguntas = perguntas

    @discord.ui.button(label="Preencher Formulário", style=discord.ButtonStyle.primary, emoji="📝", custom_id="btn_formulario")
    async def abrir(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Isso abre a janelinha (Modal) para o usuário preencher
        await interaction.response.send_modal(ModalFormulario(self.titulo, self.perguntas))

# --- MODAL (A JANELINHA DE PREENCHER) ---
class ModalFormulario(discord.ui.Modal):
    def __init__(self, titulo, perguntas):
        # O título do modal tem que ter no máximo 45 caracteres
        super().__init__(title=titulo[:45])
        self.perguntas = perguntas
        
        # O Discord só deixa colocar até 5 campos de texto em um modal
        for i, pergunta in enumerate(perguntas[:5]):
            self.add_item(discord.ui.TextInput(
                label=pergunta[:45], # Label do campo
                style=discord.TextStyle.short if len(pergunta) < 30 else discord.TextStyle.paragraph,
                required=True,
                placeholder="Digite sua resposta aqui..."
            ))

    async def on_submit(self, interaction: discord.Interaction):
        # Pega as respostas que a pessoa digitou
        respostas = []
        for i, child in enumerate(self.children):
            pergunta = self.perguntas[i]
            respostas.append(f"**{pergunta}**\n{child.value}\n")
            
        embed = discord.Embed(
            title=f"📩 Nova Resposta: {self.title}",
            description=f"Enviado por: {interaction.user.mention}\n\n" + "\n".join(respostas),
            color=self.bot.COR_TRAMA if hasattr(self, 'bot') else discord.Color.red()
        )
        
        # Cria um canal privado só para a Staff ver as respostas
        guild = interaction.guild
        categoria = discord.utils.get(guild.categories, name="📩 Formulários")
        if not categoria:
            categoria = await guild.create_category("📩 Formulários")
            
        canal_resposta = await guild.create_text_channel(f"resp-{interaction.user.name.lower()}", category=categoria)
        
        # Permissões: Todo mundo vê, menos o @everyone
        await canal_resposta.set_permissions(guild.default_role, read_messages=False)
        await canal_resposta.set_permissions(interaction.user, read_messages=True)
        
        await canal_resposta.send(embed=embed)
        
        await interaction.response.send_message("✅ Formulário enviado com sucesso! A Staff vai analisar.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Atendimento(bot))
