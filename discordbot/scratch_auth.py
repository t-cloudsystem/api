from __future__ import annotations  # 型アノテーション時の参照エラー回避
import os
import base64
from typing import Literal, Optional
from logging import getLogger, StreamHandler, DEBUG
from dataclasses import dataclass

import discord
from discord.ext import commands
import requests

from discordbot.templates import EmojiTemplates
# from templates import EmojiTemplates  # テスト用


logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False


@dataclass
class WaitingData:
    public_code: str
    private_code: str
    method: Literal["cloud", "comment", "profile-comment"]


class ScratchAuth:
    def __init__(self, *, api: str = "https://auth-api.itinerary.eu.org", redirect: str = "https://www.takechi.cloud/"):
        """Scratch認証を行います。
        環境変数に'SCRATCH_AUTH_PROJECT_ID'を設定してください。

        Raises:
            ValueError: 環境変数が適切に設定されていない場合
        """

        self.auth_project_id = os.environ.get("SCRATCH_AUTH_PROJECT_ID")

        if not self.auth_project_id:
            raise ValueError("Scratch認証用のプロジェクトを環境変数に指定してください。")

        self.auth_API = api
        self.auth_redirect = redirect
        self.waitings: dict[str, WaitingData] = {}
        self.cs_guild: Optional[discord.Guild] = None

    def init_with_bot(self, bot: commands.Bot):
        """Botのインスタンスを利用した初期化

        Args:
            bot (discord.ext.commands.Bot): Botのインスタンス
        """

        self.bot = bot

        bot.add_view(ChooseMethodView(self, EmojiTemplates(bot)))
        bot.add_view(WaitingVerifyView(self, 0))

        self.cs_guild = self.bot.get_guild(int(os.environ.get("DISCORD_CS_SERVERID")))

    def get_tokens(self, method: Literal["cloud", "comment", "profile-comment"], discord_id: int, username: str = None) -> WaitingData:
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

        logger.debug(f"APIリクエスト: {params}")
        res = requests.get(f"{self.auth_API}/auth/getTokens/", params=params)
        # {'publicCode': 'abcabc', 'privateCode': 'abcabcabcabc', 'redirectLocation': 'https://www.takechi.cloud/', 'method': 'comment', 'authProject': '1071161378'}
        logger.debug(f"APIレスポンス: {res.json()}")

        if res.status_code != 200:
            raise ConnectionError(f"APIの取得に失敗しました コード: {res.status_code}")

        res_json = res.json()

        waiting = WaitingData(public_code=res_json["publicCode"], private_code=res_json["privateCode"], method=method)
        self.waitings[discord_id] = waiting
        # {"task": task, "publicCode": res_json["publicCode"], "privateCode": res_json["privateCode"], "method": method}

        return waiting

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

        logger.debug(f"プライベートコード: {private_code}")
        res = requests.get(f"{self.auth_API}/auth/verifyToken/:privateCode", params={"privateCode": private_code})
        logger.debug(f"APIレスポンス: {res.text}, コード: {res.status_code}, タイプ: {res.headers['content-type']}")

        # 失敗だと403になるが、JSONは取得できる
        if not res.headers["content-type"].lower().startswith("application/json"):
            raise ConnectionError(f"APIの取得に失敗しました コード: {res.status_code}")

        res_json = res.json()
        # {"valid":false,"username":null,"redirect":null}

        if not res_json["valid"]:
            logger.info("未認証")
            return False

        if res_json["redirect"] != self.auth_redirect:
            logger.error("認証元が異なります")
            return False

        discord_id, waiting_data = list({k: v for k, v in self.waitings.items() if v.private_code == private_code}.items())[0]
        self.waitings.pop(discord_id)

        if not self.cs_guild:
            raise RuntimeError("Botによる初期化がされていなかったため、ロールを付与できません")

        member = self.cs_guild.get_member(discord_id)
        await member.add_roles(discord.utils.get(self.cs_guild.roles, name="CSuser"), reason="ユーザー認証による自動付与")

        await self.cs_guild.get_channel(int(os.environ.get("DISCORD_CS_CHANNELID"))).send(
            f"ユーザー認証が完了しました。臨時で記録しています。\nScratch: {res_json["username"]}\nDiscord: {member.id}"
            )

        logger.info(f"ユーザー認証完了 Scratch: {res_json["username"]} Discord: {member.id}")

        return True


