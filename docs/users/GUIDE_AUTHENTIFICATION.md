# Guide d'Authentification - Korrigo

## Pour les Étudiants

### Première connexion

1. Accédez à l'URL de connexion élève (par exemple: `https://korrigo.example.com/student/login`)
2. Entrez votre **adresse email** (fournie par l'administration)
3. Entrez votre **mot de passe temporaire** (fourni par l'administration)
4. Cliquez sur "Se connecter"

### Changement de mot de passe obligatoire

Lors de votre première connexion avec un mot de passe temporaire, vous serez automatiquement redirigé vers la page de changement de mot de passe :

1. Entrez un **nouveau mot de passe** (minimum 8 caractères)
2. Confirmez le mot de passe en le ressaisissant
3. Cliquez sur "Modifier le mot de passe"

**Conseils pour un mot de passe sécurisé :**
- Au moins 8 caractères
- Mélange de lettres majuscules et minuscules
- Incluez des chiffres
- Ajoutez des caractères spéciaux (!, @, #, etc.)

### Changement de mot de passe ultérieur

Vous pouvez changer votre mot de passe à tout moment depuis votre espace personnel.

### Mot de passe oublié

Si vous avez oublié votre mot de passe :

1. Contactez l'administration du lycée ou votre enseignant responsable
2. Un administrateur réinitialisera votre mot de passe
3. Vous recevrez un nouveau mot de passe temporaire
4. Reconnectez-vous et changez immédiatement le mot de passe

### Compte verrouillé

Après **5 tentatives de connexion échouées**, votre compte sera temporairement verrouillé pendant **15 minutes** pour des raisons de sécurité.

Un message vous indiquera le temps restant avant de pouvoir réessayer.

---

## Pour les Enseignants / Correcteurs

### Connexion

1. Accédez à l'URL de connexion enseignant (par exemple: `https://korrigo.example.com/teacher/login`)
2. Entrez votre **adresse email** ou votre **nom d'utilisateur**
3. Entrez votre **mot de passe**
4. Cliquez sur "Se connecter"

### Première connexion

Si c'est votre première connexion avec un mot de passe temporaire, vous serez invité à le changer immédiatement.

### Changement de mot de passe

Vous pouvez changer votre mot de passe à tout moment :

1. Connectez-vous à votre espace correcteur
2. Accédez aux paramètres de votre compte
3. Sélectionnez "Changer mon mot de passe"
4. Suivez les instructions

### Mot de passe oublié

Contactez l'administrateur système pour réinitialiser votre mot de passe.

---

## Pour l'Administrateur

### Connexion

1. Accédez à l'URL de connexion admin (par exemple: `https://korrigo.example.com/admin/login`)
2. Entrez **username: admin**
3. Entrez votre mot de passe administrateur
4. Cliquez sur "Se connecter"

⚠️ **Important**: L'administrateur se connecte avec son nom d'utilisateur `admin`, pas avec une adresse email.

### Réinitialisation du mot de passe d'un étudiant

1. Connectez-vous en tant qu'administrateur
2. Accédez au tableau de bord administrateur
3. Dans la section "Gestion des Élèves", cliquez sur "Afficher les élèves"
4. Trouvez l'étudiant dans la liste
5. Cliquez sur le bouton "Réinitialiser mot de passe"
6. Une boîte de dialogue affichera le **mot de passe temporaire généré**
7. Notez ce mot de passe immédiatement - il ne sera plus affiché
8. Communiquez-le de manière sécurisée à l'étudiant
9. L'étudiant devra le changer à sa prochaine connexion

⚠️ **Important**:
- Le mot de passe temporaire n'est affiché qu'une seule fois
- L'étudiant sera forcé de le changer à sa prochaine connexion
- Ne communiquez jamais les mots de passe par email non chiffré

### Réinitialisation du mot de passe d'un enseignant

1. Accédez à la section "Utilisateurs" depuis le menu principal
2. Trouvez l'enseignant dans la liste
3. Cliquez sur "Réinitialiser mot de passe"
4. Suivez la même procédure que pour les étudiants

### Changement de votre propre mot de passe

1. Accédez aux paramètres de votre compte
2. Sélectionnez "Changer mon mot de passe"
3. Entrez votre nouveau mot de passe
4. Confirmez et validez

---

## Architecture d'Authentification

### Système unifié Django

Korrigo utilise le système d'authentification Django natif pour tous les types d'utilisateurs :

- **Étudiants**: Email + Mot de passe
- **Enseignants**: Email ou Username + Mot de passe
- **Administrateur**: Username (`admin`) + Mot de passe

### Backend d'authentification personnalisé

Un backend d'authentification personnalisé (`EmailAuthBackend`) gère :
- Authentification par email pour étudiants et enseignants
- Authentification par username pour l'administrateur
- Fallback sur l'authentification standard Django

### Sécurité

**Protection contre les attaques par force brute** :
- Limitation de taux (rate limiting): 5 tentatives par 15 minutes par IP
- Verrouillage de compte: 5 tentatives échouées = 15 minutes de blocage
- Régénération de session après authentification réussie

**Gestion des mots de passe** :
- Hashage sécurisé avec Django (PBKDF2 par défaut)
- Mots de passe temporaires générés de manière cryptographiquement sûre
- Politique de changement obligatoire après réinitialisation

**Audit** :
- Toutes les tentatives de connexion sont journalisées
- Les réinitialisations de mot de passe sont tracées
- Métadonnées d'audit incluant l'administrateur responsable

---

## Identifiants par défaut (Développement uniquement)

⚠️ **Ces identifiants sont pour l'environnement de développement local uniquement. Ne JAMAIS les utiliser en production !**

### Admin
- **Username**: `admin`
- **Password**: `admin` (ou valeur de `ADMIN_PASSWORD` env var)

### Enseignants (x3)
- **Username**: `prof1`, `prof2`, `prof3`
- **Email**: `prof1@viatique.local`, `prof2@viatique.local`, `prof3@viatique.local`
- **Password**: `prof` (ou valeur de `TEACHER_PASSWORD` env var)

### Étudiants (x10)
- **Email**: `eleve1@viatique.local`, `eleve2@viatique.local`, ... `eleve10@viatique.local`
- **Password**: `eleve` (ou valeur de `STUDENT_PASSWORD` env var)

---

## Production - Bonnes pratiques

### Variables d'environnement

En production, définissez ces variables d'environnement avant d'exécuter le script de seed :

```bash
export ADMIN_PASSWORD="VotreMotDePasseSecurise123!"
export TEACHER_PASSWORD="MotDePasseProfSecurise456!"
export STUDENT_PASSWORD="MotDePasseEleveSecurise789!"
```

Si les variables ne sont pas définies, le script génère des mots de passe aléatoires sécurisés et les affiche une seule fois.

### Recommandations

1. **Ne jamais utiliser les mots de passe par défaut en production**
2. **Changer immédiatement tous les mots de passe après le premier déploiement**
3. **Utiliser des mots de passe forts** (minimum 12 caractères, caractères variés)
4. **Activer HTTPS** pour toutes les communications
5. **Configurer des sauvegardes régulières** de la base de données
6. **Monitorer les logs d'audit** pour détecter les activités suspectes
7. **Mettre en place une politique de rotation des mots de passe** (tous les 90 jours)

---

## Dépannage

### Problème : "Compte temporairement verrouillé"

**Cause**: 5 tentatives de connexion échouées

**Solution**: Attendez 15 minutes ou contactez un administrateur pour débloquer le compte

### Problème : "Email ou mot de passe incorrect"

**Solutions possibles**:
1. Vérifiez que vous utilisez la bonne adresse email
2. Vérifiez que le mot de passe est correct (attention à la casse)
3. Si vous avez oublié votre mot de passe, demandez une réinitialisation

### Problème : "Erreur de connexion"

**Solutions possibles**:
1. Vérifiez votre connexion internet
2. Actualisez la page (F5)
3. Videz le cache de votre navigateur
4. Essayez avec un autre navigateur
5. Contactez l'administrateur si le problème persiste

### Problème : Redirection en boucle après connexion

**Cause**: Problème de session ou cookies bloqués

**Solution**:
1. Activez les cookies dans votre navigateur
2. Videz les cookies du site
3. Utilisez un navigateur récent et à jour

---

## Support

Pour toute assistance, contactez :
- **Étudiants**: Votre enseignant responsable ou l'administration
- **Enseignants**: L'administrateur système
- **Problèmes techniques**: L'équipe de support IT du lycée

---

## Annexe : API Endpoints

Documentation technique pour les développeurs.

### Student Login
```
POST /api/students/login/
Body: { "email": "student@example.com", "password": "password" }
Response: { "message": "Connexion réussie", "role": "Student", "must_change_password": false }
```

### Teacher/Admin Login
```
POST /api/login/
Body: { "username": "username_or_email", "password": "password" }
Response: { "message": "Login successful", "role": "Teacher|Admin" }
```

### Change Password
```
POST /api/change-password/
Body: { "password": "new_password" }
Authentication: Required (session)
```

### Admin: Reset Student Password
```
POST /api/students/{student_id}/reset-password/
Authentication: Required (admin)
Response: { "message": "Mot de passe réinitialisé", "temporary_password": "generated_password" }
```

### Admin: Reset Teacher Password
```
POST /api/users/{user_id}/reset-password/
Authentication: Required (admin)
Response: { "message": "Password reset successfully", "temporary_password": "generated_password" }
```

---

**Version**: 1.0
**Dernière mise à jour**: Février 2026
**Système**: Korrigo - Plateforme de correction de copies
