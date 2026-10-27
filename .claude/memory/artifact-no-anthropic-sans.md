---
name: artifact-no-anthropic-sans
description: Az Artifact keretében nincs Anthropic Sans / Mono — a CSS-ben első hiába; a lap a vendorolt woff2-ket FontFace-ként tölti
metadata:
  type: project
---

Mérve 2026-10-26-án: a lap `--font-ui`-ja elsőként az „Anthropic Sans”-t kéri, a keretben mégis
a rendszerfont (SF Pro) rajzolt. A Fejlesztő képernyőképén a sorok szélessége tizedpixelre a
rendszerfonté volt (`fix(gitio): eltűnt git bináris után újrakeresés` 14 px-en: 276,1 px; az
Anthropic Sans-szal 284,4 px). Az app gyorsítótárában van egy `/_runtime/AnthropicSans-Roman-
Variable-*.woff2` az Artifact-futtatókörnyezettől, de a sima HTML Artifactra nem hat.

Következmény: a CDS köztes vastagságai (pl. a Badge `font-weight: 540`) rendszerfonton a
következő létező vastagságra, 600-ra esnek, félkövérnek hatnak.

**Why:** a lap az app betűjével akar megjelenni; a CSP külső fontot nem enged (`data:` sem).

**How to apply:** a fontok a `page_code`-on át jönnek (`part: "font"`, `"font-mono"`, base64), a lap
`new FontFace(név, ArrayBuffer)`-rel regisztrálja (`page/js/font.js`) — ez nem fetch. A monó is az
app fontja (Anthropic Mono): rendszerfonton (SF Mono) a 360-as törzsvastagság a Light vágásra esne.
Ha betűfüggő mérés kell, a szélesség-összevetés (canvas `measureText`) dönti el, melyik font
rajzol; a `document.fonts.check()` erre nem jó. Kapcsolódó: [[artifact-csp]].
