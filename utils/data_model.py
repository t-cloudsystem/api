from typing import Literal
from enum import IntEnum

from pydantic import BaseModel, Field, HttpUrl


class User(BaseModel):
    id: int = Field(..., description="たーけクラウドシステムのユーザーID", examples=[11])
    name: str = Field(..., description="ユーザー名", min_length=3, max_length=20, examples=["takechi-scratch"])
    point: int = Field(..., description="ユーザーのポイント", ge=0, examples=[100])
    icon: HttpUrl = Field(..., description="ユーザーのアイコンURL", examples=["https://example.com/icon.png"])
    teams: list[int] = Field(default_factory=list, description="所属中のチームIDのリスト", examples=[[1, 2, 3]])


class UserForAdmin(User):
    is_banned: bool = Field(default=False, description="ユーザーがアクセス制限されているかどうか")
    is_deleted: bool = Field(default=False, description="ユーザーが削除されているかどうか")


class Team(BaseModel):
    id: int = Field(..., description="チームID", examples=[1])
    name: str = Field(..., description="チーム名", examples=["たーけクラウドシステム管理チーム"])
    studio_url: HttpUrl = Field(..., description="チームのスタジオURL", examples=["https://scratch.mit.edu/studios/12345678/"])
    leader: int = Field(..., description="リーダーのユーザーID", examples=[11])
    users: list[int] = Field(default_factory=list, description="メンバーのユーザーIDのリスト", examples=[[12, 13, 14]])
    review: float = Field(..., description="チームのレビュー評価", ge=0.0, le=5.0, examples=[4.5])
    point: int = Field(..., description="チームのポイント", ge=0, examples=[1000])
    yield_rate: int = Field(..., description="山分け率", ge=0, le=99, examples=[50])


class TeamForAdmin(Team):
    is_deleted: bool = Field(default=False, description="チームが削除されているかどうか")


class WaitingServerRequest(BaseModel):
    id: str
    type: str
    data: dict
    result: dict | None = None
    error: str | None = None
    completed: bool = False


class APIError(BaseModel):
    error: str = Field(..., description="エラーメッセージ", examples=["An error occurred"])


class APIInfo(BaseModel):
    website: HttpUrl = Field("https://scratch.mit.edu/studios/33110478/", description="公式ウェブサイトURL")
    author: str = Field("@takechi-scratch in t-cloudsystem admin team", description="API製作者")
    help: HttpUrl = Field("https://scratch.mit.edu/users/ito-noizi/", description="お問い合わせURL")


class HealthInfo(BaseModel):
    version: str = Field(..., description="APIのバージョン")
    api_status: Literal["OK", "Not working", "error"] = Field("OK", description="APIの稼働状態")
    cs_status: Literal["OK", "Not working", "error"] = Field("OK", description="CSサーバーの稼働状態")


class ReportType(IntEnum):
    LOGIN_ERROR = 1
    GENERAL_ERROR = 2
    ABUSE_REPORT = 3
    OTHER = 4


class ReportData(BaseModel):
    user_id: int = Field(..., description="ユーザーID", examples=[6353])
    message: str = Field(..., description="送信内容", examples=["This is a test message"])
    type: ReportType = Field(..., description="報告の種類", examples=[ReportType.GENERAL_ERROR])
