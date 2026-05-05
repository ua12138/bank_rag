from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status

from RAG_PLUS.config import plus_settings


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("utf-8"))


@dataclass
class UserClaims:
    sub: str
    roles: list[str]
    scopes: list[str]
    exp: int


class TokenManager:
    """使用 HMAC-SHA256 生成和校验轻量 Token。"""

    def __init__(self, secret: str) -> None:
        self.secret = secret.encode("utf-8")

    def issue(self, subject: str, roles: list[str], scopes: list[str], ttl_seconds: int) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": subject,
            "roles": roles,
            "scopes": scopes,
            "iat": int(time.time()),
            "exp": int(time.time()) + max(1, ttl_seconds),
        }
        header_b64 = _b64url_encode(json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        payload_b64 = _b64url_encode(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        signature = hmac.new(self.secret, signing_input, hashlib.sha256).digest()
        return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"

    def verify(self, token: str) -> UserClaims:
        parts = token.split(".")
        if len(parts) != 3:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token format")

        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(self.secret, signing_input, hashlib.sha256).digest()
        given_sig = _b64url_decode(signature_b64)

        if not hmac.compare_digest(expected_sig, given_sig):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token signature")

        try:
            payload: dict[str, Any] = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token payload") from exc

        exp = int(payload.get("exp", 0))
        if exp <= int(time.time()):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token expired")

        return UserClaims(
            sub=str(payload.get("sub", "")),
            roles=[str(x) for x in payload.get("roles", [])],
            scopes=[str(x) for x in payload.get("scopes", [])],
            exp=exp,
        )


class AuthService:
    def __init__(self) -> None:
        self.token_manager = TokenManager(plus_settings.auth_secret)

    def login(self, username: str, password: str) -> tuple[str, list[str]]:
        # 生产应接入企业 IAM / LDAP / OIDC。这里保留本地管理员账号用于演示。
        if username == plus_settings.admin_username and password == plus_settings.admin_password:
            scopes = ["rag:query", "rag:admin", "tools:read", "tools:write", "workflow:run"]
            token = self.token_manager.issue(
                subject=username,
                roles=["admin"],
                scopes=scopes,
                ttl_seconds=plus_settings.auth_token_ttl_seconds,
            )
            return token, scopes

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid username or password")

    @staticmethod
    def require_scopes(claims: UserClaims, required: list[str]) -> None:
        for scope in required:
            if scope not in claims.scopes and "rag:admin" not in claims.scopes:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"missing scope: {scope}")