class ChooseMethodView(discord.ui.View):
    def __init__(self, scratch_auth: ScratchAuth, emoji_templates: EmojiTemplates, timeout=None):
        self.emoji_templates = emoji_templates
        self.scratch_auth = scratch_auth
        super().__init__(timeout=timeout)

        self.set_select()

    def set_select(self):
        self.select = discord.ui.Select(
            custom_id="choose_auth_method",
            placeholder="ここから選択",
            options=[
                discord.SelectOption(label="クラウド変数", value="cloud", emoji=self.emoji_templates.auth_cloud, description="Scratcherのみ利用できます。"),
                discord.SelectOption(label="プロジェクトコメント", value="comment", emoji=self.emoji_templates.auth_comment, description="指定作品にコメントしてください。"),
                discord.SelectOption(label="プロフィールコメント", value="profile-comment", emoji=self.emoji_templates.auth_profile_comment, description="プロフィールにコメントしてください。"),
            ]
        )
        self.select.callback = self.get_token
        self.add_item(self.select)

    async def get_token(self, interaction: discord.Interaction) -> None:
        method = self.select.values[0]
        if method == "profile-comment":
            await interaction.response.send_modal(UsernameModal(self.scratch_auth))
            return

        await interaction.response.defer(ephemeral=True)

        waiting_data = self.scratch_auth.get_tokens(method, interaction.user.id)
        view = WaitingVerifyView(self.scratch_auth, interaction.user.id)

        await interaction.user.send(f"認証コード: {waiting_data.public_code}", embed=waiting_embed(waiting_data.public_code), view=view)
        await interaction.followup.send("DMに認証コードを送信しました。ご確認ください！", ephemeral=True)


class UsernameModal(discord.ui.Modal):
    def __init__(self, scratch_auth: ScratchAuth) -> None:
        super().__init__(title="ユーザー認証")

        self.scratch_auth = scratch_auth
        self.username = discord.ui.TextInput(label="Scratchのユーザー名", style=discord.TextStyle.short, placeholder="scratchcat", min_length=3, max_length=20)
        self.add_item(self.username)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        waiting_data = self.scratch_auth.get_tokens("profile-comment", interaction.user.id, self.username.value)
        view = WaitingVerifyView(self.scratch_auth, interaction.user.id)

        await interaction.user.send(f"認証コード: {waiting_data.public_code}", embed=waiting_embed(waiting_data.public_code), view=view)
        await interaction.followup.send("DMに認証コードを送信しました。ご確認ください！", ephemeral=True)


def waiting_embed(public_code: str) -> discord.Embed:
    auth_project = int(os.environ.get("SCRATCH_AUTH_PROJECT_ID", "728098174"))
    return discord.Embed(
        title="ユーザー認証",
        description=f"準備ができました！\n以下のコードを**3分以内に**[入力用ページ](https://scratch.mit.edu/projects/{auth_project}/)で入力して、下の「入力しました」ボタンを押してください。\n```\n{public_code}\n```",
        color=0x4459fe
    )


class WaitingVerifyView(discord.ui.View):
    """認証コードを表示しつつ、入力を待つView"""

    def __init__(self, scratch_auth: ScratchAuth, discord_id: int, timeout=None):
        super().__init__(timeout=timeout)
        self.scratch_auth = scratch_auth
        self.discord_id = discord_id

        self.add_item(discord.ui.Button(
            label="入力用ページへ",
            url=f'https://scratch.mit.edu/projects/{self.scratch_auth.auth_project_id}/',
            style=discord.ButtonStyle.link
        ))

    @discord.ui.button(label="入力しました", custom_id="verify_token", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button: discord.Button) -> None:
        if self.discord_id not in self.scratch_auth.waitings.keys():
            embed = discord.Embed(title="ユーザー認証", description="認証の有効期限が切れました。お手数ですが、最初からやり直してください。", color=0xf6a408)
            await interaction.response.send_message(embed=embed)
            return

        waiting = self.scratch_auth.waitings[self.discord_id]
        res = await self.scratch_auth.verify_token(waiting.private_code)
        if res:
            embed = discord.Embed(title="ユーザー認証", description="認証が完了しました！", color=0x43b581)
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title="ユーザー認証", description="認証に失敗しました。正しいコードを入力しているか確認してください。", color=0xf6a408)
            await interaction.response.send_message(embed=embed)


if __name__ == "__main__":
    from dotenv import load_dotenv
    from os import path

    dotenv_path = path.join(path.abspath(path.join(path.dirname(__file__), os.pardir)), '.env')
    load_dotenv(dotenv_path)

    scratch_auth = ScratchAuth()

    print(scratch_auth.get_tokens("comment"))
