# Plan de Tâches — RPG Multi-User V2 📋🎯

Ce document répertorie les tâches à accomplir pour implémenter la **V2** selon l'approche Spec Kit.

---

## 📅 Phase 1 : Base de Données & Seeding (Priorité : P1)

- [ ] T001 [P] Créer le script de migration SQL `backend/src/database/migrations/v2_migration.sql` pour ajouter `xp`, `level` et les tables de liaison.
- [ ] T002 Modifier les modèles SQLAlchemy `User`, `UnlockedSkill`, et `UnlockedBadge` dans `backend/src/database/models.py`.
- [ ] T003 [P] Mettre à jour le script de peuplement `backend/src/database/seed.py` pour supporter de nouveaux utilisateurs de test.

---

## 🤖 Phase 2 : Bot Telegram Multi-User (Priorité : P1)

- [ ] T004 Créer des tests unitaires de routage multi-utilisateurs dans `backend/tests/test_bot_multiuser.py`.
- [ ] T005 Modifier le listener `backend/src/bot/listener.py` pour enregistrer automatiquement les utilisateurs inconnus écrivant au bot.
- [ ] T006 Adapter le planificateur de recap `backend/src/bot/scheduler.py` pour générer un recap de groupe listant les accomplissements de chaque aventurier.

---

## 🔮 Phase 3 : Moteur RPG & Compétences (Priorité : P2)

- [ ] T007 [P] Créer les tests unitaires du moteur de calcul d'XP et de niveau dans `backend/tests/test_rpg_engine.py`.
- [ ] T008 [P] Implémenter le service de calcul d'XP et d'attribution des Points de Talents lors des gains de stats dans `backend/src/services/score_service.py`.
- [ ] T009 Créer l'endpoint REST `POST /api/v1/skills/unlock` pour consommer un point de talent et débloquer une compétence.

---

- [ ] T010 [P] Intégrer la barre de progression d'XP dorée et le compteur de points de talent sous l'avatar dans `frontend/index.html`.
- [ ] T011 [P] Implémenter les écouteurs de clics JS dans `frontend/js/app.js` pour permettre le déblocage dynamique des compétences de l'arbre.
- [ ] T012 Rendre interactifs les tooltips des badges débloqués fièrement sur le dashboard.

---

## 📜 Phase 5 : Planification Hebdomadaire & Tableau de Primes (Priorité : P2)

- [ ] T013 Modifier le formulaire "Nouvelle Quête" dans `index.html` pour inclure 7 boutons/badges stylisés de planification de jours spécifiques.
- [ ] T014 [P] Créer la table SQLite `todos` et déclarer son modèle SQLAlchemy `Todo` dans le backend.
- [ ] T015 [P] Intégrer le widget "Grimoire du Jour Parfait" dans le dashboard pour afficher en clair la progression vers le statut Parfait.
- [ ] T016 Implémenter les routes REST `GET /api/v1/todos` et `POST /api/v1/todos/{id}/complete` pour lister et clore les primes (Todos).

