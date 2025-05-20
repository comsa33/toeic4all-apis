# app/main.py 또는 새로운 라우터 파일에 추가

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import httpx

from app.config import settings

auth_router = APIRouter()

@auth_router.post("/token")
async def login_for_swagger(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Swagger UI에서 사용할 토큰 획득 엔드포인트
    실제로는 auth-server로 요청을 전달합니다.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.AUTH_SERVER_URL}/auth/login/oauth2",
                data={"username": form_data.username, "password": form_data.password}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "access_token": data["access_token"],
                    "token_type": "bearer"
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="잘못된 사용자 이름 또는 비밀번호",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"인증 서버 연결 오류: {str(e)}"
        )
