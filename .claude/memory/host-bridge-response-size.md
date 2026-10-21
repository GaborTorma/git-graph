---
name: host-bridge-response-size
description: A host-híd egy tool-válasza 3 999 000 karakterig átmegy, 4 000 000-nál „The tool result is too large.” — ezért karcsú a Mermaid-build, és ezért ~2,8 MB a képlimit
metadata:
  type: project
---

Mérve 2026-10-15-én (contract 0.2.80), a `page_code` ideiglenes `part`-jaival, az appban:

| Válasz | Eredmény |
| --- | --- |
| 3 382 711 karakter | megy, 275 ms |
| 3 572 520 karakter | megy |
| 3 665 728 karakter (Mermaid 12.2.0 karcsú, ELK-kal) | megy, 290 ms |
| 5 082 864 karakter | `tool_error` — „The tool result is too large.” |

Pontosítva 2026-10-21-én (#54, ideiglenes `file_diff` próbával, `{"x": "a"*n}` válasz, az appban):
3 999 000 karakter megy, 4 000 000 `tool_error` — „The tool result is too large.” A határ
gyakorlatilag 4 000 000 karakter (a válasz teljes szövege), a hívás ~250 ms. A gépen a `page_code` 32–46 ms, a lapon
a hívás ~270 ms; az első hívásba az engedélykérés is beleszámít (~7 s). CSP-sértés egyik esetben sem
volt.

**Why:** a Mermaid 12.x hivatalos buildje 5,5 MB, nem fér át ([[mermaid-build]]).

**How to apply:** nagy `page_code` `part` vagy `graph_data` előtt nézd meg a méretet; a
`scripts/mermaid.sh` buildjének a mért határ alatt kell maradnia. A kép data URI-ja base64
(×4/3): oldalanként külön válaszban a nyers kép legfeljebb ~2,95 MB lehet (`IMAGE_MAX`); 3 MB
(4,19 M karakter) már nem fér át.
