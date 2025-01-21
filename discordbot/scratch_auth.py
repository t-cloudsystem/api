import time
import os
import uuid
import base64
from typing import Literal

import discord
import requests

from discordbot.templates import EmojiTemplates


class ChooseMethodView(discord.ui.View):
    def __init__(self, emoji_templates: EmojiTemplates, timeout=None):
        self.emoji_templates = emoji_templates
        super().__init__(timeout=timeout)

        @discord.ui.select(
            cls=discord.ui.Select,
            placeholder="ここから選択",
            options=[
                discord.SelectOption(label="クラウド変数", emoji=self.emoji_templates.auth_cloud, description="Scratcherのみ利用できます。"),
                discord.SelectOption(label="プロジェクトコメント", emoji=self.emoji_templates.auth_comment, description="指定作品にコメントしてください。"),
                discord.SelectOption(label="プロフィールコメント", emoji=self.emoji_templates.auth_profile_comment, description="プロフィールにコメントしてください。"),
            ]
        )
        async def select(interaction: discord.Interaction, select: discord.ui.Select):
            await interaction.response.send_message(f"{select.values[0]}がいいんだね！", ephemeral=True)


class WaitingVerifyView(discord.ui.View):
    """認証コードを表示しつつ、入力を待つView"""

    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.danger)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message("キャンセルしました。", ephemeral=True)
        self.stop()

    @discord.ui.button(label="再送信", style=discord.ButtonStyle.secondary)
    async def resend(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message("再送信しました。", ephemeral=True)

    @discord.ui.button(label="認証", style=discord.ButtonStyle.primary)
    async def verify(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message("認証しました。", ephemeral=True)
        self.stop()


class ScratchAuth:
    def __init__(self):
        self.auth_project_id = os.environ.get("SCRATCH_AUTH_PROJECT_ID")

        if not self.auth_project_id:
            raise ValueError("Scratch認証用のプロジェクトを環境変数に指定してください。")

        self.auth_API = "https://auth-api.itinerary.eu.org"
        self.auth_redirect = "https://www.takechi.cloud/"
        self.waiting_cogs = []

    def init_with_bot(self, bot: discord.ext.commands.Bot):
        """Botのインスタンスを利用した初期化

        Args:
            bot (discord.ext.commands.Bot): Botのインスタンス
        """

        bot.add_view(ChooseMethodView())
        bot.add_view(WaitingVerifyView())

        self.emoji_templates = EmojiTemplates(bot)

    def getTokens(self, method: Literal["cloud", "comment", "profile-comment"], username: str = None):
        """認証用のトークンを取得します

        Args:
            method (Literal[&quot;cloud&quot;, &quot;comment&quot;, &quot;profile&quot;]): 認証タイプを選択します。
            username (str, optional): 認証するユーザー名を入力します。プロフィールコメントの場合は必須です。

        Raises:
            ValueError: 環境変数が適切に設定されていない場合
            ConnectionError: APIとの通信でエラーが発生した場合

        Returns:
            Any: APIのレスポンス
        """

        if method == "profile-comment" and not username:
            raise ValueError("プロフィールコメントの場合はユーザー名を指定してください")

        redirect_base64 = base64.urlsafe_b64encode(self.auth_redirect.encode()).decode()

        params = {"redirect": redirect_base64, "method": method, "authProject": self.auth_project_id}
        if method == "profile-comment":
            params["username"] = username

        res = requests.get(f"{self.auth_API}/auth/getTokens/", params=params)

        if res.status_code != 200:
            raise ConnectionError(f"APIの取得に失敗しました コード: {res.status_code}")

        return res.json()


if __name__ == "__main__":
    from dotenv import load_dotenv
    from os import path

    dotenv_path = path.join(path.abspath(path.join(path.dirname(__file__), os.pardir)), '.env')
    load_dotenv(dotenv_path)

    scratchauth = ScratchAuth()

    print(scratchauth.getTokens("cloud").json())
