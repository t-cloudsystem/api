from pydantic import BaseModel, Field


class User(BaseModel):
    id: int = Field(..., description="たーけクラウドシステムのユーザーID", examples=[11])
    name: str = Field(..., description="ユーザー名", min_length=3, max_length=20, examples=["takechi-scratch"])
    point: int = Field(..., description="ユーザーのポイント", ge=0, examples=[100])
    icon: str = Field(..., description="ユーザーのアイコンURL", pattern=r"^(https?)://[^\s/$.?#].[^\s]*$", examples=["https://example.com/icon.png"])
    teams: list[int] = Field(default_factory=list, description="所属中のチームIDのリスト", examples=[[1, 2, 3]])


class UserForAdmin(User):
    is_banned: bool = Field(default=False, description="ユーザーがアクセス制限されているかどうか")
    is_deleted: bool = Field(default=False, description="ユーザーが削除されているかどうか")


class WaitingServerRequest(BaseModel):
    id: str
    type: str
    data: dict
    result: dict | None = None
    error: str | None = None
    completed: bool = False
