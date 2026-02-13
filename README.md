# TXT-Parser

Desktop GUI tool (PyQt6) voor deterministische parsing van `Numeral Display & Input[NUMxxxx` blokken in `.txt` en `.rtf` bestanden.

## Features

- Exacte split op `Numeral Display & Input[NUM`
- Ondersteunt directe inlees van `.rtf` (RTF wordt naar platte tekst geconverteerd)
- Normaliseert literal escaped newlines (`\n`) wanneer deze in geconverteerde tekst voorkomen
- Section-aware extractie (voorkeur voor relevante secties zoals `General` en `Input Max/Min`)
- RTF decode via `striprtf` indien beschikbaar, met ingebouwde fallback parser
- Extractie van vaste regels met `startswith` matching
- Diagnostics: aantal blokken, numerieke sortering, missende nummers, dubbele Address-regels
- Address lookup met classificatie:
  - gevonden binnen NUM-blok
  - gevonden buiten NUM-blok
  - niet gevonden in bestand
- Markdown export met exact gespecificeerde kolommen
- Clipboard copy

## Run

```bash
python main.py
```

## Tests

```bash
python -m unittest discover -s tests -v
```


## PR zichtbaar maken (troubleshooting)

Als je een PR niet ziet na een commit vanuit Codex, controleer:

```bash
git branch -vv
git remote -v
git log --oneline -n 5
```

Push daarna expliciet de branch waarop de commit staat:

```bash
git push -u origin work
```

Maak vervolgens de PR vanaf `work` naar je doelbranch (bijv. `main`).
