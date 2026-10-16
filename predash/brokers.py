"""Read-only broker API authentication adapters.

Only documented authentication is enabled here. Account endpoints stay disabled until
their exact request/response schemas have been verified against the broker's API spec.
"""
from __future__ import annotations

import requests


class BrokerConnectionError(RuntimeError):
    """Safe, user-facing broker connection error."""


class KBOpenAPI:
    """KB Securities Open API client credentials token check (official documented flow)."""

    BASE_URL = "https://developer.kbsec.com:32484"

    def __init__(self, app_key: str, app_secret: str):
        self.app_key = str(app_key or "").strip()
        self.app_secret = str(app_secret or "").strip()
        self.access_token: str | None = None
        if not self.app_key or not self.app_secret:
            raise BrokerConnectionError("KB증권 appKey와 appSecret을 입력하세요.")

    def authorize(self) -> bool:
        try:
            response = requests.post(
                f"{self.BASE_URL}/oauth2/token",
                json={
                    "grant_type": "client_credentials",
                    "appKey": self.app_key,
                    "appSecret": self.app_secret,
                },
                headers={"Content-Type": "application/json"},
                timeout=(5, 20),
            )
            if response.status_code in (401, 403):
                raise BrokerConnectionError(
                    "KB증권 인증이 거부되었습니다. 발급 키, Open API 신청 상태와 권한을 확인하세요."
                )
            if response.status_code == 429:
                raise BrokerConnectionError(
                    "KB증권 API 호출 제한에 도달했습니다. 잠시 후 다시 시도하세요."
                )
            response.raise_for_status()
            data = response.json()
        except BrokerConnectionError:
            raise
        except (requests.RequestException, ValueError):
            raise BrokerConnectionError(
                "KB증권 인증 서버에 연결하지 못했습니다. 네트워크와 API 상태를 확인하세요."
            ) from None

        token = data.get("access_token") if isinstance(data, dict) else None
        if not isinstance(token, str) or not token.strip():
            # Never expose raw provider payloads, which may contain sensitive details.
            raise BrokerConnectionError(
                "KB증권에서 인증 토큰을 받지 못했습니다. 공식 API 포털의 오류 안내를 확인하세요."
            )
        self.access_token = token
        return True

    def balance(self):
        """Intentionally disabled until the exact account-balance API schema is verified."""
        raise BrokerConnectionError(
            "인증은 완료됐지만 잔고 조회는 아직 활성화되지 않았습니다. "
            "KB증권 공식 API 문서의 잔고 조회 요청·응답 규격 검증이 필요합니다."
        )


class MiraeAssetOpenAPI:
    """Fail-closed placeholder; no verified public personal-account API contract configured."""

    def __init__(self, *args, **kwargs):
        raise BrokerConnectionError(
            "미래에셋증권 개인 계좌 조회용 공식 API 규격과 이용 권한이 확인되지 않아 연결을 활성화하지 않았습니다."
        )
