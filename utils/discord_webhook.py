import httpx


class DiscordWebhook:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send_quick_report(self, user_id: int, message: str):
        """Discord Webhookを使用してメッセージを送信する"""
        payload = {
            "content": "",
            "embeds": [{
                "title": "クイック報告",
                "description": "",
                "color": 0x5686ff,
                "fields": [
                    {
                        "name": "ユーザーID",
                        "value": str(user_id)
                    },
                    {
                        "name": "送信内容",
                        "value": str(message)
                    }
                ]
                }
            ]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.webhook_url,
                headers={"Content-Type": "application/json"},
                json=payload
            )
            response.raise_for_status()
