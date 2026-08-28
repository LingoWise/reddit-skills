import base64
import importlib
import json
import os
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv


PUBLIC_BASE = "https://www.reddit.com"
OAUTH_BASE = "https://oauth.reddit.com"

DEFAULT_USER_AGENT = "python:reddit-skills:v0.1"
SESSION_FILE_NAME = "reddit_session.json"


def _skill_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def _checkpoints_dir() -> Path:
    path = _skill_dir() / "checkpoints"
    path.mkdir(exist_ok=True)
    return path


def default_session_path() -> Path:
    """Return the default path for a saved browser storage state."""
    return _checkpoints_dir() / SESSION_FILE_NAME


def _load_dotenv():
    """Load environment variables from the project root, skill .env, or CWD."""
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv()
    root_dotenv = _skill_dir().parent.parent / ".env"
    if root_dotenv.exists():
        _load_dotenv(root_dotenv, override=True)
    skill_dotenv = _skill_dir() / ".env"
    if skill_dotenv.exists():
        _load_dotenv(skill_dotenv, override=True)


def _env(name: str, default: str = "") -> str:
    _load_dotenv()
    return os.getenv(name, default) or ""


def _is_placeholder(value: str) -> bool:
    if not value:
        return True
    lowered = value.lower()
    return (
        "your_" in lowered
        or "example" in lowered
        or "placeholder" in lowered
        or "TODO" in value.upper()
    )


def user_agent() -> str:
    return _env("REDDIT_USER_AGENT", DEFAULT_USER_AGENT).strip() or DEFAULT_USER_AGENT


def client_id() -> str:
    return _env("REDDIT_CLIENT_ID", "").strip()


def client_secret() -> str:
    return _env("REDDIT_CLIENT_SECRET", "").strip()


def login_method() -> str:
    return _env("REDDIT_LOGIN_METHOD", "").strip().lower()


def session_path() -> Path:
    raw = _env("REDDIT_AUTH_SESSION", "").strip()
    if raw:
        return Path(raw)
    return default_session_path()


def username() -> str:
    return _env("REDDIT_USERNAME", "").strip()


def password() -> str:
    return _env("REDDIT_PASSWORD", "").strip()


