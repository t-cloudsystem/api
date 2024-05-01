import random
from flask import Flask, jsonify, request
import time
import hashlib
import json
import requests

import os
from os.path import join, dirname
import sys

admin = {}

admin_username = ["takechi-scratch", "laiboo", "ito-noizi", "syun1116111"]

if "dotenv" in sys.modules: #Glitchで実行されているか
    from dotenv import load_dotenv
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)

    slack_token = os.environ.get("SLACK_TOKEN")
    server_pass = os.environ.get("SERVER_PASS")

    for i in range(len(admin_username)):
        admin[admin_username[i]] = os.environ.get(f"ADMIN_TOKEN_{i}")
else:
    slack_token = str(os.getenv("SLACK_TOKEN"))
    server_pass = "password"
    for i in range(len(admin_username)):
        admin[admin_username[i]] = "password"


api_server_start = time.time()
message = []

def get_key_by_value(dictionary, target_value):
    for key, value in dictionary.items():
        if value == target_value:
            return key
    return None  # キーが見つからなかった場合のデフォルトの返り値

def delete_request(sessionID):
    global waiting_requests

    for d in waiting_requests[:]:
        if d['sessionID'] == int(sessionID):
            waiting_requests.remove(d)
        
waiting_requests = []
cs_server_time = 0

app = Flask(__name__)



def send_to_slack(subject, body, mention=False): #メールの送信
    headers = {"Authorization": "Bearer " + slack_token}
    blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{'<!channel>' if mention else ''} *{subject}*\n{body}"
                    }
                }
            ]

    data = {"channel": "C063AAU14DS", "blocks": json.dumps(blocks)}
    return requests.post("https://slack.com/api/chat.postMessage", headers=headers, data=data)



@app.route('/')
def home():
    return jsonify({
    "website":"https://scratch.mit.edu/studios/33110478/",
    "author":"@takechi-scratch",
    "help":"https://scratch.mit.edu/users/takechi-scratch/"
})

@app.route('/health/')
def health():
    if time.time() - cs_server_time < 15:
        cs_status = "OK"
    else:
        cs_status = "Not working"
    return jsonify({
    "version":"ver.0.9(beta)",
    "uptime":time.time() - api_server_start,
    "api_status":"OK",
    "cs_status":cs_status
})

@app.errorhandler(400)
def error_400(error):
    return jsonify({"message": "error", "status": 400}), 400

@app.errorhandler(403)
def error_403(error):
    return jsonify({"message": "error", "status": 403}), 403

@app.errorhandler(404) # 404エラーが発生した場合の処理
def error_404(error):
    return jsonify({"message": "error", "status": 404}), 404

@app.errorhandler(405) # 404エラーが発生した場合の処理
def error_405(error):
    return jsonify({"message": "error", "status": 405}), 405

@app.errorhandler(500)
def error_500(error):
    return jsonify({"message": "error", "status": 500}), 500

"""@app.route("/cs_api/login/", methods=["POST"])
def login():
    if time.time() - cs_server_time < 15:
        data = request.get_json()
        username = data.get("username")

        sessionID = random.randint(1,10000)
        waiting_requests.append({"OK":False, "sessionID":sessionID, "session_code":10, "username":username, "userID": -1})
        reqID = len(waiting_requests) - 1

        for i in range(100):
            if waiting_requests[reqID]["OK"] == True:
                delete_request(sessionID)
                return jsonify({"message": "OK", "ID": waiting_requests[reqID]["userID"]})
            time.sleep(0.2)

        delete_request(sessionID)
        return jsonify({"message": "error", "status": 500, "error_code": "E0003"}), 500
    else:
        return jsonify({"message": "error", "status": 500, "error_code": "E0002"}), 500"""

@app.route("/cs_api/user/<userID_raw>/")
def get_userdata(userID_raw):
    global waiting_requests
    
    try:
        userID = int(userID_raw)
    except:
        return jsonify({"message": "error", "status": 400}), 400

    if time.time() - cs_server_time < 15:
        sessionID = random.randint(1,10000)
        waiting_requests.append({"OK":False, "sessionID":sessionID, "session_code":14, "userID":userID})
        reqID = len(waiting_requests) - 1

        for i in range(100):
            if waiting_requests[reqID]["OK"] == True:
                if waiting_requests[reqID]["public"] == 1:
                    res = jsonify({"message": "OK", "username": waiting_requests[reqID]["username"], "icon": waiting_requests[reqID]["iconID"]})
                else:
                    if waiting_requests[reqID]["public"] == 0:
                        res = jsonify({"message": "private_account", "status": 403}), 403
                    else:
                        res = jsonify({"message": "Not found", "status": 404}), 404
                delete_request(sessionID)
                return res
            time.sleep(0.2)

        delete_request(sessionID)
        return jsonify({"message": "error", "status": 500, "error_code": "E0003"}), 500
    else:
        return jsonify({"message": "error", "status": 500, "error_code": "E0002"}), 500

