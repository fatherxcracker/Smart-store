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
        "tagsDescription": "Every item in stock has its own RFID tag. Stock = tags not sold yet.",
        "availableStock": "Available stock",
        "product": "Product",
        "assignTitle": "Add a Tag by Hand",
        "assignDescription": "Type the EPC printed on the tag if it can't be scanned. Adds 1 item to stock.",
        "epcLabel": "EPC (up to 24 hexadecimal characters)",
        "epcHelp": "Use only numbers 0–9 and letters A–F.",
        "readTag": "Read tag from RFID reader",
        "bulkTitle": "Scan Tagged Items",
        "bulkDescription": "Put one or more new items on the reader and scan. Each tag adds 1 item to stock. Tags already on an item in stock are skipped, and each tag is only added once.",
        "scanAll": "Scan tags on reader",
        "assignTag": "Add item to stock",
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
        "tagsDescription": "Chaque article en stock a sa propre étiquette RFID. Stock = étiquettes pas encore vendues.",
        "availableStock": "Stock disponible",
        "product": "Produit",
        "assignTitle": "Ajouter une étiquette à la main",
        "assignDescription": "Saisissez l’EPC imprimé sur l’étiquette s’il ne peut pas être lu. Ajoute 1 article au stock.",
        "epcLabel": "EPC (24 caractères hexadécimaux maximum)",
        "epcHelp": "Utilisez uniquement les chiffres 0–9 et les lettres A–F.",
        "readTag": "Lire une étiquette RFID",
        "bulkTitle": "Lire des articles étiquetés",
        "bulkDescription": "Placez un ou plusieurs nouveaux articles sur le lecteur et lancez la lecture. Chaque étiquette ajoute 1 article au stock. Les étiquettes déjà sur un article en stock sont ignorées, et chaque étiquette n’est ajoutée qu’une fois.",
        "scanAll": "Lire les étiquettes",
        "assignTag": "Ajouter l’article au stock",
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
