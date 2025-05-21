from fastapi import Request, Response, HTTPException, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from app.db.redis_client import RateLimiter
from app.config import settings

class RateLimitMiddleware(BaseHTTPMiddleware):
    """API 요청 속도 제한 미들웨어"""
    
    def __init__(self, app, max_requests: int = None, window_seconds: int = None):
        super().__init__(app)
        self.rate_limiter = RateLimiter(
            max_requests=max_requests or settings.redis_rate_limit_max,
            window_seconds=window_seconds or settings.redis_rate_limit_window
        )
    
    async def dispatch(self, request: Request, call_next):
        # API 엔드포인트인 경우만 속도 제한 적용
        # /api/v1/ 경로인지 확인
        if "/api/v1/" in request.url.path:
            # 클라이언트 식별자 (IP 또는 사용자 ID)
            client_id = request.client.host
            
            # 인증된 사용자인 경우 사용자 ID 사용
            if hasattr(request.state, "user") and request.state.user:
                client_id = f"user:{request.state.user.id}"
            
            # 공개 엔드포인트에는 속도 제한 완화 (2배 허용)
            is_public = "/api/v1/questions/" in request.url.path
            max_requests = self.rate_limiter.max_requests * 2 if is_public else self.rate_limiter.max_requests
            
            # 허용 여부 확인
            if not await self.rate_limiter.is_allowed(client_id):
                # 남은 시간 정보 가져오기
                remaining_info = await self.rate_limiter.get_remaining(client_id)
                
                # 응답 헤더에 정보 추가
                headers = {
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(remaining_info["reset_seconds"]),
                    "Retry-After": str(remaining_info["reset_seconds"])
                }
                
                # 429 Too Many Requests 에러 반환
                return Response(
                    content=f"Rate limit exceeded. Try again in {remaining_info['reset_seconds']} seconds.", 
                    status_code=429,
                    headers=headers
                )
            
            # 남은 요청 수 정보
            remaining_info = await self.rate_limiter.get_remaining(client_id)
            
            # 응답 준비
            response = await call_next(request)
            
            # 응답 헤더에 정보 추가
            response.headers["X-RateLimit-Limit"] = str(max_requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining_info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(remaining_info["reset_seconds"])
            
            return response
        
        # API 엔드포인트가 아니면 그냥 통과
        return await call_next(request)
