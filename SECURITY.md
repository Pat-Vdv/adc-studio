# Politique de sécurité et de confidentialité

## Données interdites dans ce dépôt

Ne jamais ajouter :

- noms de clients réels ;
- adresses e-mail ou coordonnées personnelles ;
- numéros de TVA, comptes bancaires ou identifiants ;
- noms de serveurs, domaines, adresses IP ou topologies réelles ;
- captures d’écran de production ;
- journaux techniques réels ;
- mots de passe, tokens, secrets, certificats ou clés privées ;
- rapports d’intervention clients ;
- exports de bases de données ;
- sauvegardes ou archives de production.

## Exemples et démonstrations

Tous les exemples doivent être :

- fictifs ;
- anonymisés ;
- nettoyés de toute donnée opérationnelle ;
- contrôlés avant commit.

## Réaction en cas de fuite

Si une donnée sensible est ajoutée par erreur :

1. arrêter immédiatement tout partage ;
2. supprimer la donnée de l’historique Git ;
3. révoquer les secrets exposés ;
4. effectuer une revue complète du dépôt ;
5. documenter l’incident.
