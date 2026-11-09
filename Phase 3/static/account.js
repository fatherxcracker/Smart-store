
/*
 Smart Store Phase 3
 Customer accounts + page navigation + EN/FR translation
*/

const registerForm = document.getElementById("register-form");
const loginForm = document.getElementById("login-form");
const message = document.getElementById("message");

const pages = ["login", "register", "dashboard", "history"];
let currentPage = "login";
let currentLanguage = localStorage.getItem("smartstore-language") || "en";
let loggedIn = false;

// Translations for the entire customer account interface
const translations = {
    en: {
        portal: "Customer Portal",
        dashboard: "Dashboard",
        history: "Purchase History",
        logout: "Log Out",
        welcomeBack: "WELCOME BACK",
        welcomeTitle: "Shopping made smarter.",
        welcomeDesc: "Access your membership, track rewards, and view your shopping history.",
        memberAccess: "MEMBER ACCESS",
        signIn: "Sign in",
        signInDesc: "Enter your details to access your account.",
        email: "Email address",
        password: "Password",
        noAccount: "Don't have an account?",
        createOne: "Create one",
        joinStore: "JOIN SMART STORE",
        registerTitle: "More rewards. Every visit.",
        registerDesc: "Create an account and receive your own membership number.",
        createAccount: "Create account",
        registerSubtitle: "Join our loyalty program today.",
        fullName: "Full name",
        phone: "Phone (optional)",
        haveAccount: "Already have an account?",
        overview: "ACCOUNT OVERVIEW",
        hello: "Hello",
        dashboardDesc: "Here's your Smart Store membership.",
        memberCard: "MEMBERSHIP CARD",
        memberNumber: "MEMBER NUMBER",
        loyaltyPoints: "LOYALTY POINTS",
        pointsDesc: "Earn 1 point for every full dollar spent before tax.",
        profile: "MY PROFILE",
        yourPurchases: "Your purchases",
        purchaseDesc: "View receipts and track points earned.",
        viewHistory: "View purchase history",
        activity: "ACCOUNT ACTIVITY",
        purchaseHistory: "Purchase History",
        historyDesc: "Your previous Smart Store receipts.",
        backDashboard: "Back to dashboard",
        receipt: "Receipt",
        date: "Date",
        total: "Total",
        earned: "Points earned",
        footer: "Smart shopping, better rewards.",
        noPurchases: "No purchases yet.",
        viewReceipt: "View receipt",
        closeReceipt: "Close receipt",
        loginRequired: "Please log in.",
        accountCreated: "Account created successfully!",
        loginSuccess: "Login successful!",
        loginFailed: "Incorrect email or password.",
        loggedOut: "You have been logged out.",
        requestFailed: "Something went wrong. Please try again.",
        receiptNotFound: "Receipt not found.",
        loading: "Loading...",
        featureOne: "Your digital membership card",
        featureTwo: "Earn rewards on every purchase",
        featureThree: "All your receipts in one place",
        checkoutLink: "Self-checkout",
        inventoryLink: "Inventory",
    },

    fr: {
        portal: "Portail client",
        dashboard: "Tableau de bord",
        history: "Historique des achats",
        logout: "Déconnexion",
        welcomeBack: "BON RETOUR",
        welcomeTitle: "Magasinez plus intelligemment.",
        welcomeDesc: "Accédez à votre carte de membre, à vos récompenses et à votre historique d'achats.",
        memberAccess: "ESPACE MEMBRE",
        signIn: "Se connecter",
        signInDesc: "Entrez vos informations pour accéder à votre compte.",
        email: "Adresse courriel",
        password: "Mot de passe",
        noAccount: "Vous n'avez pas de compte ?",
        createOne: "Créer un compte",
        joinStore: "REJOIGNEZ SMART STORE",
        registerTitle: "Plus de récompenses à chaque visite.",
        registerDesc: "Créez un compte et obtenez votre numéro de membre.",
        createAccount: "Créer un compte",
        registerSubtitle: "Inscrivez-vous à notre programme de fidélité.",
        fullName: "Nom complet",
        phone: "Téléphone (facultatif)",
        haveAccount: "Vous avez déjà un compte ?",
        overview: "APERÇU DU COMPTE",
        hello: "Bonjour",
        dashboardDesc: "Voici votre compte Smart Store.",
        memberCard: "CARTE DE MEMBRE",
        memberNumber: "NUMÉRO DE MEMBRE",
        loyaltyPoints: "POINTS DE FIDÉLITÉ",
        pointsDesc: "Gagnez 1 point par dollar entier dépensé avant taxes.",
        profile: "MON PROFIL",
        yourPurchases: "Vos achats",
        purchaseDesc: "Consultez vos reçus et vos points gagnés.",
        viewHistory: "Voir l'historique des achats",
        activity: "ACTIVITÉ DU COMPTE",
        purchaseHistory: "Historique des achats",
        historyDesc: "Vos reçus Smart Store précédents.",
        backDashboard: "Retour au tableau de bord",
        receipt: "Reçu",
        date: "Date",
        total: "Total",
        earned: "Points gagnés",
        footer: "Magasinez mieux, gagnez plus.",
        noPurchases: "Aucun achat pour le moment.",
        viewReceipt: "Voir le reçu",
        closeReceipt: "Fermer le reçu",
        loginRequired: "Veuillez vous connecter.",
        accountCreated: "Compte créé avec succès !",
        loginSuccess: "Connexion réussie !",
        loginFailed: "Courriel ou mot de passe incorrect.",
        loggedOut: "Vous êtes déconnecté.",
        requestFailed: "Une erreur est survenue. Veuillez réessayer.",
        receiptNotFound: "Reçu introuvable.",
        loading: "Chargement...",
        featureOne: "Votre carte de membre numérique",
        featureTwo: "Gagnez des récompenses à chaque achat",
        featureThree: "Tous vos reçus au même endroit",
        checkoutLink: "Caisse libre-service",
        inventoryLink: "Inventaire",
    }
};

