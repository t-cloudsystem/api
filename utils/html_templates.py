from pathlib import Path


class HTMLTemplates:
    def __init__(self):
        ads_error_path = Path("assets/ads_error.html")
        if not ads_error_path.exists():
            raise FileNotFoundError(f"Template file not found: {ads_error_path}")

        ads_error_template = ads_error_path.read_text(encoding="utf-8")

        self.ads_not_found = self._format(
            ads_error_template,
            status_code=404,
            title="リンク先が見つかりません",
            message="宣伝リンクが削除されたか、<br />URLが間違っている可能性があります。"
        )

        self.ads_not_available = self._format(
            ads_error_template,
            status_code=503,
            title="現在利用できません",
            message="""サーバーが稼働していないため、<br />リンクにアクセスできません。<br /><br />
            申し訳ありませんが、<br />しばらくしてから再度お試しください。"""
        )

    def _format(self, template: str, **kwargs) -> str:
        for key, value in kwargs.items():
            template = template.replace("{"+key+"}", str(value))
        return template