@app.route("/cs_api/userID/<username>/")
def get_userID(username):
    global waiting_requests

    if time.time() - cs_server_time < 15:
        sessionID = random.randint(1,10000)
        waiting_requests.append({"OK":False, "sessionID":sessionID, "session_code":3, "username":str(username)})
        reqID = len(waiting_requests) - 1

        for i in range(100):
            if waiting_requests[reqID]["OK"] == True:
                if waiting_requests[reqID]["public"] == True:
                    res = jsonify({"message": "OK", "ID": waiting_requests[reqID]["userID"]})
                else:
                    res = jsonify({"message": "Not Found", "status": 404}), 404
                delete_request(sessionID)
                return res
            time.sleep(0.2)

        delete_request(sessionID)
        return jsonify({"message": "error", "status": 500, "error_code": "E0003"}), 500
    else:
        return jsonify({"message": "error", "status": 500, "error_code": "E0002"}), 500

@app.route("/cs_api/count/")
def user_count():
    global waiting_requests

    if time.time() - cs_server_time < 15:
        sessionID = random.randint(1,10000)
        waiting_requests.append({"OK":False, "sessionID":sessionID, "session_code":3, "username":str(username)})
        reqID = len(waiting_requests) - 1

        for i in range(100):
            if waiting_requests[reqID]["OK"] == True:
                if waiting_requests[reqID]["public"] == True:
                    res = jsonify({"message": "OK", "ID": waiting_requests[reqID]["userID"]})
                else:
                    res = jsonify({"message": "Not Found", "status": 404}), 404
                delete_request(sessionID)
                return res
            time.sleep(0.2)

        delete_request(sessionID)
        return jsonify({"message": "error", "status": 500, "error_code": "E0003"}), 500
    else:
        return jsonify({"message": "error", "status": 500, "error_code": "E0002"}), 500
      
@app.route("/cs_api/report/", methods=["POST"])
def bug_report():
    data = request.get_json()
    try:
        userID = data.get("userID")
        type = data.get("type")
        if type not in ["1", "2", "3", "4"]:
            return jsonify({"message": "error", "status": 400}), 400
    except:
        return jsonify({"message": "error", "status": 400}), 400

    report_message = {"1":"ログインできない", "2":"エラーが発生する", "3":"不正を発見した", "4":"そのほかの不具合"}[str(type)]

    response = send_to_slack("クイック報告(API)", f"対応をお願いします。\nユーザーID:{userID}\n内容:{report_message}", mention=True if type=="3" else False)

    if str(response.status_code) == "200":
        return jsonify({"message": "OK"})
    else:
        return jsonify({"message": "error", "status": 500}), 500


@app.route("/cs_api/admin/pass/get/", methods=["POST"])
def cs_pass_get():
    data = request.get_json()
    try:
        userID = data.get("userID")
        input_token = data.get("admin_token")
    except:
        return jsonify({"message": "error", "status": 400}), 400

    if time.time() - cs_server_time < 15:
        access_user = get_key_by_value(admin, input_token)
        if access_user != None:
        
            sessionID = random.randint(1,10000)
            waiting_requests.append({"OK":False, "sessionID":sessionID, "session_code":6, "userID":int(userID), "admin":access_user})
            reqID = len(waiting_requests) - 1

            for i in range(100):
                if waiting_requests[reqID]["OK"] == True:
                    if waiting_requests[reqID]["password"] != "":
                        res = jsonify({"message": "OK", "password": waiting_requests[reqID]["password"]})
                    else:
                        res = jsonify({"message": "Not Found", "status": 404}), 404
                    delete_request(sessionID)
                    return res
                time.sleep(0.2)

            delete_request(sessionID)
            return jsonify({"message": "error", "status": 500, "error_code": "E0003"}), 500
          
        else:
            return jsonify({"message": "error", "status": 403}), 403
    else:
        return jsonify({"message": "error", "status": 500, "error_code": "E0002"}), 500

