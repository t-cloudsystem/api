from scratchattach import ScratchCloud, CloudActivity

raw_logs: list[CloudActivity] = ScratchCloud(project_id=1071161378).logs()
logs = [cloud_activity for cloud_activity in raw_logs if cloud_activity.type == "set" and cloud_activity.var == "AuthCode"]
print([cloud_activity.value for cloud_activity in logs])
