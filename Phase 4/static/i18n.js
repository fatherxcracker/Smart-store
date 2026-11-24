/* English / French for the Phase 4 pages (dashboard, reports, fridges, sensor).
   The page is written in English; every text is looked up here and swapped for
   French when the language is "fr". The language is the same one the store
   portal uses (localStorage "smartstore-language"), so one switch changes both.
   Texts added by scripts (live widgets, charts) are translated as they appear. */
(function () {
    "use strict";
    var KEY = "smartstore-language";

    var FR = {
        // header and navigation
        "Dashboard & reports": "Tableau de bord et rapports", "Account": "Compte", "Checkout": "Caisse",
        "Manage inventory": "Gérer l'inventaire", "Print / save PDF": "Imprimer / enregistrer en PDF",
        "STORE INSIGHTS": "APERÇU DU MAGASIN", "Dashboard": "Tableau de bord", "Inventory": "Inventaire",
        "Sales": "Ventes", "Customer activity": "Activité des clients", "Fridges & fan": "Réfrigérateurs et ventilateur",
        "MSP01 sensor": "Capteur MSP01", "My purchases": "Mes achats", "My purchase reports": "Mes rapports d'achats",
        "Inventory report": "Rapport d'inventaire", "Sales report": "Rapport des ventes", "Minew MSP01 sensor": "Capteur Minew MSP01",
        "Reports": "Rapports", "Store": "Magasin",
        // admin dashboard shell
        "Admin dashboard": "Tableau de bord administrateur", "ADMIN DASHBOARD": "TABLEAU DE BORD ADMINISTRATEUR", "MY ACCOUNT": "MON COMPTE",
        "Overview": "Aperçu", "Store overview": "Aperçu du magasin", "Live monitoring": "Surveillance en direct", "Products & stock": "Produits et stock", "Users": "Utilisateurs",
        "Notifications": "Notifications", "Log Out": "Déconnexion",
        "My account": "Mon compte", "Membership & points": "Carte de membre et points", "Purchase history": "Historique d'achats",
        "Self-checkout": "Caisse libre-service",
        "Dashboard content": "Contenu du tableau de bord", "Dashboard sections": "Sections du tableau de bord",
        "Back to dashboard": "Retour au tableau de bord", "Back to the admin dashboard": "Retour au tableau de bord administrateur", "Store notifications": "Notifications du magasin",
        "Latest 100 events: stock received, checkouts, low-stock notices, product changes and errors.": "100 derniers événements : stock reçu, achats, avis de stock bas, modifications de produits et erreurs.",
        "Message": "Message", "See all": "Tout voir", "No notifications yet.": "Aucune notification pour l'instant.",
        "Success": "Succès", "Warning": "Avertissement", "Info": "Info", "Error": "Erreur",
        // filters
        "From": "Du", "Through": "Au", "Search item": "Chercher un article", "Product / price history": "Produit / historique des prix",
        "All my products": "Tous mes produits", "Apply filters": "Appliquer les filtres", "Apply filter": "Appliquer le filtre",
        "Reset": "Réinitialiser", "Reset filters": "Réinitialiser les filtres", "Download CSV": "Télécharger en CSV",
        "Top / bottom": "Meilleurs / moins bons", "Category": "Catégorie", "All categories": "Toutes les catégories",
        "Product name": "Nom du produit", "Live report · refreshes every 5 seconds": "Rapport en direct · mise à jour toutes les 5 secondes",
        "Check your filters": "Vérifiez vos filtres",
        // customer reports
        "Total spent in date period": "Total dépensé pour la période", "Receipts in date period": "Reçus pour la période",
        "Matching purchases / units": "Achats correspondants / unités",
        "Total spending includes all your receipts in the date period, after points discounts and including tax. Item filters narrow the receipt list and matching purchases, not that spending total.":
            "Le total dépensé inclut tous vos reçus de la période, après les rabais de points et avec les taxes. Les filtres d'article réduisent la liste des reçus et des achats correspondants, pas ce total.",
        "Spending over time": "Dépenses dans le temps", "What you paid each day (after points discounts, including tax).": "Ce que vous avez payé chaque jour (après rabais de points, taxes incluses).",
        "Inflation report: price history": "Rapport d'inflation : historique des prix",
        "Unit prices paid on each purchase, before points discounts and tax. Product price changes today do not change this history.":
            "Prix unitaires payés à chaque achat, avant les rabais de points et les taxes. Les changements de prix d'aujourd'hui ne modifient pas cet historique.",
        "No purchases in this period. Try a different date range.": "Aucun achat pour cette période. Essayez une autre plage de dates.",
        "Choose one product above to display its price-history chart.": "Choisissez un produit ci-dessus pour afficher son graphique d'historique des prix.",
        "Matching item purchases": "Achats d'articles correspondants", "Date and time": "Date et heure", "Product": "Produit",
        "Quantity": "Quantité", "Unit price": "Prix unitaire", "Receipt": "Reçu",
        "No matching purchases for these filters.": "Aucun achat ne correspond à ces filtres.", "Your receipts": "Vos reçus",
        "No receipts match these filters.": "Aucun reçu ne correspond à ces filtres.",
        "Daily spending chart": "Graphique des dépenses quotidiennes", "Historical purchase prices": "Prix d'achat historiques",
        // dashboard
        "Sales today (incl. tax)": "Ventes du jour (taxes incl.)", "Orders today": "Commandes du jour", "Customers today": "Clients du jour",
        "Low-stock products": "Produits en stock faible", "Sales, last 7 days": "Ventes des 7 derniers jours", "Low stock": "Stock faible",
        "Every product is above its low-stock limit.": "Tous les produits sont au-dessus de leur seuil de stock faible.",
        "Open the inventory report": "Ouvrez le rapport d'inventaire", "to change each category's limit.": "pour modifier le seuil de chaque catégorie.",
        "Refrigerators": "Réfrigérateurs", "Open fridge controls": "Ouvrir les commandes des réfrigérateurs",
        "Refrigerator 1": "Réfrigérateur 1", "Refrigerator 2": "Réfrigérateur 2", "Normal": "Normal", "Too warm": "Trop chaud",
        "Waiting for data": "En attente de données", "Fan": "Ventilateur", "OFF": "ARRÊT", "ON": "MARCHE",
        "Open sensor page": "Ouvrir la page du capteur", "Temperature": "Température", "Humidity": "Humidité",
        "Light intensity": "Intensité lumineuse", "Motion": "Mouvement", "Sensor status": "État du capteur",
        "Online": "En ligne", "No data yet": "Pas encore de données", "Offline (stale)": "Hors ligne (données périmées)",
        "Motion detected": "Mouvement détecté", "No motion": "Aucun mouvement", "No motion yet": "Aucun mouvement pour l'instant",
        "Waiting for the sensor": "En attente du capteur", "Recent notifications": "Notifications récentes",
        "No notifications yet.": "Aucune notification pour l'instant.", "Loading…": "Chargement…",
        "Fridge monitoring is not running.": "La surveillance des réfrigérateurs n'est pas active.",
        "Sales in the last 7 days": "Ventes des 7 derniers jours", "No sales yet this week.": "Aucune vente cette semaine.",
        "Log in again as an administrator.": "Reconnectez-vous en tant qu'administrateur.",
        "Could not refresh. Retrying shortly.": "Actualisation impossible. Nouvelle tentative bientôt.",
        // inventory report
        "Active products": "Produits actifs", "Units in stock": "Unités en stock", "Low stock products": "Produits en stock faible",
        "Moderate stock products": "Produits en stock modéré", "Available stock": "Stock disponible",
        "Every unit is one RFID-tagged item.": "Chaque unité est un article avec une étiquette RFID.",
        "below the category limit ·": "sous le seuil de la catégorie ·", "below twice the limit ·": "sous le double du seuil ·",
        "otherwise. Change each category's limit in the section below.": "sinon. Modifiez le seuil de chaque catégorie dans la section ci-dessous.",
        "ID": "ID", "Available": "Disponible", "Last restocked": "Dernier réapprovisionnement", "Level": "Niveau", "Never": "Jamais",
        "low": "faible", "moderate": "modéré", "good": "bon", "No products in this category.": "Aucun produit dans cette catégorie.",
        "Low-stock limit per category": "Seuil de stock faible par catégorie", "A product is": "Un produit est",
        "when fewer units than the limit remain. The checkout then sends a low-stock notification. Default: 5 units.":
            "lorsqu'il reste moins d'unités que le seuil. La caisse envoie alors une notification de stock faible. Par défaut : 5 unités.",
        "Save": "Enregistrer", "No categories yet.": "Aucune catégorie pour l'instant.",
        // sales
        "Total paid, including tax": "Total payé, taxes incluses", "Net sales, before tax": "Ventes nettes, avant taxes",
        "Units sold / orders": "Unités vendues / commandes", "Points discounts": "Rabais de points", "Sales over time": "Ventes dans le temps",
        "Most sold": "Les plus vendus", "Least sold": "Les moins vendus", "Sold items by product": "Articles vendus par produit",
        "Item sales use the price at purchase before points discounts and tax. Active products with zero sales are included; deleted products appear if sold in this period.":
            "Les ventes d'articles utilisent le prix à l'achat, avant les rabais de points et les taxes. Les produits actifs sans vente sont inclus; les produits supprimés apparaissent s'ils ont été vendus durant cette période.",
        "Sold quantity": "Quantité vendue", "Item sales before discounts": "Ventes d'articles avant rabais", "Daily sales": "Ventes quotidiennes",
        "Download daily sales (CSV)": "Télécharger les ventes quotidiennes (CSV)", "Date": "Date", "Orders": "Commandes",
        "Total paid": "Total payé", "No products.": "Aucun produit.", "Daily sales chart": "Graphique des ventes quotidiennes",
        // customers
        "Distinct purchasing members": "Membres acheteurs distincts", "New purchasing members": "Nouveaux membres acheteurs",
        "Returning members": "Membres qui reviennent", "Guest / unlinked orders": "Commandes d'invités / non liées",
        "New = first-ever purchase in this period. Returning = purchased before the period. Each member is counted once for the period. Guests and deleted accounts cannot be identified as distinct customers; their orders are shown separately.":
            "Nouveau = premier achat de tous les temps durant cette période. Qui revient = a déjà acheté avant la période. Chaque membre est compté une fois pour la période. Les invités et les comptes supprimés ne peuvent pas être identifiés comme des clients distincts; leurs commandes sont indiquées séparément.",
        "Purchasing customers over time": "Clients acheteurs dans le temps", "Busiest days": "Jours les plus achalandés",
        "Quietest days": "Jours les plus tranquilles", "Daily activity": "Activité quotidienne",
        "Rankings use distinct purchasing members, not foot traffic. Zero-purchase days are included; all ties are listed.":
            "Les classements utilisent les membres acheteurs distincts, pas l'achalandage. Les jours sans achat sont inclus; toutes les égalités sont indiquées.",
        "Purchasing members": "Membres acheteurs", "Daily purchasing customer count": "Nombre quotidien de clients acheteurs",
        // fridges
        "and the fan starts; reply NO and nothing happens.": "et le ventilateur démarre; répondez NON et rien ne se passe.",
        "Temperature limit (°C)": "Limite de température (°C)", "Temperature, last 6 hours": "Température, 6 dernières heures",
        "No history yet - readings are saved every 30 seconds.": "Pas encore d'historique : les relevés sont enregistrés toutes les 30 secondes.",
        "Fan control": "Commande du ventilateur", "duty cycle": "rapport cyclique", "Turn ON": "Allumer", "Turn OFF": "Éteindre",
        "Speed": "Vitesse", "Alerts and notifications": "Alertes et notifications", "No active alerts.": "Aucune alerte active.",
        "Waiting for data": "En attente de données", "No reading received yet.": "Aucun relevé reçu pour l'instant.",
        "Enter a valid temperature limit first.": "Entrez d'abord une limite de température valide.",
        // sensor
        "Two DHT11 sensors (ESP32 → Mosquitto) watch the refrigerators. Above the limit, an email asks whether to turn on the fan: reply":
            "Deux capteurs DHT11 (ESP32 → Mosquitto) surveillent les réfrigérateurs. Au-dessus de la limite, un courriel demande s'il faut allumer le ventilateur : répondez",
        "YES": "OUI",
        "Minew MSP01 BLE sensor: temperature, humidity, light intensity and motion. Readings arrive by Bluetooth scan, MQTT topic":
            "Capteur Bluetooth Minew MSP01 : température, humidité, intensité lumineuse et mouvement. Les relevés arrivent par balayage Bluetooth, par le sujet MQTT",
        "or the": "ou par le point d'accès", "endpoint. A sensor that has not reported for 5 minutes is shown as offline.":
            ". Un capteur qui n'a rien envoyé depuis 5 minutes est affiché comme hors ligne.",
        "History": "Historique", "Last hour": "Dernière heure", "Last 6 hours": "6 dernières heures", "Last 24 hours": "24 dernières heures",
        "Last 7 days": "7 derniers jours", "Motion events": "Événements de mouvement", "events in the last 24 hours": "événements dans les dernières 24 heures",
        "Time": "Heure", "No motion in this period.": "Aucun mouvement durant cette période.",
        "No temperature readings in this period.": "Aucun relevé de température durant cette période.",
        "No humidity readings in this period.": "Aucun relevé d'humidité durant cette période.",
        "No light readings in this period.": "Aucun relevé de lumière durant cette période.",
        "Temperature history": "Historique de la température", "Humidity history": "Historique de l'humidité", "Light history": "Historique de la lumière",
        // levels of notifications
        "warning": "avertissement", "success": "succès", "info": "info", "error": "erreur",
        // errors from the server
        "Enter a valid date in YYYY-MM-DD format.": "Entrez une date valide au format AAAA-MM-JJ.",
        "The end date must be on or after the start date.": "La date de fin doit être égale ou postérieure à la date de début.",
        "Choose a period of at most 366 days.": "Choisissez une période d'au plus 366 jours.",
        "Choose an earlier end date.": "Choisissez une date de fin plus rapprochée.",
        "Choose a valid ranking size.": "Choisissez une taille de classement valide.",
        "Choose between 1 and 50 ranked products.": "Choisissez entre 1 et 50 produits classés.",
        "Choose a valid product.": "Choisissez un produit valide.", "Choose a category from the list.": "Choisissez une catégorie dans la liste.",
        "The low-stock limit must be a whole number.": "Le seuil de stock faible doit être un nombre entier.",
        "The low-stock limit must be between 0 and 100000.": "Le seuil de stock faible doit être entre 0 et 100000.",
        "Your session or access has changed. Log in again on the account page.": "Votre session ou votre accès a changé. Reconnectez-vous sur la page du compte.",
        "Could not refresh. Showing the last successful report; retrying shortly.": "Actualisation impossible. Dernier rapport affiché; nouvelle tentative bientôt.",
        "Welcome, Store Admin!": "Bienvenue, Store Admin!",
        // fixed product categories
        "Bakery": "Boulangerie", "Beverages": "Boissons", "Candy": "Bonbons", "Dairy": "Produits laitiers", "Deli": "Charcuterie",
        "Frozen Foods": "Surgelés", "Fruits & Vegetables": "Fruits et légumes", "Health & Beauty": "Santé et beauté", "Household": "Entretien ménager",
        "Meat & Seafood": "Viandes et poissons", "Pantry": "Épicerie", "Pet Supplies": "Animaux", "Snacks": "Collations", "Other": "Autre",
        "cash": "comptant", "credit": "crédit", "debit": "débit", "card": "carte"
    };

    // Texts with numbers or names inside: [pattern, replacement]
    var RULES = [
        [/^Signed in as (.*)$/, "Connecté en tant que $1"],
        [/^Dates include the whole selected day in (.+)\. Maximum period: 366 days\.$/, "Les dates incluent toute la journée sélectionnée (fuseau : $1). Période maximale : 366 jours."],
        [/^Updated (.+) · refreshes every 5 seconds$/, "Mis à jour à $1 · actualisation toutes les 5 secondes"],
        [/^Updated (.+)$/, function (m, a) { return "Mis à jour : " + translate(a); }],
        [/^(\d+) units?$/, "$1 unité(s)"],
        [/^Daily amounts paid, including tax\. GST: (.+) · QST: (.+)$/, "Montants payés par jour, taxes incluses. TPS : $1 · TVQ : $2"],
        [/^Refrigerator (\d) temperature, last 6 hours$/, "Température du réfrigérateur $1, 6 dernières heures"],
        [/^Last 7 days: (.+)$/, "7 derniers jours : $1"],
        [/^Humidity (.+) · limit (.+)$/, "Humidité $1 · limite $2"],
        [/^Battery (.+)$/, "Batterie $1"],
        [/^Last motion (.+) · (\d+) events? in the last hour$/, function (m, a, n) { return "Dernier mouvement : " + translate(a) + " · " + n + " événement(s) dans la dernière heure"; }],
        [/^(\d+)% duty cycle · MQTT (connected|not connected)$/, function (m, d, s) { return d + " % rapport cyclique · MQTT " + (s === "connected" ? "connecté" : "non connecté"); }],
        [/^(\d+)% duty cycle$/, "$1 % rapport cyclique"],
        [/^(.+) \((.+)\) — $/, "$1 ($2) — "],
        [/^(\d+) left$/, "$1 restant(s)"],
        [/^ · limit (\d+)$/, " · seuil $1"],
        [/^(\d+) purchasing members per day$/, "$1 membre(s) acheteur(s) par jour"],
        [/^Smart Store · Phase 4 · (.*)$/, "Smart Store · Phase 4 · $1"],
        [/^(\d+) s ago$/, "il y a $1 s"], [/^(\d+) min ago$/, "il y a $1 min"], [/^(\d+) h ago$/, "il y a $1 h"], [/^(\d+) days ago$/, "il y a $1 jours"],
        [/^just now$/, "à l'instant"], [/^never$/, "jamais"],
        [/^Temperature alert: Refrigerator (\d) is (.+)C \(threshold (.+)C\)\. Email sent - waiting for a response\.$/, "Alerte de température : le réfrigérateur $1 est à $2C (seuil $3C). Courriel envoyé : en attente d'une réponse."],
        [/^Temperature alert: Refrigerator (\d) is (.+)C \(threshold (.+)C\)\. The alert email could not be sent \(check \.env SMTP settings\)\.$/, "Alerte de température : le réfrigérateur $1 est à $2C (seuil $3C). Le courriel d'alerte n'a pas pu être envoyé (vérifiez les réglages SMTP du fichier .env)."],
        [/^Refrigerator (\d) threshold set to (.+)C\.$/, "Seuil du réfrigérateur $1 réglé à $2C."],
        [/^User replied YES \((.+)\) - fan turned ON at (\d+)% \(Refrigerator (\d) was (.+)C\)\.$/, "Réponse OUI ($1) : ventilateur allumé à $2 % (réfrigérateur $3 : $4C)."],
        [/^User replied NO \((.+)\) - no action taken for Refrigerator (\d) \((.+)C\)\.$/, "Réponse NON ($1) : aucune action pour le réfrigérateur $2 ($3C)."],
        [/^Fan duty cycle set to (\d+)%\.$/, "Vitesse du ventilateur réglée à $1 %."],
        [/^Fan turned ON manually at (\d+)% duty cycle\.$/, "Ventilateur allumé manuellement à $1 %."],
        [/^Fan turned OFF manually from the dashboard\.$/, "Ventilateur éteint manuellement depuis le tableau de bord."],
        [/^(.+): low stock is now below (\d+) units\.$/, "$1 : le stock est maintenant faible sous $2 unités."],
        [/^Welcome, (.+)!$/, "Bienvenue, $1!"],
        [/^(\d+) ([A-Za-z]+ .*)$/, null]
    ].filter(function (r) { return r[1] !== null; });

    var originals = new WeakMap();   // text node -> English text
    var written = new WeakMap();     // text node -> last text we wrote (to ignore our own changes)
    var lang = "en";

    function stored() { try { return localStorage.getItem(KEY) === "fr" ? "fr" : "en"; } catch (e) { return "en"; } }

    function translate(text) {
        if (lang !== "fr") return text;
        var trimmed = text.trim();
        if (!trimmed) return text;
        var lead = text.slice(0, text.indexOf(trimmed)), tail = text.slice(text.indexOf(trimmed) + trimmed.length);
        var found = FR[trimmed];
        if (found === undefined) {
            for (var i = 0; i < RULES.length; i++) {
                if (RULES[i][0].test(trimmed)) { found = trimmed.replace(RULES[i][0], RULES[i][1]); break; }
            }
        }
        return found === undefined ? text : lead + found + tail;
    }

    window.t = function (text) { return translate(String(text)); };

    function applyNode(node, force) {
        var current = node.data;
        if (written.get(node) === current) {
            if (!force) return;                          // our own write, nothing new
        } else {
            originals.set(node, current);                // a script wrote new English text
        }
        var out = translate(originals.get(node));
        if (out !== current) { written.set(node, out); node.data = out; } else { written.set(node, current); }
    }

    function walk(root, force) {
        var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
            acceptNode: function (n) {
                var p = n.parentNode && n.parentNode.nodeName;
                return p === "SCRIPT" || p === "STYLE" || p === "NOSCRIPT" ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
            }
        });
        var n;
        while ((n = w.nextNode())) applyNode(n, force);
    }

    var ATTRS = ["placeholder", "aria-label", "title"];
    function attributes(root) {
        var list = root.querySelectorAll ? root.querySelectorAll("[placeholder],[aria-label],[title]") : [];
        Array.prototype.forEach.call(list, function (el) {
            ATTRS.forEach(function (a) {
                if (!el.hasAttribute(a)) return;
                var key = "data-en-" + a;
                if (!el.hasAttribute(key)) el.setAttribute(key, el.getAttribute(a));
                el.setAttribute(a, translate(el.getAttribute(key)));
            });
        });
    }

    function title() {
        if (!document.documentElement.hasAttribute("data-en-title")) document.documentElement.setAttribute("data-en-title", document.title);
        var english = document.documentElement.getAttribute("data-en-title");
        var parts = english.split(" | ");
        document.title = parts.map(function (p) { return translate(p); }).join(" | ");
    }

    function everything() {
        document.documentElement.lang = lang;
        walk(document.body, true);
        attributes(document.body);
        title();
        var en = document.getElementById("lang-en"), fr = document.getElementById("lang-fr");
        if (en && fr) {
            en.setAttribute("aria-pressed", lang === "en"); fr.setAttribute("aria-pressed", lang === "fr");
            en.classList.toggle("active", lang === "en"); fr.classList.toggle("active", lang === "fr");
        }
        document.dispatchEvent(new CustomEvent("smartstore-language", { detail: lang }));
        walk(document.body, true);   // charts redrawn by the event above add new text
    }
    window.translatePage = everything;

    function setLanguage(next) {
        lang = next === "fr" ? "fr" : "en";
        try { localStorage.setItem(KEY, lang); } catch (e) { /* ignore */ }
        everything();
        // Keep the account's language (used for receipt emails) in step when signed in.
        try {
            fetch("/api/account/language", { method: "POST", credentials: "same-origin",
                headers: { "Content-Type": "application/json" }, body: JSON.stringify({ language: lang }) }).catch(function () {});
        } catch (e) { /* ignore */ }
    }

    lang = stored();
    document.documentElement.lang = lang;
    window.addEventListener("storage", function (event) {
        if (event.key === KEY && stored() !== lang) { lang = stored(); everything(); }
    });

    document.addEventListener("DOMContentLoaded", function () {
        var en = document.getElementById("lang-en"), fr = document.getElementById("lang-fr");
        if (en) en.addEventListener("click", function () { setLanguage("en"); });
        if (fr) fr.addEventListener("click", function () { setLanguage("fr"); });
        everything();
        // Translate whatever scripts add or change later (live tiles, charts, refreshed reports).
        var pending = false;
        new MutationObserver(function (records) {
            if (pending) return;
            pending = true;
            setTimeout(function () {
                pending = false;
                walk(document.body);
                attributes(document.body);
            }, 0);
        }).observe(document.body, { childList: true, subtree: true, characterData: true });
    });
})();
