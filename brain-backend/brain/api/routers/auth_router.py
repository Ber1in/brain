# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import logging
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status
from fastapi import Depends
from typing import Optional
from fastapi import Form

from brain.api.schemas import auth_schemas
from brain.auth import ACCESS_TOKEN_EXPIRE_MINUTES
from brain.auth import create_access_token, create_refresh_token
from brain.auth import decode_refresh_token, ldap_authenticate


router = APIRouter()
LOG = logging.getLogger(__name__)


class OAuth2TokenRequestForm:
    def __init__(
        self,
        grant_type: str = Form(default="password"), 
        username: Optional[str] = Form(None),
        password: Optional[str] = Form(None),
        scope: Optional[str] = Form(""),
        client_id: Optional[str] = Form(None),
        client_secret: Optional[str] = Form(None),
        refresh_token: Optional[str] = Form(None),
    ):
        self.grant_type = grant_type
        self.username = username
        self.password = password
        self.scopes = scope.split()
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token


@router.post("/login", response_model=auth_schemas.TokenResponse)
def login_for_access_token(data: OAuth2TokenRequestForm = Depends()):
    if data.grant_type == "password":
        if not data.username or not data.password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="username and password must be provided for password grant type",
            )

        if not ldap_authenticate(data.username, data.password):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        access_token = create_access_token(data={"sub": data.username})
        refresh_token = create_refresh_token(data={"sub": data.username})
        LOG.info(f"User {data.username} login successfully.")

    elif data.grant_type == "refresh_token":
        if not data.refresh_token:
            raise HTTPException(status_code=400, detail="refresh_token required")

        decoded_refresh_token = decode_refresh_token(data.refresh_token)

        if not decoded_refresh_token:
            raise HTTPException(status_code=400, detail="Invalid refresh token")

        access_token = create_access_token(data={"sub": decoded_refresh_token["sub"]})
        refresh_token = data.refresh_token
        LOG.info(f"User {decoded_refresh_token['sub']} refresh token successfully.")
    else:
        msg = f"Unsupported grant_type: {data.grant_type}"
        LOG.error(msg) 
        raise HTTPException(status_code=400, detail=msg)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_token": refresh_token,
    }
