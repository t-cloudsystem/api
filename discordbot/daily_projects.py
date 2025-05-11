import os
import datetime
from logging import getLogger, StreamHandler, DEBUG
import random

from discord.ext import commands, tasks
import requests
import scratchattach as sa

from discordbot.scratch_info import ScratchInfo


logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False


JST = datetime.timezone(datetime.timedelta(hours=9))

# 宣伝をする時刻
start_times = [
    datetime.time(hour=7, minute=0, tzinfo=JST),
]


class DailyProjects(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.studio_id = os.environ.get("SCRATCH_DAILY_PROJECTS_STUDIO_ID")
        self.api_url = os.environ.get("SCRATCH_DAILY_HISTORY_API_URL")
        self.api_pass = os.environ.get("SCRATCH_DAILY_HISTORY_API_PASS")
        self.channel_id = os.environ.get("SCRATCH_DAILY_CHANNELID")

        if not all([self.studio_id, self.api_url, self.api_pass, self.channel_id]):
            raise ValueError("環境変数を正しく設定してください。")

        self.max_applies = 20

        self.run.start()

    def cog_unload(self):
        self.run.cancel()

    @tasks.loop(time=start_times)
    async def run(self):
        await self.decide_daily_project()

    async def decide_daily_project(self, mention: bool = True):
        studio: sa.Studio = sa.get_studio(self.studio_id)
        studio.update()

        past_res = requests.get(self.api_url)
        if not past_res.headers["Content-Type"].startswith("application/json") or past_res.json()["code"] != 200:
            logger.error("API側でエラーが発生しました")
            logger.debug(past_res.text)
            return

        past_projects = set(int(data["id"]) for data in past_res.json()["data"])
        applies = {}

        projects_id = []
        projects_weight = []

        # projectsは新しい順に返される
        for project in studio.projects(limit=studio.project_count):
            if project.moderation_status == "notsafe":
                continue

            if project.author not in applies:
                applies[project.author] = 0

            # 採用済みと合わせてカウント
            if applies[project.author] > self.max_applies:
                continue

            applies[project.author] += 1

            if project.id in past_projects:
                continue

            projects_id.append(project)
            projects_weight.append(1)

        if not projects_id:
            logger.info("対象作品なし")
            channel = self.bot.get_channel(int(self.channel_id))
            text = f"選択できる作品がありませんでした。\n[エントリースタジオ](https://scratch.mit.edu/studios/{self.studio_id}/)で作品を追加しましょう！"
            message = await channel.send(text)
            return

        logger.debug(f"選択肢: {[str(x) for x in projects_id]}")
        logger.debug(f"重み: {projects_weight}")

        choiced_project = random.choices(projects_id, k=1, weights=projects_weight)[0]
        logger.info(f"選ばれた作品: {choiced_project.title}")

        text = f"## 今日の作品\nhttps://scratch.mit.edu/projects/{choiced_project.id}/"
        if mention:
            text += "\n|| <@&1324929451175313438> ||"
        embed = ScratchInfo(type="projects", id=choiced_project.id).get_embed(can_delete=False)

        channel = self.bot.get_channel(int(self.channel_id))
        message = await channel.send(content=text, embed=embed)
        await message.add_reaction(self.bot.get_emoji(1324552402250236005))  # :scratch_love:
        await message.add_reaction(self.bot.get_emoji(1324552400022798416))  # :scratch_favorite:
        logger.debug(f"メッセージを送信しました: {message.id}")

        TODAY = datetime.datetime.now(JST).strftime("%Y/%m/%d")
        await message.create_thread(name=TODAY+" 作品", reason=f"今日の作品(自動作成) {TODAY}")
        logger.debug("スレッドを作成しました")

        requests.post(self.api_url, json={
            "id": choiced_project.id,
            "title": choiced_project.title,
            "pass": self.api_pass
        })
