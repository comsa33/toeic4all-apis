from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.config import settings

# OAuth2PasswordBearer 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/swagger-auth/token")

async def verify_token(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증할 수 없습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception

# 현재 사용자 가져오기
async def get_current_user(payload: dict = Depends(verify_token)):
    return payload
