# ADC Studio

**ADC Studio** est un framework documentaire professionnel, versionné et composé de briques réutilisables.

## Points d’entrée

- [État du projet](PROJECT_STATUS.md)
- [Roadmap](ROADMAP.md)
- [Catalogue des composants](COMPONENT_CATALOG.md)
- [Cycle de vie des composants](docs/component_lifecycle.md)
- [ADR-0006 — Architecture par composants](docs/adr/ADR-0006-document-component-architecture.md)

## Version courante

- Version : `0.4.4`
- Sprint : `004.4`
- Statut : Bibliothèque de composants — fondations

## Structure

```text
ADC-Studio/
├── README.md
├── PROJECT_STATUS.md
├── ROADMAP.md
├── COMPONENT_CATALOG.md
├── CHANGELOG.md
├── VERSION
├── components/
├── templates/
├── examples/
├── brand/
└── docs/
```

## Principe

Un rapport ADC Studio est assemblé à partir de composants documentaires identifiés, versionnés, documentés et suivis selon un cycle de maturité commun.

Chaque sprint doit mettre à jour au minimum :

1. `PROJECT_STATUS.md` ;
2. le catalogue et les métadonnées des composants concernés ;
3. `CHANGELOG.md` ;
4. `VERSION` si la version évolue.
