from logging import getLogger, StreamHandler, DEBUG

from discord import app_commands
from discord.ext import commands
import discord

from discordbot.templates import EmbedTemplates

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False


class EditModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot, message: discord.Message) -> None:
        super().__init__(title="メッセージ編集")
        self.edited_text = discord.ui.TextInput(label="メッセージ", style=discord.TextStyle.long, placeholder=message.content, required=True)
        self.add_item(self.edited_text)

        self.message = message
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        text = self.edited_text.value

        await self.message.edit(
            content=text
        )

        await interaction.response.send_message("編集が完了しました！", ephemeral=True)


class PostModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot, channel: discord.abc.GuildChannel) -> None:
        super().__init__(title="メッセージ作成")
        self.edited_text = discord.ui.TextInput(label="メッセージ", style=discord.TextStyle.long, required=True)
        self.add_item(self.edited_text)

        self.channel = channel
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        text = self.edited_text.value

        await self.channel.send(
            content=text
        )

        await interaction.response.send_message("送信しました！", ephemeral=True)


@app_commands.guild_only()
class AdminMessages(app_commands.Group):
    def __init__(self, bot: commands.Bot, discord_cs_server_id: int) -> None:
        super().__init__(name="admin_message", description="管理者用コマンド")
        self.bot = bot
        self.discord_cs_server_id = discord_cs_server_id

    @app_commands.command(name="edit", description="メッセージを編集します")
    async def edit_message(self, interaction: discord.Interaction, message_id: str) -> None:
        if not message_id.isdigit():
            await interaction.response.send_message("メッセージIDを変換できません", ephemeral=True)
            return

        message = await interaction.channel.fetch_message(int(message_id))
        if message.author != self.bot.user:
            await interaction.response.send_message(embed=EmbedTemplates.not_bot_message, ephemeral=True)
            return

        modal = EditModal(self.bot, message)
        await interaction.response.send_modal(modal)

    async def interaction_check(self, interaction: discord.Integration):
        if interaction.guild is None:
            await interaction.response.send_message(embed=EmbedTemplates.dm, ephemeral=True)
            return False

        if interaction.guild is not None and interaction.guild.id != self.discord_cs_server_id:
            await interaction.response.send_message(embed=EmbedTemplates.outside_cs, ephemeral=True)
            return False

        if discord.utils.get(interaction.user.roles, name="admin"):
            await interaction.response.send_message(embed=EmbedTemplates.no_permission, ephemeral=True)
            return False

        return True
