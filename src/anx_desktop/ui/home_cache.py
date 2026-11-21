"""Persistent first-page snapshots of the public home catalog."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import asdict
from pathlib import Path

from .data import Page, Release

# home_0 may contain recommendations; unknown/custom tabs are not public.
PUBLIC_TABS = frozenset(f"home_{index}" for index in range(1, 9))


class HomeCache:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self, tab: str, page_size: int) -> Page[Release] | None:
        if tab not in PUBLIC_TABS or not self.path.is_file():
            return None
        try:
            with closing(sqlite3.connect(self.path, timeout=0.02)) as db:
                row = db.execute(
                    "SELECT payload FROM home_pages_v1 WHERE tab = ? AND page_size = ?",
                    (tab, page_size),
                ).fetchone()
            if row is None:
                return None
            payload = json.loads(row[0])
            items = []
            for item in payload["items"]:
                for field in ("genres", "screenshots", "votes"):
                    item[field] = tuple(item[field])
                item.update(is_favorite=False, list_status=0)
                items.append(Release(**item))
            count = payload["total_count"]
            pages = payload["total_pages"]
            if not items or type(count) is not int or type(pages) is not int:
                return None
            return Page(tuple(items), 1, page_size, count, pages)
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError):
            return None

    def store(self, tab: str, page: Page[Release]) -> None:
        # The current repository also returns an empty page on transport errors.
        if tab not in PUBLIC_TABS or page.page != 1 or not page.items:
            return
        try:
            items = []
            for release in page.items:
                item = asdict(release)
                del item["is_favorite"], item["list_status"]
                items.append(item)
            payload = json.dumps(
                dict(items=items, total_count=page.total_count, total_pages=page.total_pages),
                ensure_ascii=False,
            )
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(self.path, timeout=0.02)) as db, db:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS home_pages_v1 (
                        tab TEXT NOT NULL,
                        page_size INTEGER NOT NULL,
                        payload TEXT NOT NULL,
                        PRIMARY KEY (tab, page_size)
                    )
                """)
                db.execute(
                    "INSERT OR REPLACE INTO home_pages_v1 VALUES (?, ?, ?)",
                    (tab, page.page_size, payload),
                )
        except (OSError, sqlite3.Error, ValueError, TypeError):
            # A read-only, busy or corrupt cache must not block live results.
            pass