def bearer_token(secret: Optional[str] = None) -> Optional[str]:
    """Extract a Reddit bearer token from a secret string."""

    if secret is None:
        secret = client_secret()
    if not secret or _is_placeholder(secret):
        return None

    # Case 1: the value is a base64-encoded JSON object containing an access token.
    try:
        padded = secret + "=" * (-len(secret) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
        token = data.get("accessToken") or data.get("token")
        if token:
            return token
    except Exception:
        pass

    # Case 2: the value is a JWT whose payload contains an access token.
    if "." in secret:
        try:
            payload = secret.split(".")[1]
            padded = payload + "=" * (-len(payload) % 4)
            data = json.loads(base64.urlsafe_b64decode(padded))
            token = data.get("accessToken") or data.get("token")
            if token:
                return token
        except Exception:
            pass

    return None


def has_bearer() -> bool:
    return bearer_token() is not None


def has_praw_creds() -> bool:
    cid = client_id()
    csec = client_secret()
    if not cid or not csec:
        return False
    if _is_placeholder(cid) or _is_placeholder(csec):
        return False
    return True


def use_browser() -> bool:
    """Return True when the chosen strategy requires a real browser login."""
    method = login_method()
    if method in ("playwright", "rustwright", "browser"):
        return True
    # If no method is set and no API credentials are configured, fall back to a
    # browser login so the user can authenticate manually.
    if method:
        return False
    if not has_praw_creds() and not has_bearer():
        try:
            importlib.import_module("rustwright.sync_api")
            return True
        except ImportError:
            return False
    return False


def resolve_strategy() -> str:
    """Choose an authentication strategy based on environment configuration."""
    method = login_method()
    if method in ("playwright", "rustwright", "browser"):
        return "browser"
    if method == "bearer":
        return "bearer"
    if method == "praw":
        return "praw"
    if use_browser():
        return "browser"
    if has_bearer():
        return "bearer"
    if has_praw_creds():
        return "praw"
    return "public"


def credential_hygiene() -> tuple[bool, list[str]]:
    """Check that configured credentials are not placeholder or empty.

    Returns (ok, list of problems).
    """
    problems = []
    strategy = resolve_strategy()
    cid = client_id()
    csec = client_secret()

    if strategy in ("praw", "bearer"):
        if not cid or not csec:
            problems.append("REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are required")
        if _is_placeholder(cid):
            problems.append("REDDIT_CLIENT_ID is still a placeholder value")
        if _is_placeholder(csec):
            problems.append("REDDIT_CLIENT_SECRET is still a placeholder value")
        if strategy == "bearer" and not bearer_token():
            problems.append("REDDIT_CLIENT_SECRET does not contain a parseable bearer token")

    if strategy == "praw":
        uname = username()
        pwd = password()
        if not uname or not pwd:
            problems.append("REDDIT_USERNAME and REDDIT_PASSWORD are required for PRAW script apps")

    return (len(problems) == 0, problems)


def validate_credentials() -> tuple[bool, str]:
    """Validate the active authentication strategy and return (ok, message)."""
    ok, problems = credential_hygiene()
    if not ok:
        return False, "credential hygiene: " + "; ".join(problems)

    strategy = resolve_strategy()

    if strategy == "browser":
        try:
            importlib.import_module("rustwright.sync_api")
            return True, "rustwright browser login available"
        except ImportError:
            return False, "rustwright not installed; run `uv pip install -r skills/reddit-auth/requirements.txt`"

    if strategy == "bearer":
        token = bearer_token()
        headers = {"Authorization": f"Bearer {token}", "User-Agent": user_agent()}
        try:
            response = requests.get(
                f"{OAUTH_BASE}/r/all/search",
                headers=headers,
                params={"q": "test", "limit": 1},
                timeout=15,
            )
            response.raise_for_status()
            return True, "bearer token works"
        except Exception as exc:
            return False, f"bearer token failed: {exc}"

    if strategy == "praw":
        try:
            from praw import Reddit
            kwargs = {
                "client_id": client_id(),
                "client_secret": client_secret(),
                "user_agent": user_agent(),
                "username": username(),
                "password": password(),
            }
            reddit = Reddit(**kwargs)
            list(reddit.subreddit("all").search("test", limit=1))
            return True, "praw credentials work"
        except ImportError:
            return False, "praw not installed"
        except Exception as exc:
            return False, f"praw auth failed: {exc}"

    # public
    try:
        response = requests.get(
            f"{PUBLIC_BASE}/search.json",
            headers={"User-Agent": user_agent()},
            params={"q": "test", "limit": 1},
            timeout=15,
        )
        response.raise_for_status()
        return True, "public search works"
    except Exception as exc:
        return False, f"public search failed: {exc}"


def refresh_needed(session_path: Optional[Path] = None) -> bool:
    """Return True if no valid saved browser session exists."""
    if session_path is None:
        session_path = default_session_path()
    return not Path(session_path).exists()


@dataclass
class Session:
    """A logged-in Rustwright browser session."""

    page: object
    context: object
    browser: object
    playwright: object
    username: Optional[str] = None
    session_path: Optional[Path] = None

    def close(self) -> None:
        """Save storage state and close the browser."""
        if self.context and self.session_path:
            try:
                state = self.context.storage_state()
                self.session_path.parent.mkdir(parents=True, exist_ok=True)
                self.session_path.write_text(json.dumps(state, indent=2, default=str))
            except Exception as exc:
                print(f"  warning: could not save session: {exc}", flush=True)

        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass

        try:
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass


def _import_rustwright():
    """Import Rustwright lazily so the module can load without it installed."""
    try:
        from rustwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "rustwright is not installed. Run `uv pip install rustwright`"
        ) from exc


