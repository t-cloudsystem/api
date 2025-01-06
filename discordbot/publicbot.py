import datetime
import random
import time
import os
import hashlib
from logging import getLogger, StreamHandler, DEBUG

from dotenv import load_dotenv
from discord.ext import commands, tasks
import discord
import requests
from scratchattach import ScratchCloud, CloudActivity
from scratchattach.utils.exceptions import FetchError as SAFetchError

from discordbot.scratch_info import get_scratch_info
from discordbot.daily_projects import DailyProjects


load_dotenv(verbose=True)
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False

cs_guild = None

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


class RandomStatusTask(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.change_status.start()

    def cog_unload(self):
        self.change_status.cancel()

    @tasks.loop(seconds=5.0)
    async def change_status(self):
        try:
            text = "".join([random.choice(["ク", "ラ", "ウ", "ド"]) for _ in range(4)])
            await self.bot.change_presence(status=discord.Status.online, activity=discord.Game(text + "システム"))
        except Exception as e:
            logger.error(f"ステータス変更中にエラーが発生しました {e}")


class discordAuth:
    hash_template = "{username}__{discord_id}__{time}"

    def __init__(self, project_id: str) -> None:
        self.waiting_users = []
        self.project_id = str(project_id)

    async def issue_authcode(self, username, discord_id):
        timestamp = int(time.time())
        self.waiting_users.append({"username": username, "discord_id": discord_id, "status": "waiting", "start_time": timestamp})
        authcode = await self._make_authcode(username, discord_id, timestamp)
        logger.info(f"認証コード発行 DiscordID {discord_id} コード {authcode}")
        return authcode

    async def check_authcode(self, discord_id):
        discord_ids = [user["discord_id"] for user in self.waiting_users if user["status"] == "waiting"]
        if discord_id not in discord_ids:
            return "", "not_found"

        userdata = [user for user in self.waiting_users if user["discord_id"] == discord_id][-1]
        raw_logs: list[CloudActivity] = ScratchCloud(project_id=1071161378).logs()

        if isinstance(raw_logs, SAFetchError):
            return userdata["username"], "fetch_error"

        logs = [cloud_activity for cloud_activity in raw_logs if cloud_activity.type == "set" and cloud_activity.var == "AuthCode" and cloud_activity.username == userdata["username"]]

        if len(logs) == 0:
            return userdata["username"], "not_found"

        log = logs[0]
        logger.debug(f"参照したクラウドログ {log.value}")

        if max(time.time(), log.timestamp / 1000) > userdata["start_time"] + 300 or log.timestamp / 1000 < userdata["start_time"]:
            return userdata["username"], "timeout"

        if str(log.value) == str(await self._make_authcode(userdata["username"], discord_id, userdata["start_time"])):
            # Scratchのユーザー名とDiscordのユーザーIDを紐づける
            userdata["status"] = "completed"
            return userdata["username"], "completed"
        else:
            return userdata["username"], "wrong_authcode"

    async def is_registered(self, username):
        data = requests.get(f"https://api.scratch.mit.edu/users/{username}").json()
        if "code" in data:
            return False

        # ユーザーが登録されているかをCSサーバーに問い合わせる
        return True

    async def _make_authcode(self, username, discord_id, time):
        hash_object = hashlib.md5(self.hash_template.format(username=username, discord_id=discord_id, time=time).encode())
        return int(hash_object.hexdigest(), 16)


class csAuthSettingModal(discord.ui.Modal):
    def __init__(self, discord_auth=None, auth_project_id="0") -> None:
        super().__init__(title="ユーザー認証")
        self.username = discord.ui.TextInput(label="Scratchのユーザー名", style=discord.TextStyle.short, placeholder="scratchcat", min_length=3, max_length=20)
        self.add_item(self.username)

        if discord_auth:
            self.discord_auth = discord_auth
        else:
            self.discord_auth = discordAuth(auth_project_id)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("DMに内容を送信したので、ご確認ください！", ephemeral=True)

        if discord.utils.get(interaction.user.roles, name="CSuser") is not None:
            embed = discord.Embed(title="ユーザー認証", description="あなたはすでに認証が完了しているようです。", color=0x43b581)
            await interaction.user.send(embed=embed)
            return

        is_registered = await self.discord_auth.is_registered(self.username.value)
        if is_registered:
            authcode = await self.discord_auth.issue_authcode(self.username.value, interaction.user.id)
            scratch_URL = f"https://scratch.mit.edu/projects/{os.environ.get('SCRATCH_AUTH_PROJECT_ID')}/"
            embed = discord.Embed(title="ユーザー認証", description=f"ユーザー名が確認できました！\n5分以内に以下のコードを[入力用ページ]({scratch_URL})で入力して、下の「入力しました」ボタンを押してください。\n```\n{authcode}\n```", color=0x4459fe)
            view = csAuthOKView(discord_auth=self.discord_auth)
            view.add_item(discord.ui.Button(label="入力用ページ", url=scratch_URL, style=discord.ButtonStyle.link))
            await interaction.user.send(content=str(authcode), embed=embed, view=view)
        else:
            embed = discord.Embed(title="ユーザー認証", description="あなたはクラウドシステムに登録されていないようです。もう一度入力してください。", color=0xf04747)
            await interaction.user.send(embed=embed)


class csAuthStartView(discord.ui.View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)

    @discord.ui.button(label="はじめる", custom_id="startauth", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button: discord.Button) -> None:
        await interaction.response.send_modal(csAuthSettingModal(auth_project_id=os.environ.get("SCRATCH_AUTH_PROJECT_ID")))


class csAuthOKView(discord.ui.View):
    def __init__(self, timeout=None, auth_project_id="0", discord_auth=None):
        super().__init__(timeout=timeout)
        self.auth_project_id = auth_project_id

        if discord_auth:
            self.discord_auth = discord_auth
            self.auth_project_id = self.discord_auth.project_id
        else:
            self.discord_auth = discordAuth(auth_project_id)
            self.auth_project_id = auth_project_id

    @discord.ui.button(label="入力しました", custom_id="checkauth", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button: discord.Button) -> None:
        global cs_guild

        scratch_username, status = await self.discord_auth.check_authcode(interaction.user.id)
        if status == "completed":
            description = "認証が完了しました！"
            color = 0x43b581

            member = cs_guild.get_member(interaction.user.id)
            await member.add_roles(discord.utils.get(cs_guild.roles, name="CSuser"), reason="ユーザー認証による自動付与")

            await cs_guild.get_channel(int(os.environ.get("DISCORD_CS_CHANNELID"))).send(f"ユーザー認証が完了しました。臨時で記録しています。\nScratch: {scratch_username}\nDiscord: {member.id}")

            logger.info(f"ユーザー認証完了 Scratch: {scratch_username} Discord: {member.id}")
        elif status == "timeout":
            description = "認証コードの期限が切れました。もう一度初めからやり直してください。"
            color = 0xf6a408
        elif status == "wrong_authcode":
            description = "認証できませんでした。コードが間違っている可能性があります。もう一度ページに入力してください。"
            color = 0xf6a408
        elif status == "not_found":
            description = "認証できませんでした。コードが入力されていない可能性があります。30秒後にもう一度入力し直してください。"
            color = 0xf6a408
        elif status == "fetch_error":
            description = "認証できませんでした。Scratch側でクラウド変数のエラーが発生している可能性があります。時間をおいて再度試してみてください。"
            color = 0xf6a408
        else:
            description = "不明なエラーが発生しました。お問い合わせページでお問い合わせをお願いします。"
            color = 0xf04747
            logger.error(f"不明なエラー {status}")
        embed = discord.Embed(title="ユーザー認証", description=description, color=color)
        await interaction.response.send_message(embed=embed)


class csApplyStartView(discord.ui.View):
    def __init__(self, cs_server, timeout=None):
        super().__init__(timeout=timeout)
        self.cs_server = cs_server

    @discord.ui.button(label="はじめる", custom_id="startapply", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button: discord.Button) -> None:
        await interaction.response.send_message("DMに内容を送信したので、ご確認ください！", ephemeral=True)

        if discord.utils.get(interaction.user.roles, name="CSuser") is None:
            embed = discord.Embed(title="管理者応募", description="あなたはまだユーザー認証が完了していないようです。", color=0xf04747)
            await interaction.user.send(embed=embed)
            return

        # user = await self.cs_server.get_userinfo(interaction.user.id)

        authcode = 12345  # await discord_auth.issue_authcode(self.username.value, interaction.user.id)
        embed = discord.Embed(title="管理者応募", description=f"応募ありがとうございます！\n[専用応募フォーム](https://docs.google.com/forms/d/e/1FAIpQLSemE_oSBe5p0ipVvyku4XDjFl5yZafyHdFhdXbrpBMZoAD-EA/viewform?usp=pp_url&entry.545537387={authcode})で必要事項を入力してください。\n認証コード\n```\n{authcode}\n```", color=0x558aff)
        await interaction.user.send(content=str(authcode), embed=embed)


class csPublicBot:
    def __init__(self, cs_server=None):
        self.bot = commands.Bot(
            command_prefix="c!",
            case_insensitive=True,
            help_command=None,
            intents=intents
        )
        self.tree = self.bot.tree

        if cs_server:
            self.cs_server = cs_server
        else:
            from ..api.server_com import ConnectCS
            self.cs_server = ConnectCS()

        # runの後に定義しなければいけないものたち
        self.auth_view = None
        self.apply_view = None
        self.daily_projects = None

        self._register_decorator()

    def _register_decorator(self):
        """クラスで定義されたコマンドを登録
        """

        # デコレーターを利用せずにイベントを登録
        self.on_ready = self.bot.event(self.on_ready)
        self.on_message = self.bot.event(self.on_message)
        self.on_raw_reaction_add = self.bot.event(self.on_raw_reaction_add)

        @self.tree.command(name="cs_auth", description="ユーザー認証のテンプレートを表示します。")
        async def auth_command(interaction: discord.Interaction):
            embed = discord.Embed(title="ユーザー認証", description="下のボタンを押して、☁システムとの連携を始めましょう！", color=0x4459fe)
            if discord.utils.get(interaction.user.roles, name="admin") is not None:
                await interaction.channel.send(embed=embed, view=self.auth_view)
                await interaction.response.send_message("↓送信が完了しました", ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, view=self.auth_view, ephemeral=True)

        @self.tree.command(name="cs_apply", description="管理者応募のテンプレートを表示します。")
        async def apply_command(interaction: discord.Interaction):
            embed = discord.Embed(title="管理者応募", description="下のボタンを押して、管理者への応募を始めましょう！", color=0x558aff)
            if discord.utils.get(interaction.user.roles, name="admin") is not None:
                await interaction.channel.send(embed=embed, view=self.apply_view)
                await interaction.response.send_message("↓送信が完了しました", ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, view=self.apply_view, ephemeral=True)

        @self.tree.command(name="admin_make_threads", description="スレッドを作成します。")
        async def make_threads(interaction: discord.Interaction):
            # 送信したユーザーがadminロールを持っているか
            if discord.utils.get(interaction.user.roles, name="admin") is None:
                await interaction.response.send_message("実行権限がありません。", ephemeral=True)

            channel = self.bot.get_channel(1258771478959226980)
            thread = await channel.create_thread(name="応募内容2", reason="テスト")
            link = thread.mention
            await thread.send(f"スレッドが開始されました\n ||{interaction.user.mention} {self.cs_guild.get_role(int(os.environ.get('DISCORD_CS_ADMINROLE'))).mention}||")
            await interaction.response.send_message(f"{link} こちらで会話してください", ephemeral=True)

        @self.tree.command(name="admin_decide_daily_project", description="手動で今日の作品を選出します。")
        async def decide_daily_project(interaction: discord.Interaction):
            # 送信したユーザーがadminロールを持っているか
            if discord.utils.get(interaction.user.roles, name="admin") is None:
                await interaction.response.send_message("実行権限がありません。", ephemeral=True)

            await interaction.response.defer()
            await self.daily_projects.decide_daily_project()
            await interaction.followup.send("選出が完了しました", ephemeral=True)

    async def _delete_info(self, payload: discord.RawReactionActionEvent):
        """作成した情報の埋め込みを削除

        Args:
            payload (discord.RawReactionActionEvent): on_raw_reaction_addのペイロード
        """
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        sent_by_me = self.bot.user.id == message.author.id
        if sent_by_me and message.embeds[0].footer.text != "🗑️リアクションで削除":
            logger.debug("削除対象外の埋め込み")
            return

        try:
            ref_message = await channel.fetch_message(message.reference.message_id)
        except discord.errors.NotFound:
            logger.debug("元メッセージが見つからないため誰でも削除可能")
            ref_message = None

        if not ref_message or ref_message.author.id == payload.user_id:
            await message.delete()
            logger.info(f"埋め込みを削除しました {message.id}")

    async def on_ready(self):
        global cs_guild

        await self.tree.sync()

        self.auth_view = csAuthStartView()
        self.apply_view = csApplyStartView(self.cs_server)
        self.bot.add_view(self.auth_view)
        self.bot.add_view(self.apply_view)
        self.daily_projects = DailyProjects(self.bot)

        cs_guild = self.bot.get_guild(int(os.environ.get("DISCORD_CS_SERVERID")))

        channel = self.bot.get_channel(int(os.environ.get("DISCORD_CS_CHANNELID")))
        if channel:
            await channel.send(f"パブリックサーバーが再起動されました 現在時刻:{datetime.datetime.now()}")
        else:
            logger.warning("チャンネルIDが見つかりません")

        RandomStatusTask(self.bot)
        logger.info("Botの準備ができました！")

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.guild is None:
            await message.reply(content="メッセージありがとうございます！こちらでのお問い合わせにはお答えできませんのでご了承ください。\n[お問い合わせチャンネル](https://discord.com/channels/1210843458932178994/1256881718766469131)のご利用をお願いします。")
            return

        app_info = await self.bot.application_info()
        data = get_scratch_info(message.content, app_info.icon.url)
        if data:
            await message.reply(embeds=[scratch_info.get_embed() for scratch_info in data], mention_author=False)

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        logger.debug(f"リアクション追加 {payload.emoji.name}")
        if payload.emoji.name == "🗑️":
            await self._delete_info(payload)


if __name__ == "__main__":
    public_bot = csPublicBot()
    public_bot.bot.run(os.environ.get("DISCORD_TOKEN_CSPUBLIC"))
