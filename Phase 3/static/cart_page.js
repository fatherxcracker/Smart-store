// Translates the checkout page and updates account navigation

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
            smartShopping: "SMART SHOPPING",
            checkoutTitle: "Self-checkout",
            checkoutDesc: "Scan your products and complete your purchase",
            scanProducts: "Scan Products",
            scanDesc: "Scan an RFID tag or enter a product barcode",
            scanRFID: "Scan RFID",
            autoScan: "Auto Scan",
            productBarcode: "Product Barcode",
            barcodePlaceholder: "Scan or enter barcode",
            addProduct: "Add Product",
            shoppingCart: "Shopping Cart",
            cartDesc: "Review the products added to your cart",
            product: "Product",
            quantity: "Quantity",
            price: "Price",
            total: "Total",
            actions: "Actions",
            orderSummary: "Order Summary",
            summaryDesc: "Review your total before paying",
            subtotal: "Subtotal",
            gst: "GST (5%)",
            qst: "QST (9.975%)",
            membershipNumber: "Membership Number (optional)",
            membershipPlaceholder: "Enter membership number",
            paymentMethod: "Payment Method",
            selectPayment: "Select payment method",
            creditCard: "Credit Card",
            debitCard: "Debit Card",
            cash: "Cash",
            completePurchase: "Complete Purchase",
            resetCart: "Reset Cart",
            purchaseReceipt: "Purchase Receipt",
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
            smartShopping: "MAGASINAGE INTELLIGENT",
            checkoutTitle: "Caisse libre-service",
            checkoutDesc: "Numérisez vos produits et terminez votre achat",
            scanProducts: "Numériser les produits",
            scanDesc: "Numérisez une étiquette RFID ou entrez un code-barres",
            scanRFID: "Numériser RFID",
            autoScan: "Numérisation automatique",
            productBarcode: "Code-barres du produit",
            barcodePlaceholder: "Numérisez ou entrez le code-barres",
            addProduct: "Ajouter un produit",
            shoppingCart: "Panier",
            cartDesc: "Vérifiez les produits ajoutés à votre panier",
            product: "Produit",
            quantity: "Quantité",
            price: "Prix",
            total: "Total",
            actions: "Actions",
            orderSummary: "Résumé de la commande",
            summaryDesc: "Vérifiez le total avant de payer",
            subtotal: "Sous-total",
            gst: "TPS (5 %)",
            qst: "TVQ (9,975 %)",
            membershipNumber: "Numéro de membre (facultatif)",
            membershipPlaceholder: "Entrez votre numéro de membre",
            paymentMethod: "Mode de paiement",
            selectPayment: "Sélectionnez un mode de paiement",
            creditCard: "Carte de crédit",
            debitCard: "Carte de débit",
            cash: "Comptant",
            completePurchase: "Terminer l'achat",
            resetCart: "Vider le panier",
            purchaseReceipt: "Reçu d'achat",
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

        // Translate iframe title
        document.querySelectorAll("[data-i18n-title]").forEach(element => {
            const key = element.dataset.i18nTitle;

            if (storeTranslations[storeLanguage][key]) {
                element.title =
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
                ? "Caisse libre-service | Smart Store"
                : "Self-checkout | Smart Store";

        // Tell other JavaScript that the language changed
        // cart.js can listen for this event to translate dynamic messages
        window.dispatchEvent(
            new CustomEvent("smartstore-language-change", {
                detail: { language: storeLanguage }
            })
        );
    }

    async function saveStoreLanguage() {
        try {
            const response = await fetch("/api/account/language", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ language: storeLanguage })
            });
            // Guests keep their language in this browser only.
            if (!response.ok && response.status !== 401) throw new Error();
        } catch {
            showMessage(storeLanguage === "fr"
                ? "La préférence de langue n'a pas pu être enregistrée."
                : "Could not save your language preference.", "error");
        }
    }

    // English button
    document.getElementById("lang-en").addEventListener("click", () => {
        changeStoreLanguage("en");
        saveStoreLanguage();
    });

    // French button
    document.getElementById("lang-fr").addEventListener("click", () => {
        changeStoreLanguage("fr");
        saveStoreLanguage();
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

    // Start checkout translation and navigation
    changeStoreLanguage(storeLanguage);
    checkStoreLogin();
