# Authentification & appareils

Tu connais le principe d'un mot de passe pour te connecter à un site. Ici, il y a **trois couches** empilées avant d'accéder au dashboard, parce que le Pi tourne exposé sur Internet pour que le groupe y accède de n'importe où.

## Les trois couches

```mermaid
flowchart TD
  A["Cloudflare Access\n(email autorisé)"] --> B["Mot de passe applicatif\n(par utilisateur)"]
  B --> C["Cookie d'appareil\n(habit_device, par origine)"]
  C --> D["Dashboard / bot"]
```

1. **Cloudflare Access**, en amont du serveur : seules les adresses email autorisées passent, avant même d'atteindre l'application.
2. **Mot de passe applicatif** : chaque joueur a son propre mot de passe, vérifié par l'API.
3. **Cookie d'appareil** (`habit_device`) : posé par navigateur/origine, pas par machine physique — si tu ouvres le dashboard depuis deux navigateurs différents sur le même téléphone, ce sont deux appareils distincts pour le système.

## Auto-approbation des appareils (comportement actuel)

> [!note] Après le passage par Cloudflare Access, **tout nouvel appareil est auto-approuvé seulement après un mot de passe applicatif valide**. Un mauvais mot de passe ne crée jamais d'appareil approuvé.

L'approbation expire après `AUTH_DEVICE_DAYS` jours (90 par défaut). À l'expiration, ou depuis un nouveau navigateur, le dashboard affiche « Session expirée ou nouvel appareil. Reconnecte-toi. » et redemande le mot de passe. Une connexion réussie renouvelle l'approbation pour 90 jours. La liste des appareils reste visible dans Réglages → Sécurité & Appareils; un admin peut y révoquer manuellement un appareil et toutes ses sessions actives.

## Bootstrap : créer le premier mot de passe admin

Avant toute connexion, il faut un premier compte admin. `AUTH_BOOTSTRAP_CODE` (variable d'environnement) est un code temporaire à usage unique : `POST /auth/bootstrap` le vérifie, fixe le mot de passe du premier utilisateur choisi et le passe admin. Une fois `AUTH_BOOTSTRAP_CODE` consommé (un admin existe), la route refuse tout nouveau bootstrap.

## Endpoints principaux

| Endpoint | Rôle |
|---|---|
| `GET /auth/status` | état courant : authentifié ou non, bootstrap requis ou non, appareil connu |
| `POST /auth/bootstrap` | crée le premier admin avec `AUTH_BOOTSTRAP_CODE` |
| `POST /auth/devices/request` | enregistre l'appareil courant en attente, pour compatibilité |
| `POST /auth/login` | vérifie utilisateur + mot de passe, approuve l'appareil et ouvre une session |
| `POST /auth/logout` | révoque la session courante |
| `GET /auth/users` | liste des joueurs (appareil approuvé requis) |
| `GET /auth/devices` | liste des appareils connus (admin) |
| `POST /auth/devices/{id}/approve` / `/revoke` | approbation API et révocation disponible dans le dashboard admin |
| `POST /auth/password` | change son propre mot de passe |
| `POST /auth/users/{id}/password` | un admin change le mot de passe d'un autre joueur |

## Sessions

Une session vit `AUTH_SESSION_DAYS` jours (90 par défaut). Le cookie d'appareil expire lui aussi après `AUTH_DEVICE_DAYS` jours (90 par défaut), et le serveur vérifie la même échéance à chaque requête. `AUTH_COOKIE_SECURE` doit rester à `true` uniquement si le site tourne en HTTPS — sinon le navigateur rejette le cookie.

## Accès machine (pas un navigateur)

Un agent ou un script qui appelle l'API directement — la [télécommande IA](#/telecommande-ia) par exemple — ne passe pas par le cookie d'appareil. Il envoie l'en-tête `Authorization: Bearer <HABIT_API_TOKEN>` : un jeton machine défini en variable d'environnement, séparé du mot de passe des joueurs. Le header `X-User-ID` reste nécessaire à côté pour dire **quel** joueur agit — `HABIT_API_TOKEN` prouve seulement que l'appelant a le droit d'appeler l'API sans navigateur.

## Mode legacy (sans authentification)

Si ni `AUTH_BOOTSTRAP_CODE` ni un compte admin ne sont configurés, le système tolère un mode non authentifié — pratique pour un usage strictement local (le Pi sur le réseau domestique, sans exposition Internet). Dès qu'un admin existe, ce mode legacy se ferme automatiquement.
