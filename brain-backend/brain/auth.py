# app/auth.py
import os
import secrets
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from ldap3 import Server, Connection
import jwt
from datetime import datetime, timedelta
from fastapi import status

# LDAP config
LDAP_SERVER = 'ldaps://it-srv-idc001.yunsilicon.com:636'
LDAP_DN_SUFFIX = "@yunsilicon.com"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 1

ACCESS_SECRET_KEY_FILE = "/opt/brain/keys/access.key"
REFRESH_SECRET_KEY_FILE = "/opt/brain/keys/refresh.key"


def load_or_create_key(path: str) -> str:
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(key)
    return key


ACCESS_SECRET_KEY = load_or_create_key(ACCESS_SECRET_KEY_FILE)
REFRESH_SECRET_KEY = load_or_create_key(REFRESH_SECRET_KEY_FILE)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def ldap_authenticate(username: str, password: str) -> bool:
    """
    LDAP user authentication

    Args:
        username: Username
        password: Password

    Returns:
        bool: True if authentication successful, False otherwise
    """
    if not username or not password:
        return False

    try:
        user_dn = f"{username}{LDAP_DN_SUFFIX}"
        server = Server(LDAP_SERVER, use_ssl=True)

        # Establish connection and authenticate
        with Connection(server, user=user_dn, password=password) as conn:
            return conn.bind()

    except Exception:
        return False


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, ACCESS_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str):
    try:
        payload = jwt.decode(token, ACCESS_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def authenticate_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


def create_refresh_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_refresh_token(refresh_token: str):
    try:
        decoded_token = jwt.decode(refresh_token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])

        exp = decoded_token.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(status_code=403, detail="Refresh token has expired")

        return decoded_token

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=403, detail="Refresh token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid refresh token")
