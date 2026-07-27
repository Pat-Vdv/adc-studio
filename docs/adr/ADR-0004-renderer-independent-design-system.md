# ADR-0004 — Design System indépendant du moteur de rendu

Statut : Accepted

## Contexte

ADC Studio doit produire des rapports Word et PDF cohérents sans dupliquer les
règles graphiques dans chaque format.

## Décision

Les couleurs, typographies, espacements et structures de composants sont
décrits dans des design tokens neutres. Les modèles Word et les exports PDF
consomment ces règles.

## Conséquences

- Word et PDF partagent une identité unique.
- Une évolution graphique peut être testée sur un spécimen avant d'être
  propagée.
- PowerPoint reste hors périmètre de la version 0.4.1.
