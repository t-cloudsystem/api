import datetime
import time
import os
import hashlib
from logging import getLogger, StreamHandler, DEBUG

from dotenv import load_dotenv
from discord.ext import commands
import discord
import requests
import scratchattach

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


class discordAuth:
    hash_template = "{username}__{discord_id}__{time}"

    def __init__(self, project_id) -> None:
        self.waiting_users = []
        self.project_id = project_id

    async def issue_authcode(self, username, discord_id):
        timestamp = int(time.time())
        self.waiting_users.append({"username": username, "discord_id": discord_id, "status": "waiting", "start_time": timestamp})
        authcode = await self._make_authcode(username, discord_id, timestamp)
        logger.info(f"認証コード発行 {username}の認証コードを発行しました。 コード {authcode}")
        return authcode

    async def check_authcode(self, discord_id):
        discord_ids = [user["discord_id"] for user in self.waiting_users if user["status"] == "waiting"]
        if discord_id not in discord_ids:
            return "not_found"

        userdata = [user for user in self.waiting_users if user["discord_id"] == discord_id][-1]
        logs = [log for log in scratchattach.get_cloud_logs(self.project_id) if log["verb"] == "set_var" and log["name"] == "☁ AuthCode" and log["user"] == userdata["username"]]
        if len(logs) == 0:
            return "not_found"

        log = logs[0]
        logger.debug(f"参照したクラウドログ {log}")

        if max(time.time(), log["timestamp"] / 1000) > userdata["start_time"] + 300 or log["timestamp"] / 1000 < userdata["start_time"]:
            return "timeout"

        if str(log["value"]) == str(await self._make_authcode(userdata["username"], discord_id, userdata["start_time"])):
            # Scratchのユーザー名とDiscordのユーザーIDを紐づける
            userdata["status"] = "completed"
            return "completed"
        else:
            return "wrong_authcode"

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
            view = csAuthOKView(auth_project_id=os.environ.get("SCRATCH_AUTH_PROJECT_ID"), discord_auth=self.discord_auth)
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
        await interaction.response.send_modal(csAuthSettingModal())


class csAuthOKView(discord.ui.View):
    def __init__(self, timeout=None, auth_project_id="0", discord_auth=None):
        super().__init__(timeout=timeout)
        self.auth_project_id = auth_project_id

        if discord_auth:
            self.discord_auth = discord_auth
        else:
            self.discord_auth = discordAuth(auth_project_id)

    @discord.ui.button(label="入力しました", custom_id="checkauth", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button: discord.Button) -> None:
        global cs_guild

        status = await self.discord_auth.check_authcode(interaction.user.id)
        if status == "completed":
            description = "認証が完了しました！"
            color = 0x43b581

            member = self.cs_guild.get_member(interaction.user.id)
            await member.add_roles(discord.utils.get(self.cs_guild.roles, name="CSuser"), reason="ユーザー認証による自動付与")
            logger.info(f"ユーザー認証完了 {member.name}の認証完了")
        elif status == "timeout":
            description = "認証コードの期限が切れました。もう一度初めからやり直してください。"
            color = 0xf6a408
        elif status == "wrong_authcode":
            description = "認証できませんでした。コードが間違っている可能性があります。もう一度ページに入力してください。"
            color = 0xf6a408
        elif status == "not_found":
            description = "認証できませんでした。コードが入力されていない可能性があります。30秒後にもう一度入力し直してください。"
            color = 0xf6a408
        else:
            description = "不明なエラーが発生しました。お問い合わせページでお問い合わせをお願いします。"
            color = 0xf04747
            logger.error(f"不明なエラー {status}")
        embed = discord.Embed(title="ユーザー認証", description=description, color=color)
        await interaction.response.send_message(embed=embed)


