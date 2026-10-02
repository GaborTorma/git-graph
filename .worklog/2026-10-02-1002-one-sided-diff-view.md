# Egyoldalú diff side-by-side nélkül

Ha egy fájl diffjében csak hozzáadott vagy csak törölt sor van, a lenyitott
fájlsor most akkor is csak az egymás alatti nézetet mutatja, ha körülötte
változatlan sorok is vannak — széles Artifact-ablakban sem vált side-by-side-ra.

Eddig ez csak az új vagy egészében törölt fájlra teljesült (ott változatlan sor
sincs); egy egyszerű beszúrásnál a side-by-side bal oldala végig üres maradt, a
tartalom pedig a fél szélességbe szorult.

A döntés a teljes fájl diffjére szól, nem hunkonként: egy fájlon belül nem vált
nézetet a lap.

- [`[b5391a33]`](https://github.com/GaborTorma/git-graph/commit/b5391a33759037dbfd5a12af789c7f0fc60c57f7) · fix(ui): skip the side-by-side diff when a file only adds or only removes lines
