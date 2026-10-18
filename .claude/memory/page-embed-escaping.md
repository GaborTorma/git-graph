---
name: page-embed-escaping
description: Ami a lapra kerül, az embed()-en megy át — egy commit-üzenet </script>-je egyszer lezárta a script blokkot; a <meta charset="utf-8"> az első sor
metadata:
  type: project
---

- A beágyazott JSON lezárhatja a script blokkot: egy commit-üzenetben tényleg előfordult `</script>`
  (varazskez repó) → a lap fele nyers JSON-ként ömlött ki. Ezért a `build()` az `embed()`-en át ágyaz
  (`</` → `<\/`, U+2028/29 escape).
- `<meta charset="utf-8">` a fájl legelső sora: enélkül `file://`-ról vagy a helyi `http.server`-ről
  latin-1-ként olvasódik („beĂĄllĂ­tĂĄs”); a böngésző az első 1024 bájtban keresi.

**Why:** a lapra idegen repók szövege kerül.

**How to apply:** minden szöveg, ami a betöltőbe vagy a lapra kerül, az `embed()`-en át.