def _fetch_page(page, url: str, timeout_ms: int = 30000) -> dict:
    """Fetch a URL through a Rustwright page and return {ok, status, body, url, error}."""
    return page.evaluate(
        """
        async ([url, timeout_ms]) => {
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), timeout_ms);
            try {
                const res = await fetch(url, {
                    signal: controller.signal,
                    headers: {
                        'Accept': 'application/json',
                        'User-Agent': navigator.userAgent,
                    },
                    credentials: 'include',
                });
                const text = await res.text();
                return {ok: res.ok, status: res.status, body: text, url: res.url};
            } catch (err) {
                return {ok: false, error: err.toString()};
            } finally {
                clearTimeout(timer);
            }
        }
        """,
        [url, timeout_ms],
    )


def is_logged_in(page, timeout_ms: int = 10000) -> Optional[dict]:
    """Return the Reddit /api/me.json payload if the page is logged in, else None."""
    try:
        result = _fetch_page(page, f"{PUBLIC_BASE}/api/me.json", timeout_ms=timeout_ms)
        if not result.get("ok") and result.get("status") not in (401, 403):
            return None
        body = result.get("body", "{}")
        data = json.loads(body)
        # Anonymous responses contain loid + data.features; logged-in responses
        # contain data.name.
        me = data.get("data", data)
        if me.get("name"):
            return me
        return None
    except Exception:
        return None


def fetch_json(page, base: str, path: str, params: Optional[dict] = None, timeout_ms: int = 30000):
    """Fetch a Reddit JSON endpoint through the browser and return parsed JSON."""
    query = urllib.parse.urlencode(params or {})
    url = f"{base}{path}?{query}" if query else f"{base}{path}"
    result = page.evaluate(
        """
        async ([url, timeout_ms]) => {
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), timeout_ms);
            try {
                const res = await fetch(url, {
                    signal: controller.signal,
                    headers: {
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'User-Agent': navigator.userAgent,
                    },
                    credentials: 'include',
                });
                const text = await res.text();
                return {ok: res.ok, status: res.status, body: text, url: res.url};
            } catch (err) {
                return {ok: false, error: err.toString()};
            } finally {
                clearTimeout(timer);
            }
        }
        """,
        [url, timeout_ms],
    )
    if not result.get("ok"):
        snippet = result.get("body", result.get("error", "unknown"))[:300]
        raise RuntimeError(f"Reddit fetch failed: {url} -> {result.get('status')} {snippet}")
    return json.loads(result["body"])


def _launch_browser(sync_playwright, headless: bool = False, viewport: Optional[dict] = None):
    if viewport is None:
        viewport = {"width": 1280, "height": 800}

    p = sync_playwright().start()
    try:
        browser = p.chromium.launch(headless=headless)
    except Exception as exc:
        try:
            p.stop()
        except Exception:
            pass
        raise RuntimeError(f"Could not open browser: {exc}") from exc

    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    return Session(page=page, context=context, browser=browser, playwright=p)


def login(
    timeout: int = 300,
    headless: bool = False,
    session_path: Optional[Path] = None,
    viewport: Optional[dict] = None,
) -> Session:
    """Open a Rustwright browser on reddit.com and wait for the user to log in.

    A non-headless window is shown by default. The function polls
    ``/api/v1/me`` until a real user is detected, then saves the browser
    storage state to ``session_path`` for reuse.
    """
    sync_playwright = _import_rustwright()
    if session_path is None:
        session_path = default_session_path()
    session_path = Path(session_path)

    session = _launch_browser(sync_playwright, headless=headless, viewport=viewport)
    session.session_path = session_path

    try:
        session.page.goto(PUBLIC_BASE, wait_until="load", timeout=20000)
    except Exception as exc:
        print(f"  reddit home load warning: {exc}", flush=True)

    # Give Reddit's SPA a moment to settle before probing the login state.
    time.sleep(1)

    print("A Reddit window is open. Please log in and wait...", flush=True)

    username = None
    me_data = None
    attempts = int(timeout / 2.5)
    for i in range(attempts):
        try:
            me_data = is_logged_in(session.page, timeout_ms=5000)
            if me_data and me_data.get("name"):
                username = me_data["name"]
                print(f"  login detected as {username}", flush=True)
                break
            if i % 6 == 0:
                print(f"  waiting for login... current url: {session.page.url!r}", flush=True)
        except Exception as exc:
            if i % 6 == 0:
                print(f"  login check error: {exc}", flush=True)
        time.sleep(2.5)

    if not username:
        session.close()
        raise RuntimeError("Reddit login was not completed in time.")

    session.username = username
    return session