function t(key) {
    return translations[currentLanguage][key] || key;
}

// Apply language to all translated elements
function changeLanguage(lang) {
    currentLanguage = lang;
    localStorage.setItem("smartstore-language", lang);
    document.documentElement.lang = lang;

    document.querySelectorAll("[data-i18n]").forEach(element => {
        const key = element.dataset.i18n;
        element.textContent = t(key);
    });

    document.getElementById("lang-en").classList.toggle(
        "selected", lang === "en"
    );
    document.getElementById("lang-fr").classList.toggle(
        "selected", lang === "fr"
    );

    if (loggedIn && currentPage === "history") {
        showHistory();
    }
}

document.getElementById("lang-en").addEventListener("click", () => {
    changeLanguage("en");
});

document.getElementById("lang-fr").addEventListener("click", () => {
    changeLanguage("fr");
});

// Display only the selected page
function showPage(page) {
    if (!pages.includes(page)) return;

    if (!loggedIn && (page === "dashboard" || page === "history")) {
        page = "login";
    }

    if (loggedIn && (page === "login" || page === "register")) {
        page = "dashboard";
    }

    currentPage = page;

    pages.forEach(name => {
        document.getElementById(name + "-page").hidden = name !== page;
    });

    document.getElementById("account-nav").hidden = !loggedIn;
    document.getElementById("logout-button").hidden = !loggedIn;

    document.querySelectorAll(".nav-link").forEach(button => {
        button.classList.toggle(
            "active", button.dataset.page === page
        );
    });

    if (page === "history") {
        showHistory();
    }

    message.textContent = "";
}

document.querySelectorAll("[data-page]").forEach(button => {
    button.addEventListener("click", () => {
        showPage(button.dataset.page);
    });
});

// API requests to Flask
async function api(url, method = "GET", data = null) {
    const options = {
        method: method,
        credentials: "same-origin",
        headers: {
            "Content-Type": "application/json"
        }
    };

    if (data !== null) {
        options.body = JSON.stringify(data);
    }

    let response;

    try {
        response = await fetch(url, options);
    } catch (error) {
        throw new Error(t("requestFailed"));
    }

    const result = await response.json();

    if (!response.ok) {
        if (url.includes("/login") && response.status === 401) {
            throw new Error(t("loginFailed"));
        }

        throw new Error(result.message || result.error || t("requestFailed"));
    }

    return result;
}

