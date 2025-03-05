from discord import Embed
from discord.ext.commands import Bot


class EmbedTemplates:
    outside_cs = Embed(title="エラー", description="このコマンドは公式サーバーでのみ利用可能です。", color=0xf6a408)
    no_permission = Embed(title="エラー", description="このコマンドを実行する権限がありません。", color=0xf6a408)
    dm = Embed(title="エラー", description="このコマンドはDMでは実行できません。", color=0xf6a408)
    scratch_no_found = Embed(title="エラー", description="テキストからScratchのURLを見つけられませんでした。", color=0xf6a408)


class EmojiTemplates:
    def __init__(self, bot: Bot):
        self.auth_cloud = bot.get_emoji(1331105602956689562)
        self.auth_comment = bot.get_emoji(1331105606215536710)
        self.auth_profile_comment = bot.get_emoji(1331105604646998026)


if __name__ == "__main__":
    print(EmbedTemplates.embed_outside)
    print(EmbedTemplates.embed_no_permission)
    print(EmbedTemplates.embed_dm)
