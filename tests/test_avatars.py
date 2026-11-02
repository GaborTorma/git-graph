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

    def test_transient_error_keeps_image(self) -> None:
        """Átmeneti letöltési hiba (`OSError`, `ValueError`) a meglévő képet nem törli: a kép
        marad, az újrapróba `AVATAR_RETRY` múlva jön, nem a heti `AVATAR_TTL` után."""
        gg = self.load()
        # Adott: egy lejárt, de jó kép, és egy kép nélküli, lejárt bejegyzés
        old = time.time() - gg.avatars.AVATAR_TTL - 60
        img = "data:image/png;base64,AAAA"
        self.write_cache({"a@x.hu": {"img": img, "at": old},
                          "b@x.hu": {"img": None, "at": old}})
        errors = iter([OSError("offline"), ValueError("rossz JSON")])

        def failing_fetch(owner_repo: str, email: str, sha: str) -> str | None:
            raise next(errors)

        gg.avatars.fetch_avatar = failing_fetch
        commits = [{"sha": "1" * 40, "email": "a@x.hu", "pushed": True},
                   {"sha": "2" * 40, "email": "b@x.hu", "pushed": True}]
        # Ha a frissítés közben a letöltés elbukik
        self.assertEqual(gg.avatars.avatars_for(commits, "https://github.com/o/r"), {"a@x.hu": img})
        deadline = time.monotonic() + 5
        while gg.avatars._AVATAR_JOBS and time.monotonic() < deadline:
            time.sleep(0.02)
        # Akkor a kép megmarad, a kép nélküli bejegyzés None marad
        cache = json.loads((self.state / "avatars.json").read_text(encoding="utf-8"))
        self.assertEqual(cache["a@x.hu"]["img"], img)
        self.assertIsNone(cache["b@x.hu"]["img"])
        self.assertEqual(gg.avatars.avatars_for(commits, "https://github.com/o/r"), {"a@x.hu": img})
        self.assertEqual(gg.avatars._AVATAR_JOBS, set())                      # most nem próbál újra
        # És AVATAR_RETRY múlva újrapróbál
        later = time.time() + gg.avatars.AVATAR_RETRY + 60
        self.assertGreaterEqual(later - cache["a@x.hu"]["at"], gg.avatars.AVATAR_TTL)


class FetchAvatarTest(HomeTestCase):
    def test_big_commit(self) -> None:
        """A sok patchet hozó commit szerzőjének képe is megjön (a válasz nagyobb a képlimitnél)."""
        # Adott a GitHub: a commit adata 80 KB (a fájlok patchével), a kép kicsi
        gg = self.load()
        author = {"avatar_url": "https://avatars.githubusercontent.com/u/1?v=4"}
        big = json.dumps({"author": author, "files": [{"patch": "x" * 80_000}]}).encode()
        pages = {"https://api.github.com/repos/o/r/commits/" + "a" * 40: big,
                 "https://api.github.com/repos/o/r/commits?sha=" + "a" * 40 + "&per_page=1": json.dumps(
                     [{"author": author}]).encode(),
                 "https://avatars.githubusercontent.com/u/1?v=4&s=44": b"\x89PNG kep"}

        class Resp:
            def __init__(self, url: str) -> None:
                self.body = pages[url]
                self.headers = type("H", (), {"get_content_type": lambda _s: "image/png" if "avatars" in url
                                              else "application/json"})()

            def read(self, n: int = -1) -> bytes:
                return self.body if n < 0 else self.body[:n]

            def __enter__(self):
                return self

            def __exit__(self, *_: object) -> None:
                return None

        real = gg.avatars.urllib.request.urlopen
        self.addCleanup(setattr, gg.avatars.urllib.request, "urlopen", real)
        gg.avatars.urllib.request.urlopen = lambda req, timeout=0: Resp(req.full_url)
        # Ha a lap a szerző képét kéri
        img = gg.avatars.fetch_avatar("o/r", "a@x.hu", "a" * 40)
        # Akkor a kép data URI-ként jön
        self.assertEqual(img, "data:image/png;base64,iVBORyBrZXA=")
