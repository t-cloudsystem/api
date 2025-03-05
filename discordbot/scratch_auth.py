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
    username: Optional[str] = None


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

        self.error_embed = discord.Embed(title="ユーザー認証", description="エラーが発生しました。\nお手数ですが、最初から認証をやり直してください。", color=0xb3b3b3)

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
        if method == "profile-comment":
            waiting.username = username

        self.waitings[discord_id] = waiting

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

        # ScratchAuthも1回で待機リストから消されるためここで削除
        discord_id = list({k: v for k, v in self.waitings.items() if v.private_code == private_code}.items())[0][0]
        self.waitings.pop(discord_id)

        logger.debug(f"プライベートコード: {private_code}")
        res = requests.get(f"{self.auth_API}/auth/verifyToken/{private_code}")
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

        if not self.cs_guild:
            raise RuntimeError("Botによる初期化がされていなかったため、ロールを付与できません")

        member = self.cs_guild.get_member(discord_id)
        await member.add_roles(discord.utils.get(self.cs_guild.roles, name="CSuser"), reason="ユーザー認証による自動付与")

        await self.cs_guild.get_channel(int(os.environ.get("DISCORD_CS_CHANNELID"))).send(
            f'ユーザー認証が完了しました。臨時で記録しています。\nScratch: {res_json["username"]}\nDiscord: {member.id}'
            )

        logger.info(f'ユーザー認証完了 Scratch: {res_json["username"]} Discord: {member.id}')

        return True

    def waiting_embed(self, discord_id: int) -> tuple[discord.Embed, Optional[discord.ui.View], Optional[str]]:
        """認証用の埋め込みを作成

        Args:
            discord_id (int): 認証する人のDiscordID

        Returns:
            discord.Embed: Discordに送信する用の埋め込み
        """

        if discord_id not in self.waitings.keys():
            logger.error(f"認証データが見つかりません DiscordID: {discord_id}")
            return self.error_embed, None, None

        embed = discord.Embed(title="ユーザー認証", color=0x4459fe)
        view = None

        method = self.waitings[discord_id].method
        public_code = self.waitings[discord_id].public_code

        if method == "profile-comment":
            username = self.waitings[discord_id].username
            if not username:
                logger.error(f"ユーザー名が見つかりません DiscordID: {discord_id}")
                return self.error_embed, None, None

            embed.description = f"準備ができました！以下のコードを自分のプロフィールにコメントして、下の「入力しました」ボタンを押してください。\n```\n{public_code}\n```"
            view = WaitingVerifyView(self, discord_id, f"https://scratch.mit.edu/users/{username}/#comments")
        else:
            if method == "cloud":
                embed.description = f"準備ができました！\n以下のコードを[入力用ページ](https://scratch.mit.edu/projects/{self.auth_project_id}/)で入力して、下の「入力しました」ボタンを押してください。\n```\n{public_code}\n```"
            else:
                embed.description = f"準備ができました！\n以下のコードを[入力用ページ](https://scratch.mit.edu/projects/{self.auth_project_id}/)でコメントして、下の「入力しました」ボタンを押してください。\n```\n{public_code}\n```"
            view = WaitingVerifyView(self, discord_id, f"https://scratch.mit.edu/projects/{self.auth_project_id}/")

        return embed, view, public_code


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

        self.scratch_auth.get_tokens(method, interaction.user.id)
        embed, view, public_code = self.scratch_auth.waiting_embed(interaction.user.id)
        if view and public_code:
            await interaction.user.send(f"認証コード: {public_code}", embed=embed, view=view)
            await interaction.followup.send("DMに認証コードを送信しました。ご確認ください！", ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)


class UsernameModal(discord.ui.Modal):
    def __init__(self, scratch_auth: ScratchAuth) -> None:
        super().__init__(title="ユーザー認証")

        self.scratch_auth = scratch_auth
        self.username = discord.ui.TextInput(label="Scratchのユーザー名", style=discord.TextStyle.short, placeholder="scratchcat", min_length=3, max_length=20)
        self.add_item(self.username)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        self.scratch_auth.get_tokens("profile-comment", interaction.user.id, self.username.value)
        embed, view, public_code = self.scratch_auth.waiting_embed(interaction.user.id)
        if view and public_code:
            await interaction.user.send(f"認証コード: {public_code}", embed=embed, view=view)
            await interaction.followup.send("DMに認証コードを送信しました。ご確認ください！", ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)


class WaitingVerifyView(discord.ui.View):
    """認証コードを表示しつつ、入力を待つView"""

    def __init__(self, scratch_auth: ScratchAuth, discord_id: int, link_url: Optional[str] = None, timeout: Optional[int] = None):
        super().__init__(timeout=timeout)
        self.scratch_auth = scratch_auth
        self.discord_id = discord_id

        if link_url:
            self.add_item(discord.ui.Button(label="入力用ページへ", url=link_url, style=discord.ButtonStyle.link))

    @discord.ui.button(label="入力しました", custom_id="verify_token", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button: discord.Button) -> None:
        if self.discord_id not in self.scratch_auth.waitings.keys():
            logger.info(f"認証データなし DiscordID: {self.discord_id}")
            embed = discord.Embed(title="ユーザー認証", description="認証の有効期限が切れました。お手数ですが、最初からやり直してください。", color=0xf6a408)
            await interaction.response.send_message(embed=embed)
            return

        await interaction.response.defer()

        waiting = self.scratch_auth.waitings[self.discord_id]
        res = await self.scratch_auth.verify_token(waiting.private_code)
        if res:
            embed = discord.Embed(title="ユーザー認証", description="認証が完了しました！", color=0x43b581)
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title="ユーザー認証",
                description="認証に失敗しました。お手数ですが、最初からやり直してください。\n何回やっても失敗する場合は、管理者にお問い合わせください。",
                color=0xf6a408
            )
            await interaction.followup.send(embed=embed)


if __name__ == "__main__":
    from dotenv import load_dotenv
    from os import path

    dotenv_path = path.join(path.abspath(path.join(path.dirname(__file__), os.pardir)), '.env')
    load_dotenv(dotenv_path)

    scratch_auth = ScratchAuth()

    print(scratch_auth.get_tokens("comment"))
