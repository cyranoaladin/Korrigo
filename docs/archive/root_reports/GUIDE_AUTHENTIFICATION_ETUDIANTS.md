# 🔐 Guide d'Authentification Sécurisée des Étudiants

## 📋 Vue d'ensemble

Le système Korrigo utilise maintenant un système d'authentification sécurisé avec **mots de passe** pour les étudiants, garantissant la confidentialité et la sécurité des données.

---

## 🚀 Déploiement sur le Serveur

### Commandes à exécuter sur `root@moneyfactory-core`

```bash
# Se connecter au serveur
ssh root@moneyfactory-core

# Exécuter le script de déploiement
cd /var/www/labomaths/korrigo
git pull origin main
chmod +x deploy_student_auth.sh
./deploy_student_auth.sh
```

Le script effectuera automatiquement :
- Pull des modifications depuis GitHub
- Création des migrations de base de données
- Application des migrations
- Redémarrage du backend

---

## 📊 Import des Étudiants depuis CSV

### 1. Format du fichier CSV

Le fichier CSV doit contenir les colonnes suivantes :

**Colonnes obligatoires :**
- `FULL_NAME` (ou `ÉLÈVES`, `NOM ET PRÉNOM`) : Nom complet de l'étudiant
- `DATE_NAISSANCE` (ou `NÉ(E) LE`) : Date de naissance (format DD/MM/YYYY ou YYYY-MM-DD)
- `EMAIL` (ou `ADRESSE E-MAIL`) : **Adresse email unique** pour chaque étudiant

**Colonnes optionnelles :**
- `CLASSE` : Classe de l'étudiant (ex: T1, 1S2)
- `GROUPE_EDS` (ou `GROUPE`) : Groupe d'enseignement de spécialité

**Exemple de CSV :**
```csv
ÉLÈVES,NÉ(E) LE,ADRESSE E-MAIL,CLASSE,GROUPE
DUPONT Jean,15/03/2008,jean.dupont@ert.tn,T1,Maths-Physique
MARTIN Sophie,22/07/2008,sophie.martin@ert.tn,T1,SVT-Chimie
```

### 2. Processus d'import

1. **Connectez-vous** à l'interface admin : `https://korrigo.labomaths.tn/admin/`
2. **Allez** dans la section "Students" → "Import"
3. **Uploadez** votre fichier CSV
4. **Cliquez** sur "Importer"

### 3. Résultat de l'import

Le système retournera une réponse JSON contenant :

```json
{
  "created": 25,
  "updated": 0,
  "skipped": 0,
  "errors": [],
  "passwords": {
    "jean.dupont@ert.tn": "aB3xK9mP",
    "sophie.martin@ert.tn": "pL7qR2nW",
    ...
  },
  "message": "Import réussi. IMPORTANT: Sauvegardez les mots de passe générés et communiquez-les aux étudiants de manière sécurisée."
}
```

**⚠️ IMPORTANT :**
- **Sauvegardez immédiatement** le dictionnaire `passwords`
- Ces mots de passe ne seront **jamais affichés à nouveau**
- Les mots de passe sont générés aléatoirement (8 caractères : lettres + chiffres)

---

## 🔑 Génération Automatique des Mots de Passe

Pour chaque étudiant importé, le système :

1. **Crée un compte User Django** avec :
   - Username : partie avant @ de l'email (ex: `jean.dupont`)
   - Email : l'email de l'étudiant
   - Password : **mot de passe aléatoire sécurisé** (8 caractères)

2. **Lie le compte User au profil Student**

3. **Retourne le mot de passe** dans la réponse de l'import

---

## 📧 Communication aux Étudiants

### Modèle d'email à envoyer

```
Objet : Accès à vos résultats d'examens - Korrigo

Bonjour [Nom de l'étudiant],

Vous pouvez maintenant accéder à vos résultats d'examens sur la plateforme Korrigo.

🔗 URL : https://korrigo.labomaths.tn/

📧 Identifiant : [email de l'étudiant]
🔑 Mot de passe temporaire : [mot de passe généré]

⚠️ IMPORTANT :
- Changez votre mot de passe dès votre première connexion
- Ne partagez jamais votre mot de passe
- Conservez vos identifiants en lieu sûr

Pour changer votre mot de passe :
1. Connectez-vous avec vos identifiants
2. Allez dans "Mon compte" ou "Paramètres"
3. Cliquez sur "Changer le mot de passe"
4. Entrez votre mot de passe actuel et votre nouveau mot de passe

Cordialement,
L'équipe pédagogique
```

---

## 🔐 Connexion des Étudiants

### Processus de connexion

1. L'étudiant va sur : `https://korrigo.labomaths.tn/`
2. Clique sur **"Espace Élève"** ou **"Étudiant"**
3. Entre son **email** (celui du CSV)
4. Entre son **mot de passe** (celui reçu par email)
5. Clique sur **"Se connecter"**

