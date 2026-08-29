import importlib.util
import json
import time
import urllib.parse
from pathlib import Path

import requests


PUBLIC_BASE = "https://www.reddit.com"


def _load_auth():
    auth_path = Path(__file__).resolve().parent.parent.parent / "reddit-auth" / "pipeline" / "auth.py"
    spec = importlib.util.spec_from_file_location("reddit_auth_pipeline_auth", auth_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Publisher:
    def __init__(self, session):
        self._session = session
        self._modhash = None

    @classmethod
    def create(cls, headless: bool = False):
        auth = _load_auth()
        session = auth.ensure_authenticated_page(headless=headless)
        return cls(session)

    def _fetch_modhash(self):
        page = self._session.page
        result = page.evaluate(
            """
            async ([url, timeout_ms]) => {
                const controller = new AbortController();
                const timer = setTimeout(() => controller.abort(), timeout_ms);
                try {
                    const res = await fetch(url, { signal: controller.signal, credentials: 'include' });
                    const text = await res.text();
                    return {ok: res.ok, status: res.status, body: text};
                } catch (err) {
                    return {ok: false, error: err.toString()};
                } finally {
                    clearTimeout(timer);
                }
            }
            """,
            [f"{PUBLIC_BASE}/api/v1/me.json", 10000],
        )
        if not result.get("ok"):
            raise RuntimeError(f"Could not fetch user profile: {result}")
        data = json.loads(result["body"])
        me = data.get("data", data)
        self._modhash = me.get("modhash") or ""
        if not me.get("name"):
            raise RuntimeError("Not logged in")

    def _post_json(self, path: str, payload: dict) -> dict:
        if self._modhash is None:
            self._fetch_modhash()

        body = urllib.parse.urlencode({**payload, "api_type": "json", "uh": self._modhash})
        page = self._session.page

        time.sleep(0.5)
        result = page.evaluate(
            """
            async ([url, body, timeout_ms]) => {
                const controller = new AbortController();
                const timer = setTimeout(() => controller.abort(), timeout_ms);
                try {
                    const res = await fetch(url, {
                        method: 'POST',
                        signal: controller.signal,
                        credentials: 'include',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'X-Requested-With': 'XMLHttpRequest',
                        },
                        body,
                    });
                    const text = await res.text();
                    return {ok: res.ok, status: res.status, body: text};
                } catch (err) {
                    return {ok: false, error: err.toString()};
                } finally {
                    clearTimeout(timer);
                }
            }
            """,
            [f"{PUBLIC_BASE}{path}", body, 30000],
        )
        if not result.get("ok"):
            raise RuntimeError(f"Reddit POST failed: {result.get('status')} {result.get('body', '')[:200]}")
        return json.loads(result["body"])

    def _upload_media(self, image_path: Path) -> str:
        data = self._post_json("/api/media/asset.json", {"filepath": image_path.name, "mimetype": "image/png"})
        lease = data.get("json", {}).get("data", {})
        upload_url = lease.get("upload_url") or lease.get("action")
        fields = lease.get("fields", [])
        if not upload_url:
            raise RuntimeError("Could not get media upload lease")

        files = {"file": image_path.read_bytes()}
        form = {f["name"]: f["value"] for f in fields} if fields else {}
        response = requests.post(upload_url, data=form, files=files, timeout=60)
        response.raise_for_status()

        asset_url = lease.get("asset_url")
        if not asset_url:
            raise RuntimeError("Could not determine asset URL after upload")
        return asset_url

    def publish(
        self,
        *,
        subreddit: str,
        title: str,
        kind: str,
        body: str | None = None,
        url: str | None = None,
        image_path: str | None = None,
        nsfw: bool = False,
        spoiler: bool = False,
    ) -> dict:
        sr = subreddit.removeprefix("r/")
        payload = {
            "sr": sr,
            "title": title,
            "nsfw": "true" if nsfw else "false",
            "spoiler": "true" if spoiler else "false",
            "resubmit": "true",
        }

        if kind == "self":
            payload["kind"] = "self"
            payload["text"] = body or ""
        elif kind == "link":
            payload["kind"] = "link"
            payload["url"] = url or ""
        elif kind == "image":
            if not image_path:
                raise ValueError("image_path is required for image posts")
            asset_url = self._upload_media(Path(image_path))
            payload["kind"] = "image"
            payload["url"] = asset_url
        else:
            raise ValueError(f"Unknown kind: {kind}")

        data = self._post_json("/api/submit", payload)
        if data.get("json", {}).get("errors"):
            raise RuntimeError(f"Reddit rejected the post: {data['json']['errors']}")

        post_data = data.get("json", {}).get("data", {})
        post_url = post_data.get("url", "")
        post_id = post_data.get("id", "")
        permalink = post_url.replace("https://www.reddit.com", "") if post_url.startswith("https://www.reddit.com") else post_data.get("permalink", "")

        return {
            "post_id": post_id,
            "post_url": post_url or f"https://www.reddit.com{permalink}",
            "permalink": permalink,
            "subreddit": f"r/{sr}",
            "title": title,
        }

    def close(self) -> None:
        if self._session:
            self._session.close()
