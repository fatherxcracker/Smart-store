// Translates the receive stock page and updates account navigation

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
            receiveStockTitle: "Receive Stock",
            receiveStockDesc: "Record a new delivery and update product quantities",
            deliveryDetails: "Delivery Details",
            formDescription: "Enter the information for the received stock",
            product: "Product",
            selectProduct: "Select a product",
            quantityReceived: "Quantity Received",
            receptionDate: "Reception Date and Time",
            note: "Note (optional)",
            notePlaceholder: "Add a delivery note",
            recordDelivery: "Record Delivery",
            noProducts: "No products are available yet",
            addProductFirst: "Add a product first",
            inStock: "in stock",
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
            receiveStockTitle: "Réceptionner du stock",
            receiveStockDesc: "Enregistrez une nouvelle livraison et mettez à jour les quantités",
            deliveryDetails: "Détails de la livraison",
            formDescription: "Entrez les informations du stock reçu",
            product: "Produit",
            selectProduct: "Sélectionnez un produit",
            quantityReceived: "Quantité reçue",
            receptionDate: "Date et heure de réception",
            note: "Note (facultative)",
            notePlaceholder: "Ajoutez une note de livraison",
            recordDelivery: "Enregistrer la livraison",
            noProducts: "Aucun produit n'est disponible pour le moment",
            addProductFirst: "Ajoutez d'abord un produit",
            inStock: "en stock",
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

        // Translate product stock text in dropdown
        document.querySelectorAll("[data-product-name]").forEach(option => {

            // Keep product name and stock number from database
            const name = option.dataset.productName;
            const stock = option.dataset.productStock;

            // Translate only the in stock text
            option.textContent =
                name + " — " + stock + " " +
                storeTranslations[storeLanguage].inStock;
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
                ? "Réceptionner du stock | Smart Store"
                : "Receive Stock | Smart Store";
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

    // Start stock translation and navigation
    changeStoreLanguage(storeLanguage);
    checkStoreLogin();