// REGISTER
registerForm.addEventListener("submit", async event => {
    event.preventDefault();

    const data = Object.fromEntries(new FormData(registerForm));
    data.language = currentLanguage;

    try {
        const result = await api("/api/account/register", "POST", data);

        registerForm.reset();
        message.textContent = result.message || t("accountCreated");

        await loadAccount();

    } catch (error) {
        message.textContent = error.message;
    }
});

// LOGIN
loginForm.addEventListener("submit", async event => {
    event.preventDefault();

    const data = Object.fromEntries(new FormData(loginForm));

    try {
        await api("/api/account/login", "POST", data);
        loginForm.reset();

        await loadAccount();

    } catch (error) {
        message.textContent = error.message;
    }
});

// Load the customer's profile
async function loadAccount() {
    try {
        const customer = await api("/api/account/me");

        loggedIn = true;

        document.getElementById("welcome-name").textContent =
            customer.name;

        document.getElementById("card-name").textContent =
            customer.name;

        document.getElementById("customer-name").textContent =
            customer.name;

        document.getElementById("customer-email").textContent =
            customer.email;

        document.getElementById("membership-number").textContent =
            customer.membership_number;

        document.getElementById("customer-points").textContent =
            customer.points;

        showPage("dashboard");

    } catch (error) {
        loggedIn = false;
        showPage("login");
    }
}

// Purchase history
async function showHistory() {
    const container = document.getElementById("purchase-history");
    container.replaceChildren();
    container.textContent = t("loading");

    try {
        const purchases = await api("/api/account/history");
        container.replaceChildren();

        if (purchases.length === 0) {
            const empty = document.createElement("p");
            empty.style.padding = "24px";
            empty.textContent = t("noPurchases");
            container.appendChild(empty);
            return;
        }

        for (const purchase of purchases) {
            const row = document.createElement("div");
            row.className = "history-row";

            const receiptNumber = document.createElement("strong");
            receiptNumber.textContent = purchase.receipt_number;

            const date = document.createElement("span");
            // The database stores UTC; show it in the customer's local time.
            date.textContent = new Date(
                purchase.created_at.replace(" ", "T") + "Z"
            ).toLocaleString(currentLanguage === "fr" ? "fr-CA" : "en-CA", {
                dateStyle: "medium",
                timeStyle: "short"
            });

            const total = document.createElement("span");
            total.textContent = "$" + Number(purchase.total).toFixed(2);

            const points = document.createElement("span");
            points.textContent = "+" + purchase.points_earned;

            const button = document.createElement("button");
            button.textContent = t("viewReceipt");

            const details = document.createElement("div");
            details.className = "receipt-details";
            details.hidden = true;

            button.addEventListener("click", async () => {
                if (!details.hidden) {
                    details.hidden = true;
                    button.textContent = t("viewReceipt");
                    return;
                }

                try {
                    const receipt = await api(
                        "/api/account/receipt/" + purchase.id
                    );

                    details.replaceChildren();

                    const list = document.createElement("ul");

                    for (const item of receipt.items) {
                        const li = document.createElement("li");
                        li.textContent =
                            item.product_name + " × " + item.quantity +
                            " — $" + Number(item.line_total).toFixed(2);
                        list.appendChild(li);
                    }

                    details.appendChild(list);
                    details.hidden = false;
                    button.textContent = t("closeReceipt");

                } catch (error) {
                    message.textContent = error.message;
                }
            });

            row.append(
                receiptNumber, date, total, points, button
            );

            container.appendChild(row);
            container.appendChild(details);
        }

    } catch (error) {
        container.textContent = error.message;
    }
}

// LOGOUT
document.getElementById("logout-button")
    .addEventListener("click", async () => {
        try {
            await api("/api/account/logout", "POST");
            loggedIn = false;
            showPage("login");
            message.textContent = t("loggedOut");
        } catch (error) {
            message.textContent = error.message;
        }
    });

// Initialize the website
changeLanguage(currentLanguage);
loadAccount();
