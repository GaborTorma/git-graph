"""GitHub-avatarok (`avatars`): gyorstár, újrapróbálás, háttérletöltés."""
from __future__ import annotations

import json
import time

from helpers import HomeTestCase


class AvatarTest(HomeTestCase):
    def write_cache(self, data: dict) -> None:
        (self.state / "avatars.json").write_text(json.dumps(data), encoding="utf-8")

    def test_avatar_cache(self) -> None:
        """Gyorstárból jön a kép; friss bejegyzésre nem indul letöltés."""
        gg = self.load()
        now = time.time()
        self.write_cache({"a@x.hu": {"img": "data:image/png;base64,AAAA", "at": now},
                          "b@x.hu": {"img": None, "at": now}})
        commits = [{"sha": "1" * 40, "email": "a@x.hu", "pushed": True},
                   {"sha": "2" * 40, "email": "b@x.hu", "pushed": True}]
        found = gg.avatars.avatars_for(commits, "https://github.com/o/r")
        self.assertEqual(found, {"a@x.hu": "data:image/png;base64,AAAA"})
        self.assertEqual(gg.avatars._AVATAR_JOBS, set())
        self.assertEqual(gg.avatars.avatar_signal(), 1)
        self.assertEqual(gg.avatars.avatars_for(commits, ""), {})          # nem GitHub-os repó

    def test_fetch(self) -> None:
        """Lejárt vagy hiányzó bejegyzés: háttérben kéri (pusholt commit vagy noreply cím
        kell hozzá), és a gyorstárba írja; ami nem jött, `img: None`."""
        gg = self.load()
        old = time.time() - gg.avatars.AVATAR_RETRY - 60
        self.write_cache({"regi@x.hu": {"img": None, "at": old}})
        calls = []

        def fake_fetch(owner_repo: str, email: str, sha: str) -> str | None:
            calls.append((owner_repo, email, sha))
            return "data:image/png;base64,BBBB" if email.endswith("noreply.github.com") else None

        gg.avatars.fetch_avatar = fake_fetch
        commits = [{"sha": "1" * 40, "email": "regi@x.hu", "pushed": True},
                   {"sha": "2" * 40, "email": "42+nev@users.noreply.github.com"},
                   {"sha": "3" * 40, "email": "helyi@x.hu"}]                 # pusholatlan: nem kérjük
        self.assertEqual(gg.avatars.avatars_for(commits, "https://github.com/o/r"), {})
        deadline = time.monotonic() + 5
        while gg.avatars._AVATAR_JOBS and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertEqual({c[1] for c in calls}, {"regi@x.hu", "42+nev@users.noreply.github.com"})
        self.assertEqual(calls[0][0], "o/r")
        cache = json.loads((self.state / "avatars.json").read_text(encoding="utf-8"))
        self.assertIsNone(cache["regi@x.hu"]["img"])
        self.assertEqual(gg.avatars.avatars_for(commits, "https://github.com/o/r"),
                         {"42+nev@users.noreply.github.com": "data:image/png;base64,BBBB"})
