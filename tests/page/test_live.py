"""Az élő frissítés hibatűrése: a nyitva tartott `changes` hívás hibája után."""
from __future__ import annotations

from harness import PageTestCase


class TransientErrorTest(PageTestCase):
    """A nyitva tartott `changes` egyszer nem `retryable` hibával bukik (`upstream_error`: a gép
    alvása alatt lejárt hívás, az app közben újraindítja a szervert), utána a szerver válaszol."""

    INIT = """
    const use = window.claude.use;
    let n = 0;
    window.claude.use = async name => { const mcp = await use(name); return mcp && { callTool: (s, tool, args, opts) => {
      if (tool !== 'changes' || !(args.wait > 0)) return mcp.callTool(s, tool, args, opts);
      n += 1;
      if (n === 1) return Promise.reject(Object.assign(new Error('nincs'), { code: 'upstream_error', retryable: false }));
      if (n === 2) return mcp.callTool(s, tool, { ...args, wait: 0 }, opts);
      return mcp.callTool(s, tool, args, opts);
    } }; };"""

    def test_recovers(self) -> None:
        """A lábléc kiírja a hibát, de a lap újrapróbál, és visszaáll élőre."""
        # Adott: a hiba a láblécben
        self.page.wait_for_selector(".foot.stale")
        # Akkor: a következő kör sikerül, a lap újra élő
        self.page.wait_for_selector(".foot.on", timeout=10_000)
