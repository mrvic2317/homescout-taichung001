"""Pydantic models for Web API requests and responses."""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


# ============ 認證相關 ============
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    discord_id: Optional[int] = None
    username: Optional[str] = None


class User(BaseModel):
    discord_id: int
    username: str
    guild_id: int
    role: str = "member"  # member, admin


class UserLogin(BaseModel):
    discord_id: int
    password: str


# ============ 監控相關 ============
class MonitoringRuleCreate(BaseModel):
    area: str = Field(..., description="監控區域")
    price_min: Optional[int] = Field(None, description="最低價格（萬）")
    price_max: Optional[int] = Field(None, description="最高價格（萬）")
    size_min: Optional[float] = Field(None, description="最小坪數")
    size_max: Optional[float] = Field(None, description="最大坪數")


class MonitoringRule(BaseModel):
    id: int
    user_id: int
    guild_id: int
    area: str
    price_min: Optional[int]
    price_max: Optional[int]
    size_min: Optional[float]
    size_max: Optional[float]
    created_at: datetime


# ============ 案件相關 ============
class CaseCreate(BaseModel):
    title: str = Field(..., description="案件標題")
    area: Optional[str] = Field(None, description="區域")
    price: Optional[int] = Field(None, description="價格（萬）")
    status: str = Field("跟進中", description="狀態")
    assignee_id: Optional[int] = Field(None, description="指派人員 Discord ID")
    notes: Optional[str] = Field(None, description="備註")


class CaseUpdate(BaseModel):
    status: Optional[str] = None
    note: Optional[str] = None


class Case(BaseModel):
    id: int
    guild_id: int
    creator_id: int
    title: str
    area: Optional[str]
    price: Optional[int]
    status: str
    assignee_id: Optional[int]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class CaseUpdateRecord(BaseModel):
    id: int
    case_id: int
    user_id: int
    status: Optional[str]
    note: Optional[str]
    created_at: datetime


# ============ 客戶相關 ============
class ClientCreate(BaseModel):
    name: str = Field(..., description="客戶姓名")
    budget_min: Optional[int] = Field(None, description="最低預算（萬）")
    budget_max: Optional[int] = Field(None, description="最高預算（萬）")
    preferred_areas: Optional[str] = Field(None, description="偏好區域")
    description: Optional[str] = Field(None, description="需求描述")


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    preferred_areas: Optional[str] = None
    description: Optional[str] = None


class Client(BaseModel):
    id: int
    guild_id: int
    owner_id: int
    name: str
    budget_min: Optional[int]
    budget_max: Optional[int]
    preferred_areas: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


class ClientFollowupCreate(BaseModel):
    note: str = Field(..., description="跟進內容")


class ClientFollowup(BaseModel):
    id: int
    client_id: int
    user_id: int
    note: str
    created_at: datetime


# ============ 看屋相關 ============
class ViewingCreate(BaseModel):
    scheduled_at: datetime = Field(..., description="預定時間")
    client: str = Field(..., description="客戶名稱")
    property: str = Field(..., description="物件名稱")
    agent: Optional[str] = Field(None, description="指派業務")
    contact: Optional[str] = Field(None, description="聯絡方式")
    note: Optional[str] = Field(None, description="備註")
    link: Optional[str] = Field(None, description="相關連結")


class Viewing(BaseModel):
    id: int
    guild_id: int
    creator_id: int
    scheduled_at: datetime
    client: str
    property: str
    agent: Optional[str]
    contact: Optional[str]
    note: Optional[str]
    link: Optional[str]
    reminded: int
    created_at: datetime


# ============ 房價查詢相關 ============
class PriceQueryRequest(BaseModel):
    area: str = Field(..., description="查詢區域")


class ProjectGroup(BaseModel):
    road_name: str
    address_range: str
    transaction_count: int
    avg_price: float
    avg_unit_price: float
    addresses: List[str]


class PriceStats(BaseModel):
    area: str
    query_period: str
    total_transactions: int
    avg_price: float
    avg_unit_price: float
    max_price: float
    min_price: float
    max_unit_price: float
    min_unit_price: float
    project_groups: List[ProjectGroup]


# ============ 市場行情相關 ============
class MarketSummaryRequest(BaseModel):
    area: str = Field(..., description="查詢區域")
    days: int = Field(30, description="查詢天數")


class MarketSummary(BaseModel):
    area: str
    days: int
    average_price: Optional[float]
    median_price: Optional[float]
    transactions: int


class ReportRequest(BaseModel):
    areas: List[str] = Field(["全區"], description="查詢區域列表")
    days: int = Field(7, description="查詢天數")


# ============ 通用回應 ============
class MessageResponse(BaseModel):
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    detail: str
    success: bool = False
