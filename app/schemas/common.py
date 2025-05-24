from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """모든 API 응답의 기본 구조"""

    success: bool = True
    message: Optional[str] = None
    data: T


class MetaDataResponse(BaseResponse[T], Generic[T]):
    """메타데이터 조회 API 응답 구조"""

    pass


class PaginatedResponse(BaseResponse[T], Generic[T]):
    """페이지네이션 응답 구조"""

    count: int
    total: int
    page: int
    total_pages: int


class ErrorResponse(BaseModel):
    """오류 응답 구조"""

    success: bool = False
    message: str
    detail: Optional[str] = None
