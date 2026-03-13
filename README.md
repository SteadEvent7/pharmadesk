# PharmaDesk

Application desktop de gestion de pharmacie developpee en Python avec Tkinter, basee sur le cahier des charges fourni.

## Fonctionnalites couvertes

- Authentification et gestion des roles administrateur, pharmacien, caissier
- Tableau de bord avec indicateurs et ventes recentes
- Gestion des medicaments: ajout, modification, suppression, recherche
- Gestion du stock: entrees, sorties, alertes stock faible, produits expires et a expiration proche
- Point de vente: panier, total automatique, facture textuelle, deduction du stock
- Gestion des fournisseurs
- Gestion des utilisateurs
- Rapports journaliers des ventes
- Sauvegarde locale SQLite
- Verification de mises a jour distante via manifest `update.json`
- Telechargement asynchrone de l'installateur et lancement eleve sous Windows
- Journalisation des operations d'update dans `data/logs/update.log`
- Service Node.js optionnel pour centraliser la verification et le telechargement des mises a jour

## Architecture

- `main.py`: point d'entree
- `app/config.py`: configuration de l'application et choix du moteur de base
- `app/db`: connexion et schema de base de donnees
- `app/services`: logique metier
- `app/ui`: interface Tkinter et vues
- `updater-service`: micro-service Node.js pour les mises a jour
- `scripts/build.ps1`: build Windows avec PyInstaller
- `installer.iss`: script Inno Setup

## Installation locale

### Prerequis

- Python 3.11+
- Windows 10/11
- Optionnel: MySQL Server si vous souhaitez le mode client-serveur
- Optionnel: Node.js 20+ pour le service de mise a jour

### Lancer l'application

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Compte initial:

- Utilisateur: `admin`
- Mot de passe: `admin123`

## Configuration de la base de donnees

Au premier lancement, un fichier `config.json` est genere automatiquement.

Exemple de configuration SQLite:

```json
{
  "db_engine": "sqlite",
  "sqlite_path": "data/pharmacy.db",
  "mysql_host": "127.0.0.1",
  "mysql_port": 3306,
  "mysql_user": "root",
  "mysql_password": "",
  "mysql_database": "pharmacy_db",
  "low_stock_threshold": 10,
  "github_owner": "SteadEvent7",
  "github_repo": "pharmadesk",
  "auto_check_updates": false,
  "update_manifest_url": "",
  "update_download_dir": "data/updates",
  "update_installer_args": "/CLOSEAPPLICATIONS /NORESTART"
}
```

Pour activer MySQL:

1. Installer `mysql-connector-python`
2. Modifier `db_engine` en `mysql`
3. Renseigner les parametres de connexion
4. Relancer l'application pour initialiser les tables

## Build et distribution

### Executable Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1
```

Le binaire est genere dans `dist/PharmaDesk/`.

### Installateur Windows

1. Installer Inno Setup
2. Generer l'executable PyInstaller
3. Ouvrir `installer.iss` dans Inno Setup
4. Compiler pour produire `dist/installer/PharmaDeskSetup.exe`

## Service de mise a jour

Le poste client utilise en priorite un manifest distant `update.json`. Vous pouvez soit:

1. renseigner `update_manifest_url` avec une URL HTTPS directe,
2. ou laisser ce champ vide et heberger `update.json` a la racine du depot GitHub cible pour que l'application le lise via `raw.githubusercontent.com`.

Le fichier publie dans ce projet est [update.json](update.json). Vous pouvez le pousser a la racine du depot GitHub puis utiliser l'URL brute GitHub comme manifest distant.

Exemple de manifest distant:

```json
{
  "version": "1.1.0",
  "patch": 2,
  "published_at": "2026-03-13T10:30:00Z",
  "installer_name": "PharmaDeskSetup-1.1.0.exe",
  "installer_url": "https://github.com/SteadEvent7/pharmadesk/releases/download/v1.1.0/PharmaDeskSetup.exe",
  "sha256": "facultatif_si_vous_voulez_controler_l_integrite",
  "notes": "- Correction des ventes\n- Nouvelle interface login\n- Ameliorations de stabilite"
}
```

Flux implemente:

1. Lecture du manifest distant au demarrage si l'option automatique est activee pour l'administrateur.
2. Comparaison entre `APP_VERSION` / `APP_PATCH` locaux et la version distante.
3. Notification non bloquante a l'administrateur.
4. Telechargement de l'installateur dans `data/updates/` sur thread separe.
5. Preparation du lancement eleve de l'installateur, puis fermeture de l'application.
6. Logs techniques dans `data/logs/update.log`.

```powershell
cd updater-service
npm install
copy .env.example .env
npm start
```

Endpoints:

- `GET /health`
- `GET /latest`
- `GET /manifest`
- `GET /download?assetUrl=...`

Le service Node est optionnel. Il reste utile si vous souhaitez proxyfier les telechargements GitHub ou exposer votre propre manifest derriere une API.

Exemple de configuration client pour consommer directement le service:

```json
{
  "update_manifest_url": "https://votre-domaine-ou-serveur:4010/manifest"
}
```

Le endpoint `GET /manifest` renvoie exactement le format attendu par l'application:

```json
{
  "version": "1.0.0",
  "patch": 0,
  "published_at": "2026-03-13T00:00:00Z",
  "installer_name": "PharmaDeskSetup.exe",
  "installer_url": "https://votre-serveur/telechargement-ou-github",
  "notes": "...",
  "sha256": ""
}
```

## Limites actuelles

- Impression facture fournie sous forme de fenetre texte, sans pilote d'impression physique
- Les graphiques avances ne sont pas integres
- Le mode multi-poste MySQL est prepare mais doit etre valide avec votre serveur cible

## Evolutions conseillees

- Journal d'audit des actions utilisateur
- Impression ticket thermique
- Export PDF et Excel
- Sauvegarde planifiee
- Tableau de bord graphique avec `matplotlib`