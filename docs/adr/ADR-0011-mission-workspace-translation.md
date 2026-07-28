# ADR-0011 — Frontière entre l'atelier de mission et le contrat de rapport

## Statut

Accepté

## Date

2026-07-28

## Contexte

Deux mondes coexistent dans le dépôt sans se rencontrer.

`nouveau-rapport` crée un **atelier de mission** : une arborescence de travail, des
fichiers de rédaction, et un `metadata.yml` qui décrit la mission dans un vocabulaire
humain — `titre`, `auteur`, `classification` — plat et français.

Le moteur consomme une **source contractuelle** : un JSON dont la forme est décrite par
les `schema.json` des composants, dans un vocabulaire canonique et anglais — `report.title`,
`report.author`, `report.confidentiality` — imbriqué.

Aucun chemin ne relie les deux. En construire un pose une question que ni ADR-0009 ni
ADR-0010 ne tranchent : **où vit la correspondance entre ces deux vocabulaires ?**

Sans règle écrite, la réponse la plus courte s'imposera : ajouter `titre` comme alias
dans le contrat de C-001, « puisque la mission l'appelle ainsi ». Le contrat canonique
absorberait alors le vocabulaire de chaque atelier qui le rejoindrait — exactement
l'élargissement par accident qu'ADR-0010 existe pour empêcher.

## Décision

```
Atelier de mission          vocabulaire humain, propre à un outil
      │
      ▼
Traduction                  explicite, unidirectionnelle — le pont
      │
      ▼
Source contractuelle        vocabulaire canonique
      │
      ▼
Contrats de composants      ADR-0010
```

> La correspondance entre un vocabulaire d'atelier et le vocabulaire canonique vit
> **exclusivement dans le pont**. Ni le contrat, ni le moteur n'en connaissent
> l'existence.

Quatre règles en découlent.

**R1 — Aucun alias dans le contrat pour satisfaire un atelier.**
Un contrat ne gagne pas une clé parce qu'un outil amont la nomme autrement. Le contrat
décrit la forme canonique, et rien d'autre (ADR-0010).

**R2 — La traduction est unidirectionnelle.**
De l'atelier vers le contrat. Le pont ne réécrit jamais l'atelier depuis une source, et
ne s'utilise pas comme format d'échange bidirectionnel.

**R3 — Le pont traduit, il ne normalise pas.**
Les **clés** et la **forme** changent — `titre` devient `report.title`, une chaîne
`client` devient l'objet `client.name`. Les **valeurs** sont transportées telles quelles :
aucun reformatage de date, aucune casse modifiée, aucune valeur déduite, complétée ou
traduite. Le sens ne change pas en franchissant le pont.

**R4 — Une valeur absente ne s'écrit pas.**
Un champ vide de l'atelier produit une propriété absente, jamais une propriété vide.
Écrire `"id": ""` violerait le contrat de C-002, alors que l'omettre le satisfait :
l'absence s'exprime par l'absence.

## Portée

Cette ADR ne décrit pas un pont particulier, mais le rapport entre **tout** espace de
travail amont et le contrat canonique. Une interface graphique, une API, un import
depuis un autre format auront chacun leur vocabulaire et leur pont ; le contrat, lui,
reste unique et ignore combien de ponts le rejoignent.

C'est ce qui rend la règle utile au-delà du cas présent : elle empêche que le contrat
devienne l'union des vocabulaires de ses producteurs.

## Conséquences

Deviennent interdits, sans révision de cette ADR :

- ajouter à un `schema.json` une clé issue d'un vocabulaire d'atelier ;
- faire lire `metadata.yml`, ou tout autre artefact d'atelier, par le moteur ;
- déduire, compléter ou reformater une valeur pendant la traduction ;
- écrire une propriété vide plutôt que de l'omettre.

Restent ouverts :

- le nombre de ponts et leur technologie ;
- l'évolution du vocabulaire d'un atelier, qui ne concerne que son propre pont ;
- l'ajout de champs d'atelier sans contrepartie contractuelle — ils ne traversent
  simplement pas.

## Liens

- ADR-0010 — Forme canonique et tolérances : ce que le contrat décrit, et pourquoi il
  ne s'élargit pas par accident.
- ADR-0009 — Composition Pipeline : la frontière d'entrée, en aval de cette traduction.
