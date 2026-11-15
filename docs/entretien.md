# Présenter le projet en entretien

## Démonstration en deux minutes

« J’ai cherché à mesurer la contribution des achats répétés et à identifier des actions testables. J’utilise les transactions réelles Online Retail d’UCI, sur plus d’un an. Python et pandas préparent le fichier Excel ; DuckDB exécute les requêtes SQL localement, sans serveur.

Le graphique revenue.png sépare le montant de la première commande observée de celui des commandes suivantes. La barre verte représente 6,86 millions de livres, soit 78,88 % des 8,70 millions de ventes positives des clients identifiés. Pour le calcul, j’agrège d’abord les lignes en factures, puis j’utilise ROW_NUMBER par client, dans l’ordre des dates. Je somme uniquement les commandes de rang deux ou plus. La première commande d’un client qui revient reste donc dans l’autre barre.

J’ai contrôlé que le montant des lignes égale exactement celui des commandes en pence, et que la jointure avec les segments clients conserve le montant et le nombre de commandes.

Pour comprendre le retour des clients, je compare aussi les cohortes mensuelles à 30, 60 et 90 jours. J’écarte les cellules qui n’ont pas assez de recul. Le taux cumulé à 90 jours est de 47,45 % sur les cohortes matures. Enfin, un RFM transparent repère 603 clients ayant plusieurs commandes mais aucune depuis plus de 90 jours.

Je recommande de tester un accompagnement vers la deuxième commande et une relance ciblée, avec un groupe témoin. Le résultat descriptif justifie ces tests ; il ne prouve pas qu’une campagne va fonctionner. »

## Questions probables

- **Pourquoi DuckDB ?** Il exécute du SQL analytique sur des tables pandas et garde une base locale dans un seul fichier. Le projet se reproduit sans installer de serveur.
- **Pourquoi pas un modèle de churn ?** Un achat non contractuel ne donne pas de date de départ certaine. Le seuil de 90 jours est un indicateur d’inactivité interprétable. Une vraie prédiction nécessiterait des fenêtres temporelles d’entraînement et de validation.
- **Pourquoi les cohortes récentes sont-elles grises ?** Leur horizon n’est pas encore observable. Les compter comme des zéros pénaliserait artificiellement les clients les plus récents.
- **59,55 % en décembre contre 38,38 % en mai : l’acquisition s’est-elle dégradée ?** Ce résultat ne le prouve pas. Décembre contient des clients possiblement anciens, et la saison ainsi que les grossistes changent le profil des acheteurs.
- **Est-ce du CA net ?** Le KPI principal mesure les ventes positives. Les avoirs sont séparés : leur facture d’origine n’est pas explicitement renseignée. Leur total est présenté sans inventer d’affectation aux commandes.
- **Pourquoi exclure des identifiants manquants ?** Impossible de distinguer première et deuxième commande sans identité fiable. Le rapport customer_coverage.csv quantifie ce périmètre ; on ne généralise pas le pourcentage à tout le magasin.
- **Une facture avec plusieurs heures est-elle deux commandes ?** Non : 30 factures ont des lignes espacées d’une minute. Je les conserve comme une seule facture à sa première date et j’exporte les anomalies.
- **Que faudrait-il obtenir ensuite ?** Le lien entre avoir et facture initiale, les coûts/marges, les contacts marketing et davantage d’historique pour mesurer les effets et la rentabilité.

Les chiffres ci-dessus correspondent au fichier source archivé et à la fenêtre documentée dans reports/validation.json. Les résultats générés dans reports/executive-summary.md restent la référence.

## Complément : deux définitions à ne pas confondre

Les 78,88 % excluent les premières commandes du numérateur. Les **92,95 %** représentent toutes les ventes des clients ayant passé au moins deux commandes : leur première commande est incluse. Les deux pourcentages utilisent les mêmes 8,70 millions de livres de ventes positives. La différence de 14,07 points correspond aux premières commandes des clients qui rachètent ensuite. Ce classement client utilise toute la période observée : ce n’est pas une information connue au moment de leur premier achat.

L’analyse produits ajoutée suit chaque client à partir de son premier achat de chaque référence, et pas seulement les produits de son tout premier panier. Elle exige 90 jours complets de recul et mesure tout achat suivant, même d’une autre référence. Il faut citer le nombre d’acheteurs éligibles, les acheteurs exclus pour manque de recul et le seuil de comparaison. Les deux analyses produits portent sur des populations différentes : leurs taux ne sont pas interchangeables.
