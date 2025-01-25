import os
import base64
from typing import Literal, Optional
from logging import getLogger, StreamHandler, DEBUG
from dataclasses import dataclass

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
        """Scratch認証を行います。
        環境変数に'SCRATCH_AUTH_PROJECT_ID'を設定してください。

        Raises:
            ValueError: 環境変数が適切に設定されていない場合
        """

        self.auth_project_id = os.environ.get("SCRATCH_AUTH_PROJECT_ID")

        if not self.auth_project_id:
            raise ValueError("Scratch認証用のプロジェクトを環境変数に指定してください。")

        self.auth_API = "https://auth-api.itinerary.eu.org"
        self.auth_redirect = "https://www.takechi.cloud/"
        self.waitings: dict[str, WaitingData] = {}
        self.cs_guild: Optional[discord.Guild] = None

    def init_with_bot(self, bot: commands.Bot):
        """Botのインスタンスを利用した初期化

        Args:
            bot (discord.ext.commands.Bot): Botのインスタンス
        """

        self.bot = bot

        bot.add_view(ChooseMethodView())
        bot.add_view(WaitingVerifyView())

        self.cs_guild = self.bot.get_guild(int(os.environ.get("DISCORD_CS_SERVERID")))

    def get_tokens(self, method: Literal["cloud", "comment", "profile-comment"], discord_id: int, username: str = None) -> dict:
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

        task = VerifyTokenTask(self, res["privateCode"], discord_id)

        if discord_id in self.waitings.keys():
            self.waitings[discord_id].task.schedule_handler.stop()

        waiting = WaitingData(res["publicCode"], res["privateCode"], method, task)
        self.waitings[discord_id] = waiting
        # {"task": task, "publicCode": res["publicCode"], "privateCode": res["privateCode"], "method": method}

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

        discord_id, waiting_data = list({k: v for k, v in self.waitings.items() if v.private_code == private_code}.items())[0]
        self.waitings.pop(discord_id)

        waiting_data.task.schedule_handler.stop()

        member = self.cs_guild.get_member(discord_id)
        await member.add_roles(discord.utils.get(self.cs_guild.roles, name="CSuser"), reason="ユーザー認証による自動付与")

        await self.cs_guild.get_channel(int(os.environ.get("DISCORD_CS_CHANNELID"))).send(
            f"ユーザー認証が完了しました。臨時で記録しています。\nScratch: {res_json["username"]}\nDiscord: {member.id}"
            )

        logger.info(f"ユーザー認証完了 Scratch: {res_json["username"]} Discord: {member.id}")

        return True


class VerifyTokenTask(commands.Cog):
    def __init__(self, scratch_auth: ScratchAuth, private_code: str, discord_id: int) -> None:
        self.scratch_auth = scratch_auth
        self.private_code = private_code
        self.discord_id = discord_id
        self.schedule_handler.start()

    def cog_unload(self):
        self.schedule_handler.cancel()

    @tasks.loop(seconds=5.0)
    async def schedule_handler(self):
        is_ok = await self.scratch_auth.verify_token(self.private_code)
        if is_ok:
            embed = discord.Embed(title="ユーザー認証", description="認証が完了しました！", color=0x43b581)
            await self.scratch_auth.bot.get_user(self.discord_id).send(embed=embed)
            self.schedule_handler.stop()


@dataclass
class WaitingData:
    public_code: str
    private_code: str
    method: Literal["cloud", "comment", "profile-comment"]
    task: VerifyTokenTask


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
            if method == "profile-comment":
                await interaction.response.send_modal(UsernameModal, ephemeral=True)
                return

            res = self.scratch_auth.get_tokens(method, interaction.user.id)
            view = WaitingVerifyView(self.scratch_auth, interaction.user.id)

            await interaction.user.send(f"認証コード: {res['code']}", embed=waiting_embed(res["code"]), view=view)
            await interaction.response.send_message("DMに認証コードを送信したので、ご確認ください！", ephemeral=True)


class UsernameModal(discord.ui.Modal):
    def __init__(self) -> None:
        super().__init__(title="ユーザー認証")
        self.username = discord.ui.TextInput(label="Scratchのユーザー名", style=discord.TextStyle.short, placeholder="scratchcat", min_length=3, max_length=20)
        self.add_item(self.username)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        res = self.scratch_auth.get_tokens("profile-comment", interaction.user.id, self.username.value)
        view = WaitingVerifyView(self.scratch_auth, interaction.user.id)

        await interaction.user.send(f"認証コード: {res['code']}", embed=waiting_embed(res["code"]), view=view)
        await interaction.response.send_message("DMに認証コードを送信したので、ご確認ください！", ephemeral=True)


def waiting_embed(public_code: str) -> discord.Embed:
    auth_project = int(os.environ.get("SCRATCH_AUTH_PROJECT_ID", "728098174"))
    return discord.Embed(title="ユーザー認証", description=f"準備ができました！\n以下のコードを[入力用ページ](https://scratch.mit.edu/projects/{auth_project}/)で入力して、下の「入力しました」ボタンを押してください。\n```\n{public_code}\n```", color=0x4459fe)


class WaitingVerifyView(discord.ui.View):
    """認証コードを表示しつつ、入力を待つView"""

    def __init__(self, scratch_auth: ScratchAuth, discord_id: int, timeout=None):
        super().__init__(timeout=timeout)
        self.scratch_auth = scratch_auth
        self.discord_id = discord_id

    @discord.ui.button(label="入力しました", custom_id="verify_token", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button: discord.Button) -> None:
        if self.discord_id not in self.scratch_auth.waitings.keys():
            embed = discord.Embed(title="ユーザー認証", description="すでに認証が完了しているようです。", color=0xf6a408)
            await interaction.response.send_message(embed=embed)

        waiting = self.scratch_auth.waitings[self.discord_id]
        res = self.scratch_auth.verify_token(waiting.private_code)
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

    scratchauth = ScratchAuth()

    print(scratchauth.get_tokens("comment"))
