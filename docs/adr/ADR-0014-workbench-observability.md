# ADR-0014 — Gouvernance de l'observabilité du Workbench

## Statut

Accepté

## Date

2026-08-03

## Contexte

Le Workbench observe toute la chaîne documentaire sur un seul écran. Un tel outil dérive
naturellement vers une seconde implémentation du moteur : il lui suffit d'analyser un
message, de recalculer un ordre ou de compléter une information manquante pour devenir une
couche métier que rien ne gouverne.

Le risque n'est pas théorique. Les diagnostics de composition sont aujourd'hui des chaînes
libres, et aucune couche ne déclare de gravité : les deux invitent l'interface à reconstruire
ce que le moteur n'expose pas. C'est exactement l'élargissement par accident qu'ADR-0010 et
ADR-0011 existent pour empêcher, transposé à l'outillage.

## Décision

> Le Workbench est une **projection en lecture seule de faits produits par leurs couches
> propriétaires**. Il peut lire, sélectionner, filtrer, rechercher et présenter ; il ne
> valide, ne résout, ne déduit et ne reconstitue aucune décision.

Cinq invariants, normatifs.

**W1 — Lecture seule.**
Aucune mutation d'une mission, d'une source, d'un contrat, de l'IR ou d'un document. Le
Workbench n'écrit rien que l'observation elle-même n'ait explicitement demandé.

**W2 — Propriétaire unique.**
Toute information observée provient de la couche qui en est propriétaire (ADR-0012, G1).
Appeler la fonction propriétaire n'est jamais une duplication ; réimplémenter son verdict en
est toujours une.

**W3 — Pas de reconstruction.**
L'interface n'analyse aucun message destiné à un humain pour en recréer un code, un chemin,
une relation ou une provenance. Une information non structurée est présentée telle quelle,
et son absence de structure est visible.

**W4 — Instantané déterministe.**
Une passe d'observation produit un instantané autonome. L'interface n'en recalcule rien :
même source, même instantané, même écran.

**W5 — Observabilité avant exploitation métier.**
Une capacité nouvelle du moteur **destinée à devenir visible ou exploitable par une interface
métier** doit être observable dans le Workbench avant de l'être ailleurs.

Cette règle ne gouverne que ce qui a vocation à être vu. Un changement interne — refactor,
performance, correction sans effet observable — n'entre pas dans son périmètre : l'y
soumettre transformerait une garantie d'observabilité en péage arbitraire.

**W6 — Un instantané a la sensibilité de la mission observée.**
Un instantané porte le contenu du rapport d'un client. Il est donc, à tout instant, une
donnée de même nature que la mission dont il dérive.

La qualification ne dépend pas de sa durée de vie : un instantané en mémoire porte déjà ce
contenu, et la persistance ne fait qu'en allonger l'existence. Attendre qu'une commande
d'écriture existe pour poser la règle reviendrait à la poser trop tard.

Il s'ensuit, immédiatement : aucune télémétrie du contenu, aucun journal qui le reproduise,
aucun cache implicite, aucune copie vers le dépôt. Une persistance ultérieure sera une action
explicite, et devra préserver cette qualification.

## Portée

Cette ADR gouverne le **rapport** entre le Workbench et les couches qu'il observe. Elle ne
décrit aucune structure de données, aucun écran et aucune technologie.

En particulier, elle **ne fige ni la carte de rendu ni la forme des diagnostics
structurés**. Ce sont des contrats techniques, à concevoir quand un besoin réel les appellera
— W3 impose seulement qu'aucune interface ne compense leur absence en analysant du texte.

## Conséquences

Deviennent interdits, sans révision de cette ADR :

- analyser un message humain pour en extraire un code, un chemin ou une relation ;
- afficher une information qu'aucune couche ne produit — une gravité, un niveau, un
  vocabulaire inventés par l'interface ;
- recalculer dans l'interface un ordre, une présence, une cardinalité ou une résolution ;
- traduire une valeur canonique de l'IR : le français appartient au renderer (ADR-0009, I5) ;
- faire écrire au Workbench autre chose que ce qu'une commande explicite lui demande ;
- journaliser, mettre en cache, transmettre ou copier dans le dépôt le contenu d'un
  instantané.

Restent ouverts :

- la structure de la carte de rendu et celle des diagnostics de composition ;
- la technologie de l'interface, et jusqu'à son existence : un instantané inspectable vaut
  déjà observation ;
- la persistance des instantanés, leur comparaison, et les conventions qui en découleraient.

## Vérification

W1 à W3 sont vérifiables par un test d'architecture, sur le modèle de
`test_the_contracts_are_consumed_at_the_boundary_only` : le Workbench n'écrit pas, n'appelle
aucun validateur de schéma, ne code en dur aucun nom de nœud de la source, et n'importe
aucun vocabulaire de présentation.

W4 se vérifie par l'instantané lui-même : produit deux fois sur la même source, il est
identique.

W5 ne se vérifie pas par un test — c'est une règle de conduite, et elle est rappelée ici pour
que son contournement soit un choix visible plutôt qu'un oubli.

## Liens

- ADR-0012 — Gouvernance du contrat narratif : G1, dont W2 est l'application à l'outillage.
- ADR-0009 — Composition Pipeline : I5, que W3 et les conséquences reprennent.
- `docs/studies/workbench-audit.md` — l'audit qui fonde ces invariants, et les écarts qu'il
  recense.