@app.route("/cs_api/admin/pass/set/", methods=["POST"])
def cs_pass_set():
    data = request.get_json()
    try:
        userID = data.get("userID")
        password = str(data.get("password"))
        input_token = data.get("admin_token")
    except:
        return jsonify({"message": "error", "status": 400}), 400

    if time.time() - cs_server_time < 15:
        access_user = get_key_by_value(admin, input_token)
        if access_user != None:
        
            sessionID = random.randint(1,10000)
            waiting_requests.append({"OK":False, "sessionID":sessionID, "session_code":7, "userID":int(userID), "password":password, "admin":access_user})
            reqID = len(waiting_requests) - 1

            for i in range(100):
                if waiting_requests[reqID]["OK"] == True:
                    if waiting_requests[reqID]["status"] == "OK":
                        res = jsonify({"message": "OK"})
                    else:
                        res = jsonify({"message": "error", "status": waiting_requests[reqID]["status"]}), 404
                    delete_request(sessionID)
                    return res
                time.sleep(0.2)

            delete_request(sessionID)
            return jsonify({"message": "error", "status": 500, "error_code": "E0003"}), 500
          
        else:
            return jsonify({"message": "error", "status": 403}), 403
    else:
        return jsonify({"message": "error", "status": 500, "error_code": "E0002"}), 500


@app.route("/server/get/", methods=["POST"])
def session_get():
    global cs_server_time
    global waiting_requests

    cs_server_time = time.time()
    data = request.get_json()
    try:
        password = data.get("password")
    except:
        return jsonify({"message": "error", "status": 400}), 400

    if password == server_pass:
        return_requests = waiting_requests.copy()
        for d in waiting_requests[:]: #スラッシュコマンドのリクエストは削除
            if d['session_code'] in [4, 5]:
                waiting_requests.remove(d)

        return jsonify({"message": "OK", "data": return_requests})
    else:
        return jsonify({"message": "error", "status": 403}) ,403

@app.route("/server/res/", methods=["POST"])
def session_res():
    global cs_server_time
    global waiting_requests

    cs_server_time = time.time()
    data = request.get_json()
    try:
        password = data.get("password")
        server_res = data.get("res")
    except:
        return jsonify({"message": "error", "status": 400}), 400


    if password == server_pass:
        for i in server_res:
            index = next((index for (index, d) in enumerate(waiting_requests) if d["sessionID"] == i["sessionID"]), None)
            if index != None:
                if waiting_requests[index]["session_code"] == 10:
                    waiting_requests[index]["userID"] = i["userID"]
                    waiting_requests[index]["OK"] = True

                elif waiting_requests[index]["session_code"] == 14:
                    waiting_requests[index]["OK"] = True
                    raw_userdata = i["userdata"]
                    
                    if i["userdata"] != "00000":
                        if raw_userdata[0:2] in ["11", "21"]:
                            waiting_requests[index]["public"] = 1
                            waiting_requests[index]["username"] = i["username"]
                            waiting_requests[index]["iconID"] = int(raw_userdata[2:])
                        else:
                            waiting_requests[index]["public"] = 0
                    else:
                        waiting_requests[index]["public"] = -1

                elif waiting_requests[index]["session_code"] == 3:
                    if i["userID"] != 0:
                        waiting_requests[index]["public"] = True
                        waiting_requests[index]["userID"] = i["userID"]
                    else:
                        waiting_requests[index]["public"] = False
                    
                    waiting_requests[index]["OK"] = True
                else:
                    return jsonify({"message": "Reg failed"}) ,500
            else:
                return jsonify({"message": "Sessionid Not Found"}) ,404

        return jsonify({"message": "OK"})
    else:
        return jsonify({"message": "error", "status": 403}) ,403



"""@app.route('/slash/get_token/', methods=['POST'])
def get_token():
    payload = {'text': f"{request.form['token']}\nこのトークンをtakechiへDMで送信してください。"}
    return jsonify(payload)"""

@app.route('/slash/reg_auth/', methods=['POST'])
def reg_auth():
    if time.time() - cs_server_time < 15:
        sessionID = random.randint(1,10000)
        waiting_requests.append({"OK":False, "sessionID":sessionID, "session_code":4, "userID":request.form['text']})

        return jsonify({'text': "リクエストを送信しました。数秒以内にシステムサーバーから通知が来ます。"})
    else:
        return jsonify({'text': "サーバーが現在稼働していないため、リクエストを送信できません。"})

@app.route('/slash/ad_auth/', methods=['POST'])
def ad_auth():
    if time.time() - cs_server_time < 15:
        #sessionID = random.randint(1,10000)
        #waiting_requests.append({"OK":False, "sessionID":sessionID, "session_code":5, "sinseiID":request.form['text']})

        return jsonify({'text': "現在製作中です。もうしばらくお待ちください。"})
    else:
        return jsonify({'text': "サーバーが現在稼働していないため、リクエストを送信できません。"})

@app.route('/slash/get_raw_data/', methods=['POST'])
def get_rawdata():
    payload = {'text': str(request.form)}
    return jsonify(payload)

if __name__ == "__main__":
    app.run(port=8888, threaded=True) #debug=True, 