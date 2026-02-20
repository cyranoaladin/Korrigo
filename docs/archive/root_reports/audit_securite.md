### Analyse de l'Isolation des Données & Risques de Fuite

Suite à l'analyse approfondie du code backend (modèles, sérialiseurs et vues), voici les conclusions concernant l'isolation entre les données élèves et les copies :

#### 1. Architecture de Base de Données (Niveau Risque : Moyen)
L'isolation au niveau de la base de données est **faible mais fonctionnelle si bien gérée**.
- **Lien Direct :** Le modèle `Copy` (`backend/exams/models.py`) possède une clé étrangère directe vers `Student` (`student = models.ForeignKey(...)`).
- **Absence de Table de Correspondance :** Il n'y a pas de table intermédiaire (ex: `AnonymizationMapping`) qui séparerait physiquement le lien. L'anonymat repose uniquement sur le champ `anonymous_id` et la discipline des développeurs à ne pas interroger le champ `student`.
- **Modèles Connexes :** Les modèles de correction (`Annotation`, `GradingEvent`) sont correctement isolés (liés à `Copy` uniquement), ce qui est un bon point.

#### 2. Couche API & Sérialisation (Niveau Risque : ÉLEVÉ)
L'isolation est **rompue** au niveau de l'API exposée aux correcteurs.
- **Fuite d'Identifiant :** Le `CopySerializer` (`backend/exams/serializers.py`) inclut explicitement le champ `'student'` dans `Meta.fields`. Bien que cela ne renvoie que l'ID (ex: `student: 42`), cela permet à un correcteur de désanonymiser la copie s'il a accès à une liste d'élèves ou s'il peut deviner l'ID.
- **Vues Correcteurs :** Les vues `CorrectorCopiesView` et `CorrectorCopyDetailView` (`backend/exams/views.py`) utilisent ce sérialiseur standard. De plus, elles effectuent un `select_related('student')`, chargeant délibérément les données élèves en mémoire pour chaque requête.

#### 3. Risques Identifiés
1.  **Désanonymisation par ID :** Un correcteur malveillant ou curieux peut utiliser l'ID élève exposé dans le JSON de la copie pour retrouver l'identité de l'élève (via une autre API ou par déduction de classe).
2.  **Fuite Accidentelle Frontend :** Si le frontend utilise le même objet pour l'affichage, un bug d'interface pourrait afficher le nom de l'élève récupéré "en trop" par l'API.

#### Recommandations Immédiates
1.  **Créer un Sérialiseur Dédié :** Implémenter un `CorrectorCopySerializer` qui exclut formellement les champs `student` et `is_identified`.
2.  **Modifier les Vues Correcteurs :** Mettre à jour `CorrectorCopiesView` pour utiliser ce sérialiseur sécurisé et retirer le `select_related('student')` des requêtes.

Voulez-vous que je procède à la création de ce sérialiseur sécurisé (`CorrectorCopySerializer`) et à la mise à jour des vues pour colmater cette fuite ?