def new_context_from_session(
    session_path: Path,
    headless: bool = False,
    viewport: Optional[dict] = None,
) -> Session:
    """Create a new Rustwright context from a saved storage state."""
    sync_playwright = _import_rustwright()
    if viewport is None:
        viewport = {"width": 1280, "height": 800}

    session_path = Path(session_path)
    state = json.loads(session_path.read_text())

    p = sync_playwright().start()
    try:
        browser = p.chromium.launch(headless=headless)
    except Exception as exc:
        p.stop()
        raise RuntimeError(f"Could not open browser: {exc}") from exc

    context = browser.new_context(viewport=viewport, storage_state=state)
    page = context.new_page()
    return Session(page=page, context=context, browser=browser, playwright=p, session_path=session_path)


def ensure_authenticated_page(
    timeout: int = 300,
    headless: bool = False,
    session_path: Optional[Path] = None,
    viewport: Optional[dict] = None,
) -> Session:
    """Return a logged-in Rustwright page, reusing a saved session when valid."""
    if session_path is None:
        session_path = default_session_path()
    session_path = Path(session_path)

    if session_path.exists():
        try:
            session = new_context_from_session(session_path, headless=headless, viewport=viewport)
            session.page.goto(PUBLIC_BASE, wait_until="load", timeout=20000)
            time.sleep(1)
            me_data = is_logged_in(session.page, timeout_ms=10000)
            if me_data and me_data.get("name"):
                session.username = me_data["name"]
                print(f"  reusing saved session for {session.username}", flush=True)
                return session
            session.close()
            print("  saved session expired, logging in again", flush=True)
        except Exception as exc:
            print(f"  saved session invalid: {exc}", flush=True)

    return login(timeout=timeout, headless=headless, session_path=session_path, viewport=viewport)


def get_client(client_type: Optional[str] = None):
    """Return an authenticated client for the chosen strategy.

    Returns one of:
    - ``Session`` for the browser strategy.
    - ``requests.Session`` for bearer or public strategies.
    - ``praw.Reddit`` for the praw strategy.
    """
    if client_type is None:
        client_type = resolve_strategy()

    if client_type == "browser":
        return ensure_authenticated_page()

    if client_type == "bearer":
        token = bearer_token()
        if not token:
            raise RuntimeError("No bearer token could be parsed from REDDIT_CLIENT_SECRET")
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {token}",
            "User-Agent": user_agent(),
        })
        return session

    if client_type == "praw":
        try:
            from praw import Reddit
        except ImportError as exc:
            raise RuntimeError("praw not installed") from exc
        kwargs = {
            "client_id": client_id(),
            "client_secret": client_secret(),
            "user_agent": user_agent(),
        }
        uname = username()
        pwd = password()
        if uname and pwd:
            kwargs["username"] = uname
            kwargs["password"] = pwd
        return Reddit(**kwargs)

    # public
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent()})
    return session


def preflight() -> dict:
    """Run auth preflight checks and return a structured result."""
    _load_dotenv()
    env_ok, problems = credential_hygiene()
    deps_ok = True
    missing_deps = []
    try:
        importlib.import_module("rustwright.sync_api")
    except ImportError:
        deps_ok = False
        missing_deps.append("rustwright")
    try:
        importlib.import_module("dotenv")
    except ImportError:
        deps_ok = False
        missing_deps.append("python-dotenv")
    try:
        importlib.import_module("requests")
    except ImportError:
        deps_ok = False
        missing_deps.append("requests")

    reddit_ok, reddit_message = validate_credentials() if (env_ok and deps_ok) else (False, "fix dependencies and credentials first")

    result = {
        "env_ok": env_ok,
        "deps_ok": deps_ok,
        "reddit_ok": reddit_ok,
    }
    if not env_ok:
        result["credential_hygiene"] = problems
    if not deps_ok:
        result["missing_deps"] = missing_deps
    if not reddit_ok:
        result["reddit_error"] = reddit_message
    return result
