"""Gemeinsame Helfer: M3U parsen/schreiben, HTTP, Kanal-Identität."""
from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
DATA = ROOT / "data"
PLAYLISTS = ROOT / "playlists"
CONFIG = ROOT / "config" / "channels.yml"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

ATTR_RE = re.compile(r'([a-zA-Z0-9_-]+)="([^"]*)"')


def http(url, timeout=15, headers=None, max_bytes=None):
    """Minimales HTTP GET → (status, headers, body). 0 = Netzwerkfehler."""
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    req.add_header("Accept", "*/*")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    if max_bytes is not None:
        req.add_header("Range", f"bytes=0-{max_bytes - 1}")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
            body = r.read(max_bytes) if max_bytes is not None else r.read()
            return r.status, dict(r.headers), body
    except urllib.error.HTTPError as e:
        return e.code, {}, b""
    except Exception:
        return 0, {}, b""


def http_text(url, **kw):
    st, _, body = http(url, **kw)
    return st, body.decode("utf-8", "ignore")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "other"


def normalize_group(raw):
    """'IRIB National Networks | شبکه‌های …' → 'IRIB National Networks'"""
    return (raw or "").split(" | ")[0].strip() or "Other"


def parse_m3u(text):
    """→ Liste von {id,name,label,logo,group,language,quality,url}"""
    out, pending = [], None
    for raw in text.splitlines():
        line = raw.rstrip("\r").strip()
        if line.startswith("#EXTINF"):
            attrs = dict(ATTR_RE.findall(line))
            label = line.split(",", 1)[1].strip() if "," in line else ""
            pending = {
                "id": (attrs.get("tvg-id") or "").strip(),
                "name": (attrs.get("tvg-name") or label or "").strip(),
                "label": label,
                "logo": attrs.get("tvg-logo") or "",
                "group": normalize_group(attrs.get("group-title")),
                "language": attrs.get("tvg-language") or "",
                "quality": attrs.get("tvg-quality") or "",
            }
        elif line and not line.startswith("#") and pending:
            pending["url"] = line
            if not pending["id"]:
                pending["id"] = slug(pending["name"])
            out.append(pending)
            pending = None
    return out


def esc(s):
    return (s or "").replace('"', "'")


def write_m3u(channels, path, title=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["#EXTM3U"]
    if title:
        lines.append(f"# {title}")
    for c in channels:
        attrs = [
            f'tvg-id="{esc(c.get("id", ""))}"',
            f'tvg-name="{esc(c.get("name", ""))}"',
        ]
        if c.get("logo"):
            attrs.append(f'tvg-logo="{esc(c["logo"])}"')
        attrs.append(f'group-title="{esc(c.get("group", ""))}"')
        if c.get("language"):
            attrs.append(f'tvg-language="{c["language"]}"')
        if c.get("quality"):
            attrs.append(f'tvg-quality="{c["quality"]}"')
        label = c.get("label") or c.get("name") or ""
        lines.append("#EXTINF:-1 " + " ".join(attrs) + "," + label)
        lines.append(c["url"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(channels)


def load_config():
    import yaml

    with open(CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def matches(pattern, *values):
    import fnmatch

    pat = (pattern or "").lower()
    return any(fnmatch.fnmatch((v or "").lower(), pat) for v in values)


def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
