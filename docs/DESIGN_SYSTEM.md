# ADC Design System 0.4.1

Statut : candidate  
Périmètre : Word et PDF

## Objet

Cette spécification définit le langage graphique commun aux rapports A.D.C.
Elle est indépendante du document final et constitue la source de référence
pour les modèles Word et les exports PDF.

## Principes

1. La hiérarchie doit être visible en moins de trois secondes.
2. La couleur apporte du sens ; elle ne remplace jamais le texte.
3. Un rapport reste lisible imprimé en niveaux de gris.
4. Les composants ont une structure stable et un usage explicite.
5. Les rapports destinés aux clients privilégient la sobriété, la précision et la traçabilité.

## Palette

| Rôle | Couleur |
|---|---|
| Primary | `#17365D` |
| Accent | `#2F75B5` |
| Ink | `#1F2933` |
| Surface | `#F6F8FB` |
| Success | `#2E7D32` |
| Warning | `#B26A00` |
| Danger | `#B42318` |

## Typographie

- Display : Aptos Display
- Body : Aptos
- Monospace : Consolas
- Texte courant : 10,5 pt
- Titre 1 : 20 pt
- Titre 2 : 15 pt
- Titre 3 : 12 pt
- Légende : 8,5 pt
- Code : 9 pt

## Mise en page

- Format A4
- Marges : 2,0 cm haut ; 1,8 cm bas ; 2,2 cm gauche ; 1,8 cm droite
- En-tête discret, pied de page avec version et pagination
- Une page de couverture sans en-tête ni pied de page
- Pas de paragraphe justifié par défaut

## Composants

### Encadrés

- Information
- Validation
- Attention
- Critique
- Recommandation

Chaque encadré contient un libellé explicite, un texte bref et une couleur sémantique.

### Constats

Identifiant stable `F-001`, titre, observation, impact, preuve et conclusion.

### Recommandations

Identifiant stable `R-001`, priorité, effort, action proposée et résultat attendu.

### Tableaux

- Ligne d'en-tête bleu foncé, texte blanc
- Alternance de lignes très légère
- Pas de bordures verticales lourdes
- Unités dans les en-têtes lorsque pertinent

### Figures

Toute figure est accompagnée d'un numéro, d'un titre et d'une légende utile.
