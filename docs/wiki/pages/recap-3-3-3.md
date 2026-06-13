# Recap 3-3-3

Quand on a beaucoup d'objectifs, de skills et de tâches, on se perd dans les détails et on oublie ce qui compte vraiment pour la journée. Le panneau Recap 3-3-3 règle ce problème : il condense tes 3 grandes priorités du moment en un seul coup d'œil, affiché **au-dessus de la feuille de personnage** sur la page d'accueil du dashboard.

## Ce que le panneau affiche

Le panneau contient trois sections fixes, chacune limitée à 3 items :

**3 objectifs majeurs** — 3 sous-étapes d'[objectifs](#/objectifs) que tu as épinglées. Ce sont les jalons concrets que tu veux garder sous les yeux, pas l'objectif global en entier.

**3 compétences clés** — 3 [softskills](#/softskills) que tu travailles en ce moment, choisies parmi celles non encore complétées dans l'arbre.

**3 activités d'allostasie** — tes activités de récupération du jour, tirées directement de la [Boutique de Récompenses](#/boutique-recompenses). Une flèche bascule entre la vue quotidienne (allostasie daily) et la vue hebdomadaire (allostasie weekly).

## Comment interagir

**Cliquer sur une sous-étape ou une compétence** bascule directement sur l'onglet correspondant (Objectifs ou Softskills), avec l'élément ciblé sélectionné et mis en valeur. Pas besoin de naviguer manuellement.

**Le crayon** (icône d'édition) à côté de chaque section ouvre un modal qui liste les items disponibles. Tu coches ceux que tu veux épingler (3 maximum), tu enregistres — le panneau se met à jour.

**Valider une allostasie** directement depuis le panneau a le même effet que la valider depuis la boutique : l'état passe en « Validé », les [stats](#/stats-xp-niveau-or) du jour se mettent à jour immédiatement, sans frais d'Or.

**La flèche de basculement** de la section allostasie switche entre les activités daily et weekly sans recharger la page.

## Mécanique de persistance

Les sélections épinglées (sous-étapes et softskills) sont sauvegardées en base de données. Elles persistent d'une session à l'autre. L'endpoint utilisé est `PUT /api/v1/profile/pins` ; le profil retourné par `GET /api/v1/profile` inclut les listes `pinned_substeps` (IDs de sous-étapes) et `pinned_softskills` (clés de softskills).

> [!note] Si un item épinglé est complété ou supprimé ailleurs, il apparaît automatiquement comme complété dans le recap (ou est ignoré) lors du prochain chargement.

## Cas limites

- Moins de 3 items configurés : le panneau affiche uniquement les items disponibles et propose un emplacement vide ou un raccourci de configuration.
- Allostasie : si l'utilisateur n'a créé que 1 ou 2 activités dans la boutique, seules celles-là s'affichent — pas d'erreur, pas de plantage.
- Changement de [template de jour](#/templates-de-jour) : la section allostasie reflète toujours l'état de validation de la journée en cours.
