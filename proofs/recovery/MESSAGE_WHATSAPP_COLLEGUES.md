# Message WhatsApp à envoyer aux collègues

## Message unique — à envoyer tel quel

---

Salut à tous 👋

J'ai passé du temps à analyser en profondeur le code de Korrigo pour voir s'il y avait un moyen de récupérer les notes et annotations perdues directement depuis vos navigateurs.

Bonne nouvelle : Korrigo sauvegarde automatiquement une copie de toutes les notes que vous saisissez (question par question) directement dans le navigateur, en plus du serveur. Et cette sauvegarde locale n'est jamais supprimée — elle reste même après un crash serveur.

Concrètement : si vous avez noté des copies entre le 20 février et le crash, ces notes sont potentiellement encore dans votre navigateur. Ça nous éviterait de tout recorriger !

J'ai préparé une page toute simple qui fait l'extraction automatiquement. Ça ne modifie rien, ça ne supprime rien, ça ne fait que lire et exporter.

La manip prend 30 secondes :

1. Sur l'ordinateur où vous avez corrigé, ouvrez le même navigateur que d'habitude (Chrome, Firefox, Edge…)
2. Ouvrez ce lien : https://korrigo.labomaths.tn/recovery.html
3. Cliquez sur le bouton bleu "Lancer l'extraction"
4. Attendez quelques secondes — un fichier JSON se télécharge
5. Envoyez-moi ce fichier ici sur WhatsApp 📎

C'est tout !

⚠️ Important :
- Faites-le sur le même ordi et le même navigateur que celui que vous avez utilisé pour corriger
- Si vous avez plusieurs profils dans Chrome, testez sur chacun
- Ne videz surtout pas votre cache navigateur en attendant

Merci d'avance et désolé pour le dérangement 🙏

---

## Notes pour Alaeddine (ne pas envoyer)

- La page https://korrigo.labomaths.tn/recovery.html est hébergée directement sur le serveur
- Elle charge recovery.js (V3 exhaustive) et recovery.css depuis le même domaine
- CSP compliant : pas de JS/CSS inline, tout est en fichiers externes
- Le script scanne : localStorage, sessionStorage, cookies, IndexedDB, Cache Storage, Service Workers, Performance API, OPFS
- Les collègues prioritaires : **Patrick** (26 copies), **Laroussi** (23), **Edouard** (22), **Selima** (14)
- Si un collègue a plusieurs profils Chrome, il doit tester sur CHACUN d'eux
- Les données `korrigo_scores_*` contiennent les **anciens UUIDs** — le mapping vers les nouvelles copies sera fait côté serveur via `reconstitution_data_v2.json`
- Fichiers déployés sur le serveur : `/usr/share/nginx/html/recovery.{html,js,css}`
