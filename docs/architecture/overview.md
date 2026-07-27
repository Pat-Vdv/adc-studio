# Architecture du dépôt

## Séparation des responsabilités

ADC Studio contient uniquement les éléments génériques :

- identité ;
- composants ;
- modèles ;
- scripts ;
- documentation ;
- exemples fictifs.

Les données clients restent hors dépôt.

## Répertoire local recommandé

```text
D:\Projets\
├── ADC-Studio\
└── ADC-Clients\
```

## Cycle de production

1. conception des composants dans ADC Studio ;
2. versionnement et validation ;
3. génération d’un livrable ;
4. copie du livrable dans le dossier client local ;
5. aucun retour automatique du livrable client vers Git.
