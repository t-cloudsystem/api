class CSServerNotConnectedError(Exception):
    """CSサーバーが接続されていない場合に発生する例外"""
    def __init__(self, message="Sorry, CS server is not working."):
        self.message = message
