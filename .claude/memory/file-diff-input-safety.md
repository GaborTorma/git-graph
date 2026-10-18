---
name: file-diff-input-safety
description: A file_diff bemenete a lapról jön — a sha csak hex, fájlt közvetlenül csak követetlen esetben olvasunk, különben git-opció vagy tetszőleges fájl menne át
metadata:
  type: project
---

- A `sha` csak hex lehet: különben `--output=…`-szerű opcióként menne a gitnek.
- Fájlt közvetlenül csak akkor olvasunk, ha a git követetlennek mondja — a lapon át ne legyen
  kiolvasható tetszőleges fájl.

**Why:** a host-híd hívásait a lap indítja, a szerver viszont a gép fájlrendszerét éri el.

**How to apply:** minden új, lapról jövő tool-paramétert validálj (formátum, a repóhoz kötés), mielőtt
git-parancsba vagy fájlútba kerül.
