from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from typing import Optional
from fastapi import HTTPException, Depends
from passlib.context import CryptContext
from starlette import status
import secrets

from crud.user import get_user_by_name

ALGORITHM = "HS256"
SECRET_KEY = secrets.token_urlsafe(32)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_hash_password(password: str):
    """
    哈希来自用户的密码
    :param password: 原密码
    :return: 哈希后的密码
    """
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    """
    校验接收的密码是否与存储的哈希值匹配
    :param plain_password: 原密码
    :param hashed_password: 哈希后的密码
    :return: 返回值为bool类型，校验成功返回True,反之False
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    生成token
    :param data: 需要进行JWT令牌加密的数据（解密的时候会用到）
    :param expires_delta: 令牌有效期
    :return: token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=1)
    # 添加失效时间
    to_encode.update({"exp": expire})
    # SECRET_KEY：密钥
    # ALGORITHM：JWT令牌签名算法
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    # oauth2_scheme -> 从请求头中取到 Authorization 的value
    解析token 获取当前用户对象
    :param token: 登录之后获取到的token
    :return: 当前用户对象
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    db_user = get_user_by_name(username)
    if db_user is None:
        raise credentials_exception
    return db_user

