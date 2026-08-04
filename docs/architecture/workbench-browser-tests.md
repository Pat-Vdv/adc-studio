# Tests navigateur du Workbench

Une capture d'écran statique ne prouve rien d'une interaction. À partir de P4,
la navigation croisée du Workbench est vérifiée par de vrais clics dans
Chromium, et l'assertion porte sur **l'état exact du DOM** après chacun.

## Exécution

```bash
.venv/bin/python -m pytest tests/test_workbench_browser.py
```

Ces tests font partie de la suite : `python -m pytest` les exécute aussi.

## Dépendance et navigateur

Playwright est une dépendance **de développement** (`requirements-dev.txt`), au
même titre que pytest. Le Workbench lui-même n'a aucune dépendance d'exécution.

```bash
.venv/bin/pip install -r requirements-dev.txt
```

Le navigateur **du système** est réutilisé — `/usr/bin/chromium-browser` — et
aucun second navigateur n'est téléchargé :

```python
playwright.chromium.launch(executable_path="/usr/bin/chromium-browser")
```

Les tests sont **ignorés**, jamais en échec, lorsque Playwright ou ce navigateur
manquent : une machine sans navigateur doit pouvoir faire tourner la suite.

## Ce que ces tests prouvent

Chaque scénario exerce un clic, puis relève quels éléments portent la sélection
primaire et lesquels portent la mise en évidence liée, dans quels panneaux.

Les **assertions négatives** comptent autant que les positives, et ce sont elles
qui protègent la doctrine : lorsque l'instantané ne connaît pas une relation,
rien ne doit s'allumer ailleurs. Un diagnostic métier ne désigne aucun composant ;
un diagnostic de composition, qui n'est qu'une chaîne, ne désigne rien du tout ;
un artefact de mission ne rejoint pas la source.

Ces assertions ont été vérifiées comme réellement mordantes : en faisant deviner
à l'interface un composant pour un diagnostic métier, le scénario concerné
échoue. C'est la seule manière de savoir qu'un test négatif teste quelque chose.

## Captures

Les captures d'écran sont produites hors du dépôt — `~/.cache/adc-workbench-shots/`.
Un instantané a la sensibilité de la mission observée (ADR-0014, W6) ; une image
qui le montre aussi.