### Endpoints API

**Login :**
```http
POST /api/students/login/
Content-Type: application/json

{
  "email": "jean.dupont@ert.tn",
  "password": "aB3xK9mP"
}
```

**Réponse (succès) :**
```json
{
  "message": "Login successful",
  "role": "Student",
  "must_change_password": false
}
```

---

## 🔄 Changement de Mot de Passe

### Endpoint API

```http
POST /api/students/change-password/
Content-Type: application/json
Cookie: sessionid=...

{
  "current_password": "aB3xK9mP",
  "new_password": "MonNouveauMotDePasse123!"
}
```

**Réponse (succès) :**
```json
{
  "message": "Password changed successfully"
}
```

### Validation du mot de passe

Le nouveau mot de passe doit respecter les règles Django :
- Minimum 8 caractères
- Ne peut pas être trop similaire aux informations personnelles
- Ne peut pas être un mot de passe courant
- Ne peut pas être entièrement numérique

---

## 🛡️ Sécurité

### Mesures de sécurité implémentées

1. **Hachage des mots de passe** : Utilisation de l'algorithme PBKDF2 de Django
2. **Rate limiting** : 5 tentatives de connexion par 15 minutes par IP
3. **Validation des mots de passe** : Règles strictes de complexité
4. **Audit trail** : Toutes les tentatives de connexion sont enregistrées
5. **Session sécurisée** : Cookies HttpOnly, Secure, SameSite
6. **HTTPS obligatoire** : Toutes les communications sont chiffrées

### Bonnes pratiques

- ✅ Communiquez les mots de passe par canal sécurisé (email chiffré, en personne)
- ✅ Encouragez les étudiants à changer leur mot de passe immédiatement
- ✅ Ne stockez jamais les mots de passe en clair
- ✅ Sauvegardez les mots de passe générés dans un gestionnaire sécurisé
- ❌ Ne partagez jamais les mots de passe par SMS ou messagerie non chiffrée

---

## 🔧 Gestion des Comptes Étudiants

### Réinitialisation de mot de passe (Admin)

Si un étudiant oublie son mot de passe, l'administrateur peut le réinitialiser :

```bash
# Sur le serveur
docker exec korrigo-backend-1 python manage.py shell -c "
from students.models import Student
import secrets
import string

# Trouver l'étudiant
student = Student.objects.get(email='jean.dupont@ert.tn')

# Générer un nouveau mot de passe
alphabet = string.ascii_letters + string.digits
new_password = ''.join(secrets.choice(alphabet) for _ in range(8))

# Appliquer le nouveau mot de passe
student.user.set_password(new_password)
student.user.save()

print(f'Nouveau mot de passe pour {student.full_name}: {new_password}')
"
```

### Vérification des comptes

```bash
# Lister tous les étudiants avec leurs comptes
docker exec korrigo-backend-1 python manage.py shell -c "
from students.models import Student

for student in Student.objects.all():
    has_user = 'Oui' if student.user else 'Non'
    print(f'{student.full_name} | {student.email} | Compte: {has_user}')
"
```

---

## 📊 Statistiques et Monitoring

### Vérifier les connexions réussies

```bash
# Voir les dernières connexions d'étudiants
docker exec korrigo-backend-1 python manage.py shell -c "
from core.models import AuditLog

logs = AuditLog.objects.filter(
    action='authentication.attempt',
    metadata__success=True
).order_by('-timestamp')[:10]

for log in logs:
    print(f'{log.timestamp} | {log.metadata}')
"
```

---

## ❓ FAQ

**Q: Que se passe-t-il si j'importe le même CSV deux fois ?**
R: Le système met à jour les étudiants existants (basé sur nom complet + date de naissance). Les comptes User existants ne sont pas modifiés.

**Q: Les mots de passe sont-ils stockés en clair ?**
R: Non, jamais. Django utilise PBKDF2 avec un salt unique pour chaque mot de passe.

**Q: Puis-je personnaliser la longueur des mots de passe générés ?**
R: Oui, modifiez la ligne 259 dans `backend/students/services/csv_import.py`.

**Q: Comment désactiver un compte étudiant ?**
R: Via l'interface admin Django, décochez "Active" sur le compte User de l'étudiant.

---

## 🎯 Résumé

✅ **Système sécurisé** : Mots de passe hachés, rate limiting, audit trail
✅ **Génération automatique** : Mots de passe aléatoires lors de l'import CSV
✅ **Changement de mot de passe** : Les étudiants peuvent changer leur mot de passe
✅ **Confidentialité** : Chaque étudiant a ses propres identifiants uniques
✅ **Traçabilité** : Toutes les connexions sont enregistrées

Le système respecte maintenant les meilleures pratiques de sécurité et de confidentialité pour l'authentification des étudiants.
