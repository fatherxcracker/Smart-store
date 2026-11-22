// Translates the edit product page and updates account navigation

    // Remember the selected language
    let storeLanguage =
        localStorage.getItem("smartstore-language") || "en";

    // English and French translations
    const storeTranslations = {

        // English translations
        en: {
            dashboard: "Dashboard",
            history: "Purchase History",
            checkoutLink: "Self-checkout",
            inventoryLink: "Inventory",
            logout: "Log Out",
            backInventory: "← Back to Inventory",
            productManagement: "PRODUCT MANAGEMENT",
            editProductTitle: "Edit Product",
            editProductDesc: "Update the information for this product",
            productDetails: "Product Details",
            formDescription: "Make changes to the product information",
            productName: "Product Name",
            category: "Category",
            price: "Price ($)",
            upcLabel: "UPC — Barcode (maximum 13 characters)",
            upcPlaceholder: "Click here and scan the barcode",
            epcLabel: "EPC — RFID Tag (optional, maximum 24 characters)",
            readTag: "Read Tag from RFID Reader",
            producer: "Producer Company",
            saveChanges: "Save Changes",
            footer: "Smart shopping, better rewards"
        },

        // French translations
        fr: {
            dashboard: "Tableau de bord",
            history: "Historique des achats",
            checkoutLink: "Caisse libre-service",
            inventoryLink: "Inventaire",
            logout: "Déconnexion",
            backInventory: "← Retour à l'inventaire",
            productManagement: "GESTION DES PRODUITS",
            editProductTitle: "Modifier le produit",
            editProductDesc: "Modifiez les informations de ce produit",
            productDetails: "Détails du produit",
            formDescription: "Apportez des modifications aux informations du produit",
            productName: "Nom du produit",
            category: "Catégorie",
            price: "Prix ($)",
            upcLabel: "UPC — Code-barres (maximum 13 caractères)",
            upcPlaceholder: "Cliquez ici et numérisez le code-barres",
            epcLabel: "EPC — Étiquette RFID (facultatif, maximum 24 caractères)",
            readTag: "Lire l'étiquette avec le lecteur RFID",
            producer: "Entreprise productrice",
            saveChanges: "Enregistrer les modifications",
            footer: "Magasinez mieux, gagnez plus"
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
                ? "Modifier le produit | Smart Store"
                : "Edit Product | Smart Store";
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
