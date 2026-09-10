"""Small resilient client for YouTube Data API v3."""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Iterator

import requests

from config import settings

LOG = logging.getLogger(__name__)


class YouTubeError(RuntimeError):
    """Raised after an API request cannot be recovered."""


def _safe_error(message: str) -> str:
    return re.sub(r"([?&](?:key|access_token)=)[^&\s;]+", r"\1[REDACTED]", message, flags=re.I)


class YouTubeClient:
    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.YOUTUBE_API_KEY
        self.session = requests.Session()
        self.credentials: Any = None
        if not self.api_key:
            self.credentials = self._oauth_credentials()

    @staticmethod
    def _oauth_credentials() -> Any:
        """Load a cached OAuth token or perform installed-app consent once."""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError as exc:
            raise RuntimeError("OAuth requires: pip install -r requirements.txt") from exc

        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        credentials = None
        if settings.YOUTUBE_TOKEN_FILE.exists():
            credentials = Credentials.from_authorized_user_file(str(settings.YOUTUBE_TOKEN_FILE), scopes)
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        if not credentials or not credentials.valid:
            if not settings.YOUTUBE_CLIENT_SECRETS.exists():
                raise ValueError("Set YOUTUBE_API_KEY or provide secrets.json with installed-app OAuth credentials")
            flow = InstalledAppFlow.from_client_secrets_file(str(settings.YOUTUBE_CLIENT_SECRETS), scopes)
            credentials = flow.run_local_server(port=0, open_browser=True)
        settings.YOUTUBE_TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")
        return credentials

    def get(self, endpoint: str, **params: Any) -> dict[str, Any]:
        if self.api_key:
            params["key"] = self.api_key
        else:
            from google.auth.transport.requests import Request

            if self.credentials.expired:
                self.credentials.refresh(Request())
                settings.YOUTUBE_TOKEN_FILE.write_text(self.credentials.to_json(), encoding="utf-8")
            self.session.headers["Authorization"] = f"Bearer {self.credentials.token}"
        url = f"{self.BASE_URL}/{endpoint}"
        for attempt in range(settings.REQUEST_RETRIES + 1):
            try:
                response = self.session.get(url, params=params, timeout=settings.REQUEST_TIMEOUT)
                if response.status_code in {429, 500, 502, 503, 504} and attempt < settings.REQUEST_RETRIES:
                    time.sleep(2**attempt)
                    continue
                response.raise_for_status()
                return response.json()
            except requests.RequestException as exc:
                if attempt == settings.REQUEST_RETRIES:
                    detail = getattr(exc.response, "text", "")[:500]
                    raise YouTubeError(_safe_error(f"YouTube API failed: {exc}; {detail}")) from exc
                LOG.warning("Request failed (attempt %s): %s", attempt + 1, exc)
                time.sleep(2**attempt)
        raise AssertionError("unreachable")

    def pages(self, endpoint: str, **params: Any) -> Iterator[dict[str, Any]]:
        token: str | None = None
        while True:
            request_params = dict(params)
            if token:
                request_params["pageToken"] = token
            page = self.get(endpoint, **request_params)
            yield page
            token = page.get("nextPageToken")
            if not token:
                break
