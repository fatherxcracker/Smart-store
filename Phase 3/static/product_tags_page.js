// Translates the RFID tags page and updates account navigation

    // Remember the selected language
    let storeLanguage =
        localStorage.getItem("smartstore-language") || "en";

    // English and French translations
    const storeTranslations = {
    "en": {
        "dashboard": "Dashboard",
        "history": "Purchase History",
        "checkoutLink": "Self-checkout",
        "inventoryLink": "Inventory",
        "logout": "Log Out",
        "backInventory": "← Back to Inventory",
        "productManagement": "PRODUCT MANAGEMENT",
        "tagsTitle": "RFID Tags",
        "tagsDescription": "Assign one unique EPC to each physical item after receiving stock.",
        "availableStock": "Available stock",
        "product": "Product",
        "assignTitle": "Assign a Tag",
        "assignDescription": "Place one item on the reader or enter its EPC below.",
        "epcLabel": "EPC (up to 24 hexadecimal characters)",
        "epcHelp": "Use only numbers 0–9 and letters A–F.",
        "readTag": "Read tag from RFID reader",
        "assignTag": "Assign tag",
        "assignedTags": "Assigned Tags",
        "tableDescription": "Check availability and reception dates for each item.",
        "status": "Status",
        "received": "Received",
        "sold": "Sold",
        "available": "Available",
        "notRecorded": "Not recorded",
        "noTags": "No tags assigned.",
        "actions": "Actions",
        "makeAvailable": "Make available",
        "removeTag": "Remove",
        "resetAllSold": "Make all sold tags available",
        "footer": "Smart shopping, better rewards"
    },
    "fr": {
        "dashboard": "Tableau de bord",
        "history": "Historique des achats",
        "checkoutLink": "Caisse libre-service",
        "inventoryLink": "Inventaire",
        "logout": "Déconnexion",
        "backInventory": "← Retour à l’inventaire",
        "productManagement": "GESTION DES PRODUITS",
        "tagsTitle": "Étiquettes RFID",
        "tagsDescription": "Attribuez un EPC unique à chaque article physique après réception du stock.",
        "availableStock": "Stock disponible",
        "product": "Produit",
        "assignTitle": "Attribuer une étiquette",
        "assignDescription": "Placez un article sur le lecteur ou saisissez son EPC ci-dessous.",
        "epcLabel": "EPC (24 caractères hexadécimaux maximum)",
        "epcHelp": "Utilisez uniquement les chiffres 0–9 et les lettres A–F.",
        "readTag": "Lire une étiquette RFID",
        "assignTag": "Attribuer l’étiquette",
        "assignedTags": "Étiquettes attribuées",
        "tableDescription": "Consultez la disponibilité et la date de réception de chaque article.",
        "status": "Statut",
        "received": "Réception",
        "sold": "Vendu",
        "available": "Disponible",
        "notRecorded": "Non enregistré",
        "noTags": "Aucune étiquette attribuée.",
        "actions": "Actions",
        "makeAvailable": "Rendre disponible",
        "removeTag": "Retirer",
        "resetAllSold": "Rendre disponibles toutes les étiquettes vendues",
        "footer": "Magasinez mieux, gagnez plus"
    }
};

    // Change language
    function changeStoreLanguage(language) {

        // Use English if language is not supported
        storeLanguage = storeTranslations[language] ? language : "en";

        // Save language in browser
        localStorage.setItem("smartstore-language", storeLanguage);

        // Update html language
        document.documentElement.lang = storeLanguage;

        // Translate all page text
        document.querySelectorAll("[data-i18n]").forEach(element => {
            const key = element.dataset.i18n;

            if (storeTranslations[storeLanguage][key]) {
                element.textContent =
                    storeTranslations[storeLanguage][key];
            }
        });

        // Translate input placeholders
        document.querySelectorAll("[data-i18n-placeholder]").forEach(element => {
            const key = element.dataset.i18nPlaceholder;

            if (storeTranslations[storeLanguage][key]) {
                element.placeholder =
                    storeTranslations[storeLanguage][key];
            }
        });

        // Highlight selected language
        document.getElementById("lang-en").classList.toggle(
            "selected", storeLanguage === "en"
        );

        document.getElementById("lang-fr").classList.toggle(
            "selected", storeLanguage === "fr"
        );

        // Translate browser tab title
        document.title =
            storeLanguage === "fr"
                ? "Étiquettes RFID | Smart Store"
                : "RFID Tags | Smart Store";
    }

    // English button
    document.getElementById("lang-en").addEventListener("click", () => {
        changeStoreLanguage("en");
    });

    // French button
    document.getElementById("lang-fr").addEventListener("click", () => {
        changeStoreLanguage("fr");
    });

    // Check if customer is logged in
    async function checkStoreLogin() {

        try {
            // Ask Flask for current customer
            const response = await fetch("/api/account/me", {
                credentials: "same-origin"
            });

            // Customer is logged in when request succeeds
            const isLoggedIn = response.ok;

            // Show Dashboard and Purchase History after login
            document.getElementById("account-nav").hidden = !isLoggedIn;

            // Show logout button after login
            document.getElementById("logout-button").hidden = !isLoggedIn;

        } catch (error) {

            // Hide customer buttons if server cannot be reached
            document.getElementById("account-nav").hidden = true;
            document.getElementById("logout-button").hidden = true;
        }
    }

    // Logout customer
    document.getElementById("logout-button").addEventListener(
        "click", async () => {

            try {
                // Tell Flask to log out customer
                const response = await fetch("/api/account/logout", {
                    method: "POST",
                    credentials: "same-origin"
                });

                // Check if logout succeeded
                if (!response.ok) {
                    throw new Error("Logout failed");
                }

                // Return to customer login page
                window.location.href = document.body.dataset.homeUrl;

            } catch (error) {

                // Show error if logout fails
                alert(
                    storeLanguage === "fr"
                        ? "Impossible de se déconnecter"
                        : "Could not log out"
                );
            }
        }
    );

    // Start product translation and navigation
    changeStoreLanguage(storeLanguage);
    checkStoreLogin();
