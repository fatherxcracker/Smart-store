// Translates the inventory page and updates account navigation

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
            backAccounts: "← Back to Customer Accounts",
            productManagement: "PRODUCT MANAGEMENT",
            inventoryTitle: "Inventory",
            inventoryDesc: "Manage products, stock quantities and deliveries",
            addProduct: "Add Product",
            receiveStock: "Receive Stock",
            receptionHistory: "Reception History",
            resetSoldTags: "Reset sold RFID tags",
            product: "Product",
            category: "Category",
            price: "Price",
            producer: "Producer",
            inStock: "In Stock",
            actions: "Actions",
            edit: "Edit",
            delete: "Delete",
            noProducts: "No products in inventory",
            deleteConfirm: "Are you sure you want to delete this product?",
            footer: "Smart shopping, better rewards"
        },

        // French translations
        fr: {
            dashboard: "Tableau de bord",
            history: "Historique des achats",
            checkoutLink: "Caisse libre-service",
            inventoryLink: "Inventaire",
            logout: "Déconnexion",
            backAccounts: "← Retour aux comptes clients",
            productManagement: "GESTION DES PRODUITS",
            inventoryTitle: "Inventaire",
            inventoryDesc: "Gérez les produits, les quantités en stock et les livraisons",
            addProduct: "Ajouter un produit",
            receiveStock: "Réceptionner du stock",
            receptionHistory: "Historique des réceptions",
            resetSoldTags: "Réinitialiser les étiquettes RFID vendues",
            product: "Produit",
            category: "Catégorie",
            price: "Prix",
            producer: "Fabricant",
            inStock: "En stock",
            actions: "Actions",
            edit: "Modifier",
            delete: "Supprimer",
            noProducts: "Aucun produit dans l'inventaire",
            deleteConfirm: "Voulez-vous vraiment supprimer ce produit ?",
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

        // Highlight selected language
        document.getElementById("lang-en").classList.toggle(
            "selected", storeLanguage === "en"
        );

        document.getElementById("lang-fr").classList.toggle(
            "selected", storeLanguage === "fr"
        );
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

    // Confirm before deleting product
    document.querySelectorAll(".delete-form").forEach(form => {
        form.addEventListener("submit", event => {

            // Ask customer to confirm deletion
            const confirmed = confirm(
                storeTranslations[storeLanguage].deleteConfirm
            );

            // Cancel deletion if customer clicks Cancel
            if (!confirmed) {
                event.preventDefault();
            }
        });
    });

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

    // Start inventory translation and navigation
    changeStoreLanguage(storeLanguage);
    checkStoreLogin();
