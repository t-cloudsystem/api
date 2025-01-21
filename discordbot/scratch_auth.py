import time
import os
import base64
from typing import Literal
from logging import getLogger, StreamHandler, DEBUG

import discord
from discord.ext import commands, tasks
import requests

# from discordbot.templates import EmojiTemplates
from templates import EmojiTemplates  # テスト用


logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False


class ScratchAuth:
    def __init__(self):
        self.auth_project_id = os.environ.get("SCRATCH_AUTH_PROJECT_ID")

        if not self.auth_project_id:
            raise ValueError("Scratch認証用のプロジェクトを環境変数に指定してください。")

        self.auth_API = "https://auth-api.itinerary.eu.org"
        self.auth_redirect = "https://www.takechi.cloud/"
        self.waitings = {}

    def init_with_bot(self, bot: commands.Bot):
        """Botのインスタンスを利用した初期化

        Args:
            bot (discord.ext.commands.Bot): Botのインスタンス
        """

        self.bot = bot

        bot.add_view(ChooseMethodView())
        bot.add_view(WaitingVerifyView())

        self.emoji_templates = EmojiTemplates(bot)

    def get_tokens(self, method: Literal["cloud", "comment", "profile-comment"], username: str = None):
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
        # {'publicCode': 'abcabc', 'privateCode': 'abcabcabcabc', 'redirectLocation': 'https://www.takechi.cloud/', 'method': 'comment', 'authProject': '1071161378'}

        if res.status_code != 200:
            raise ConnectionError(f"APIの取得に失敗しました コード: {res.status_code}")

        task = VerifyTokenTask(self, res["privateCode"])
        self.waitings[res["publicCode"]] = task

        return res.json()

    async def verify_token(self, private_code: str):
        """トークンを検証します

        Args:
            private_code (str): Authで生成された秘密鍵

        Raises:
            ValueError: 環境変数が適切に設定されていない場合
            ConnectionError: APIとの通信でエラーが発生した場合

        Returns:
            Any: APIのレスポンス
        """

        res = requests.post(f"{self.auth_API}/auth/verifyToken/", json={"privateCode": private_code})

        if res.status_code != 200:
            raise ConnectionError(f"APIの取得に失敗しました コード: {res.status_code}")

        res_json = res.json()
        # {"valid":false,"username":null,"redirect":null}

        if not res_json["valid"]:
            logger.info("未認証")
            return False

        if res_json["redirect"] != self.auth_redirect:
            logger.error("認証元が異なります")
            return False

        cs_guild = self.bot.get_guild(int(os.environ.get("DISCORD_CS_SERVERID")))
        member = cs_guild.get_member(12345)  # ユーザーIDを引っ張ってくる必要あり
        await member.add_roles(discord.utils.get(cs_guild.roles, name="CSuser"), reason="ユーザー認証による自動付与")

        await cs_guild.get_channel(int(os.environ.get("DISCORD_CS_CHANNELID"))).send(
            f"ユーザー認証が完了しました。臨時で記録しています。\nScratch: {res_json["username"]}\nDiscord: {member.id}"
            )

        logger.info(f"ユーザー認証完了 Scratch: {res_json["username"]} Discord: {member.id}")

        return True


class VerifyTokenTask(commands.Cog):
    def __init__(self, scratch_auth: ScratchAuth, private_code: str) -> None:
        self.scratch_auth = scratch_auth
        self.private_code = private_code
        self.schedule_handler.start()

    def cog_unload(self):
        self.schedule_handler.cancel()

    @tasks.loop(seconds=5.0)
    async def schedule_handler(self):
        is_ok = await self.scratch_auth.verify_token(self.private_code)
        if is_ok:
            self.schedule_handler.stop()


class ChooseMethodView(discord.ui.View):
    def __init__(self, scratch_auth: ScratchAuth, emoji_templates: EmojiTemplates, timeout=None):
        self.emoji_templates = emoji_templates
        self.scratch_auth = scratch_auth
        super().__init__(timeout=timeout)

        self.select = discord.ui.Select(
            custom_id="choose_auth_method",
            placeholder="ここから選択",
            options=[
                discord.SelectOption(label="クラウド変数", value="cloud", emoji=self.emoji_templates.auth_cloud, description="Scratcherのみ利用できます。"),
                discord.SelectOption(label="プロジェクトコメント", value="comment", emoji=self.emoji_templates.auth_comment, description="指定作品にコメントしてください。"),
                discord.SelectOption(label="プロフィールコメント", value="profile-comment", emoji=self.emoji_templates.auth_profile_comment, description="プロフィールにコメントしてください。"),
            ]
        )
        self.add_item(self.select)

        @discord.ui.button(label="決定する", custom_id="get_token", style=discord.ButtonStyle.primary)
        async def get_token(interaction: discord.Interaction, button: discord.Button) -> None:
            method = self.select.values[0]
            tokens = self.scratch_auth.get_tokens(method)

            await interaction.response.send_message(f"認証コード: {tokens['code']}", ephemeral=True)


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


if __name__ == "__main__":
    from dotenv import load_dotenv
    from os import path

    dotenv_path = path.join(path.abspath(path.join(path.dirname(__file__), os.pardir)), '.env')
    load_dotenv(dotenv_path)

    scratchauth = ScratchAuth()

    print(scratchauth.get_tokens("comment"))