class csApplyStartView(discord.ui.View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)

    @discord.ui.button(label="はじめる", custom_id="startapply", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button: discord.Button) -> None:
        await interaction.response.send_message("DMに内容を送信したので、ご確認ください！", ephemeral=True)

        is_registered = True  # await ユーザー認証が完了している確認する&ユーザーの情報を取得
        if is_registered:
            authcode = 12345  # await discord_auth.issue_authcode(self.username.value, interaction.user.id)
            embed = discord.Embed(title="管理者応募", description=f"応募ありがとうございます！\n[専用応募フォーム](https://docs.google.com/forms/d/e/1FAIpQLSemE_oSBe5p0ipVvyku4XDjFl5yZafyHdFhdXbrpBMZoAD-EA/viewform?usp=pp_url&entry.545537387={authcode})で必要事項を入力してください。\n認証コード\n```\n{authcode}\n```", color=0x558aff)
            await interaction.user.send(content=str(authcode), embed=embed)
        else:
            embed = discord.Embed(title="管理者応募", description="あなたはまだユーザー認証が完了していないようです。", color=0xf04747)
            await interaction.user.send(embed=embed)


class csPublicBot:
    def __init__(self):
        self.intents = discord.Intents.default()
        self.intents.members = True  # メンバー管理の権限
        self.intents.message_content = True  # メッセージの内容を取得する権限

        # Botをインスタンス化
        self.bot = commands.Bot(
            command_prefix="c!",
            case_insensitive=True,
            help_command=None,
            intents=discord.Intents.all()
        )
        self.tree = self.bot.tree

        self.auth_view = None
        self.apply_view = None

        self.register_decorator()

    def register_decorator(self):
        """クラスで定義されたコマンドを登録
        """

        # デコレーターを利用せずにイベントを登録
        self.on_ready = self.bot.event(self.on_ready)
        self.on_message = self.bot.event(self.on_message)

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

        @self.tree.command(name="make_threads", description="スレッドを作成します。")
        async def make_threads(interaction: discord.Interaction):
            # 送信したユーザーがadminロールを持っているか
            if discord.utils.get(interaction.user.roles, name="admin") is None:
                await interaction.response.send_message("実行権限がありません。", ephemeral=True)

            channel = self.bot.get_channel(1258771478959226980)
            thread = await channel.create_thread(name="応募内容2", reason="テスト")
            link = thread.mention
            await thread.send(f"スレッドが開始されました\n ||{interaction.user.mention} {self.cs_guild.get_role(int(os.environ.get("DISCORD_CS_ADMINROLE"))).mention}||")
            await interaction.response.send_message(f"{link} こちらで会話してください", ephemeral=True)

    async def on_ready(self):
        global cs_guild

        # BOTのステータスを変更する
        await self.bot.change_presence(status=discord.Status.online, activity=discord.Game("Python Bot"))

        await self.tree.sync()
        self.auth_view = csAuthStartView()
        self.apply_view = csApplyStartView()
        self.bot.add_view(self.auth_view)
        self.bot.add_view(self.apply_view)
        cs_guild = self.bot.get_guild(int(os.environ.get("DISCORD_CS_SERVERID")))

        channel = self.bot.get_channel(int(os.environ.get("DISCORD_CS_CHANNELID")))
        if channel:
            await channel.send(f"パブリックサーバーが再起動されました 現在時刻:{datetime.datetime.now()}")
        else:
            logger.warning("チャンネルIDが見つかりません")

        logger.info("Botの準備ができました！")

    async def on_message(self, message: discord.Message):
        """メッセージをおうむ返しにする処理"""
        if message.author.bot:
            return

        if message.guild is None:
            await message.reply(content="メッセージありがとうございます！こちらでのお問い合わせにはお答えできませんのでご了承ください。\n[お問い合わせチャンネル](https://discord.com/channels/1210843458932178994/1256881718766469131)のご利用をお願いします。")
            return

        # if message.channel.name == "🧪｜コマンド" and message.content != "": # ボットのメッセージは無視
        #     print("サーバー名", message.guild, "チャンネル", message.channel, "ID", message.author)
        #     await message.reply(message.content)


if __name__ == "__main__":
    public_bot = csPublicBot()
    public_bot.bot.run(os.environ.get("DISCORD_TOKEN_CSPUBLIC"))
