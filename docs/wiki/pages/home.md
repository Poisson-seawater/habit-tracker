# Habit Tracker RPG

Un habit tracker auto-hébergé façon RPG, tournant en local sur un Raspberry Pi 5, piloté au choix par bot Telegram, skills LLM ou dashboard web. Il transforme la discipline quotidienne en jeu (XP, niveaux, or, quêtes, streaks, journées parfaites) pour un petit cercle qui se tient mutuellement responsable.

## Vue d'ensemble

<div class="mindmap-wrap"><svg class="markmap" data-mindmap="pages/_mindmap.md"></svg></div>
<p class="mindmap-hint">Carte interactive — clique un nœud pour ouvrir la page, molette pour zoomer. <a href="mindmap.html" target="_blank" rel="noopener">Ouvrir en plein écran ↗</a></p>

## Usage normal

*« Une app de suivi d'habitudes, d'accord. Mais concrètement, qu'est-ce que je fais de ma journée ? »*

Une petite boucle, toujours la même. Au fil de la journée, tu valides tes [habitudes](#/habitudes) au moment où tu les fais. Si elle est binaire : `/done <habitude>`. Si elle se mesure (30 min, 5 km) : `/log <habitude> <valeur>`. Tu coches aussi tes [primes](#/primes-todo), les tâches prévues pour aujourd'hui.

À l'inverse, tu as peut-être des [No-Todo](#/no-todo) : des règles que tu t'engages à ne pas enfreindre. Si tu craques, tu le déclares avec `/fail`, et ça se voit dans ton bilan.

Chaque validation fait avancer ton [Perfect Day](#/perfect-day) : les habitudes planifiées doivent être validées ou skippées avec une raison. `/status` te dit à tout moment ce qui est fait, skippé ou encore restant.

Quand toutes les habitudes prévues sont traitées, c'est un Perfect Day. À la clé : +5 XP, et ta série continue. C'est la récompense de la journée.

Puis, à 21h30, la journée se fige. Le bot publie le bilan de la guilde dans le groupe.

Tes grands projets, eux, avancent en parallèle, sur leur propre écran. Chaque sous-étape d'[objectif](#/objectifs) que tu coches te rapporte de l'Or. Le quotidien entretient la régularité ; les objectifs marquent la vraie progression.

En parallèle, l'arbre de [softskills](#/softskills) suit ta progression personnelle : chaque compétence s'active quand ses prérequis sont validés. Et pour ne pas se perdre dans l'ensemble, le panneau [Recap 3-3-3](#/recap-3-3-3) condense tes 3 priorités du moment — objectifs, compétences, activités d'allostasie — directement sur la page d'accueil du dashboard.

Quand tu as accumulé suffisamment d'Or, tu peux te récompenser dans la [Boutique de Récompenses](#/boutique-recompenses), et y valider tes activités d'allostasie daily ou weekly.

## Nouvel usager

Convaincu ? Reste à configurer ton compte. Une page dédiée te prend par la main, étape par étape, avec un exemple concret du début à la fin. [Démarrer la mise en route guidée](#/onboarding).

## Cas particuliers

Deux inquiétudes reviennent toujours, et elles sont légitimes.

**« Mes amis vont voir tout ce que je note ? »** Tu n'as pas forcément envie que le groupe sache que ta to-do du jour, c'est « acheter un cadeau à ma blonde ». Pas de souci : une [habitude](#/habitudes) marquée privée (`is_private`) compte pour ton [Perfect Day](#/perfect-day), mais reste masquée du recap public — juste comptée dans un total. Et dès que tu as posté une fois dans le groupe, tu peux parler au bot en message privé.

**« Et un jour où c'est la catastrophe parce que je suis malade ? »** Tu ne vas pas casser ta série juste parce que ton corps a lâché. C'est à ça que servent les [templates de jour](#/templates-de-jour). Bascule en `rest` : la journée se juge avec un rythme de récupération. Et si c'est juste une habitude précise qui saute, `/skip <habitude> raison: <texte>` l'excuse pour aujourd'hui sans casser ton streak. La raison est obligatoire — c'est un garde-fou honnête.

**« J'ai trop d'objectifs et de skills, je me perds. »** C'est exactement pour ça qu'existe le [Recap 3-3-3](#/recap-3-3-3) : tu épingles 3 sous-étapes d'objectifs, 3 softskills et tu vois tes 3 activités d'allostasie du jour. Un seul panneau, les vraies priorités, visible dès l'accueil.
