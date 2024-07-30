# たーけクラウドシステムAPI

## たーけクラウドシステムAPI ver.1.0 公式ドキュメント

URL：https://cs-api.glitch.me/

・APIサーバー情報取得 "https://cs-api.glitch.mehealth/" 【GET】

サーバーの情報を返します。

出力

{
    
    "api_status": "OK",
    
    "cs_status": "OK", #CSサーバーが稼働していないときは"Not Working"
    
    "uptime": 150.90346336364746, #サーバーの稼働時間
    
    "version": "ver.0.9(beta)"

}


・ユーザー情報取得 "https://cs-api.glitch.me/cs_api/user/<userID>/" 【GET】

ユーザーIDからそのユーザーの情報を返します。

出力

{
    
    "message": "OK",
    
    "userID": 11,
    
    "username": "takechi-scratch",
    
    "icon": 2

}


・ユーザーID取得 "https://cs-api.glitch.me/cs_api/userID/<ユーザー名>" 【GET】

ユーザー名から対応するユーザーIDを返します。

出力

{
    
    "message": "OK",
   
    "username": "takechi-scratch",
   
    "userID": 11   

}


・バグ報告（Slack）"https://cs-api.glitch.me/cs_api/report/" 【POST】

バグ報告をSlackに送信します。クラウドシステムサーバーが落ちていても報告可能。

リクエストbody

{
   
    "userID": 11,
   
    "type": 1

}

※"type"は、バグ報告の種類を選択可能。いくつか作成予定。

出力

{
   
    "message": "OK"

}

## お知らせ
githubのほうにファイルを移行してきました。
