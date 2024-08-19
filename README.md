# たーけクラウドシステムAPI

:::info

この機能は **現在開発中** の機能です。内容やURLなどは予告なく変更する場合があります。

:::

## APIについて
このAPIでは、たーけクラウドシステムに関する情報の取得や、
管理者に直接バグ報告など、様々なことができます！

## APIの仕組み
このAPIは、外部サービスを使用してデプロイしています。
そのため、稼働停止が起こりにくい設計になっています！

## 公式ドキュメント(ver.1.0)
URL：https://cs-api.glitch.me/

### ・APIサーバー情報取得 "https://cs-api.glitch.me/health/" 【GET】

サーバーの情報を返します。

出力
```
{
    "api_status": "OK",
    "cs_status": "OK",  # CSサーバーが稼働していないときは"Not Working"
    "uptime": 150.90346336364746,  # サーバーの稼働時間
    "version": "ver.1.0"
}
```

### ・ユーザー情報取得 "https://cs-api.glitch.me/cs_api/user/_ユーザーID_/" 【GET】

ユーザーIDからそのユーザーの情報を返します。

出力
```
{
    "message": "OK",
    "userID": 11,
    "username": "takechi-scratch",
    "icon": 2
}
```

### ・ユーザーID取得 "https://cs-api.glitch.me/cs_api/userID/_ユーザー名_/" 【GET】

ユーザー名から対応するユーザーIDを返します。

出力
```
{
    "message": "OK",
    "username": "takechi-scratch",
    "userID": 11
}
```

### ・バグ報告"https://cs-api.glitch.me/cs_api/report/" 【POST】

バグ報告を管理者に直接に送信します。クラウドシステムサーバーが落ちていても報告可能です。

リクエストbody
```
{
    "userID": 11,
    "type": 1
}
```

:::info

"type"の数字を変更して、バグ報告の種類を選べます。いくつか作成予定です。

:::

:::warning 実行方法について

URLを入力するだけでは利用できません。コマンドやブラウザのコンソール、ショートカットアプリなどからリクエストする必要があります。
詳細については調べてみてください。

:::

出力

```
{
    "message": "OK"
}
```

## iosショートカットアプリケーション(製作者　takechi・syun)
iPhoneやiPadなどで使える、バグ報告用のショートカットアプリです。下のリンクからダウンロードできます。

[ダウンロードリンク](https://www.icloud.com/shortcuts/3b7007c298314df389966ec4fed76656)


※このショートカットアプリで起きた、いかなる事(フリーズなど)については責任を負いません。

## 注意事項
- APIサーバーが止まっている時はバグ報告などができません。
- APIを悪用した場合は、アクセス制限を行ったり、全体での提供を終了したりすることがあります。
