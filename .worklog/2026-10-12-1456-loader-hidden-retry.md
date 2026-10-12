# A betöltő újrapróbál rejtett keretben

A lap betöltője (az Artifact maga) a `page_code` hívást `retryable` hibánál
1 s múlva megismétli.

Ha a lap rejtett keretben indult (az app épp másik lapot mutatott), a hívás
azonnal elbukott, és a lap ezzel a hibával állt meg: „host:git-graph is not
available while this artifact is hidden”. Rejtve az időzítők is állnak, így az
újrapróba a megjelenéskor fut le. A betöltő változott, ezért új publikálás
kellett.

Nyitva maradt: a rejtve indított lap újrapróbáját nem idéztük elő, csak a normál
betöltés lett ellenőrizve.

- [`[69314ee0]`](https://github.com/GaborTorma/git-graph/commit/69314ee0671588f3266a0ab32cd41b92a091ca72) · fix(loader): retry loading the page code once the hidden frame is shown
