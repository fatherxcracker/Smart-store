
/*
 Smart Store Phase 3
 This JavaScript file makes the customer account website work
 It handles:
 1. Changing between pages
 2. English and French translations
 3. Creating customer accounts
 4. Logging in
 5. Displaying customer information
 6. Showing loyalty points
 7. Purchase history and receipts
 8. Logging out
*/

// Get html elements

// Find the registration form in account.html
const registerForm = document.getElementById("register-form");

// Find the login form
const loginForm = document.getElementById("login-form");

// Find the area where notifications appear
const message = document.getElementById("message");


// Website settings

// These are the 4 pages in our customer account website
const pages = ["login", "register", "dashboard", "history"];

// The website starts on the login page
let currentPage = "login";

// Remember the customer's chosen language
// localStorage saves the language in the browser
// If no language was saved use English
let currentLanguage = localStorage.getItem("smartstore-language") || "en";

// At first the customer is not logged in
let loggedIn = false;


// English and french translations

// object stores the text for both languages
// en = English
// fr = French
// Each word has a key like signIn
// JavaScript uses that key to find the correct translation
const translations = {

    // English translations
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
        backDashboard: "← Back to Dashboard",
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

    // French translations
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
        backDashboard: "← Retour au tableau de bord",
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


// Translation function

// Gets the correct translation for a word
// Example: t("signIn") returns Sign in or Se connecter
function t(key) {
    return translations[currentLanguage][key] || key;
}


// Change language

function changeLanguage(lang) {

    // Change the current language
    currentLanguage = translations[lang] ? lang : "en";

    // Save chosen language in the browser
    // This remembers it after refreshing the website
    localStorage.setItem("smartstore-language", currentLanguage);
    if (loggedIn) {
        api("/api/account/language", "POST", { language: currentLanguage })
            .catch(error => { message.textContent = error.message; });
    }

    // Update the language attribute of the HTML page
    document.documentElement.lang = currentLanguage;

    // Find every html element with data-i18n
    // Replace its text with the wanted translation
    document.querySelectorAll("[data-i18n]").forEach(element => {
        const key = element.dataset.i18n;
        element.textContent = t(key);
    });

    // Highlight the EN button when English is chosen
    document.getElementById("lang-en").classList.toggle(
        "selected", currentLanguage === "en"
    );

    // Highlight the FR button when French is selected
    document.getElementById("lang-fr").classList.toggle(
        "selected", currentLanguage === "fr"
    );

    // If the customer is seeing purchase history reload it in the new language
    if (loggedIn && currentPage === "history") {
        showHistory();
    }
}

// When customer clicks EN switch to English
document.getElementById("lang-en").addEventListener("click", () => {
    changeLanguage("en");
});

// When customer clicks FR switch to French
document.getElementById("lang-fr").addEventListener("click", () => {
    changeLanguage("fr");
});


// Page navigation

// This function displays only one page at a time
// Example: showPage("register") displays the registration page
function showPage(page) {

    // Stop if the page name is not valid
    if (!pages.includes(page)) return;

    // Customers who are not logged in cannot see the dashboard or purchase history
    if (!loggedIn && (page === "dashboard" || page === "history")) {
        page = "login";
    }

    // Logged-in customers are sent to the dashboard instead of login or register
    if (loggedIn && (page === "login" || page === "register")) {
        page = "dashboard";
    }

    // Remember which page is displayed right now
    currentPage = page;

    // Hide all pages except selected page
    // Each page has an ID like login-page or history-page
    pages.forEach(name => {
        document.getElementById(name + "-page").hidden = name !== page;
    });

    // Show navigation and logout only when logged in
    document.getElementById("account-nav").hidden = !loggedIn;
    document.getElementById("logout-button").hidden = !loggedIn;

    // Highlight the selected navigation button
    document.querySelectorAll(".nav-link").forEach(button => {
        button.classList.toggle(
            "active", button.dataset.page === page
        );
    });

    // Load purchase history when opening that page
    if (page === "history") {
        showHistory();
    }

    // Clear old notification messages
    message.textContent = "";
}


// Find every button with data-page
// Example: data-page="register" means open the registration page
document.querySelectorAll("[data-page]").forEach(button => {
    button.addEventListener("click", () => {

        // Open the page selected by the customer
        showPage(button.dataset.page);
    });
});


// Handle links from other pages

// Read the page name from the URL
// Example: /#history means open Purchase History
function openRequestedPage() {

    const requestedPage = window.location.hash.replace("#", "");

    // Only open Dashboard or Purchase History when logged in
    if (loggedIn && (requestedPage === "dashboard" || requestedPage === "history")) {
        showPage(requestedPage);
    }
}

// When URL changes open the requested page
window.addEventListener("hashchange", openRequestedPage);


// connect javascript to flask

// This function sends HTTP requests to our Flask backend
// GET = retrieve information
// POST = send information
// async means the function can wait for a response without freezing the website
async function api(url, method = "GET", data = null) {

    // Set up the HTTP request
    const options = {
        method: method,

        // Include the browser's session cookie
        // Flask uses it to identify the logged-in customer
        credentials: "same-origin",

        // Tell Flask we are sending JSON
        headers: {
            "Content-Type": "application/json"
        }
    };

    // If there is data convert it into JSON text
    if (data !== null) {
        options.body = JSON.stringify(data);
    }

    let response;

    try {
        // fetch sends the request to Flask
        // await waits for the server to respond
        response = await fetch(url, options);

    } catch (error) {
        // Show an error if the server cannot be reached
        throw new Error(t("requestFailed"));
    }

    // Convert Flask's JSON response into a JavaScript object
    const result = await response.json();

    // response.ok is true for successful HTTP responses
    if (!response.ok) {

        // HTTP 401 during login means invalid credentials
        if (url.includes("/login") && response.status === 401) {
            throw new Error(t("loginFailed"));
        }

        // Show the error returned by Flask
        throw new Error(result.message || result.error || t("requestFailed"));
    }

    // Return the data received from Flask
    return result;
}


// Register costumer

// This runs when the customer submits the registration form
registerForm.addEventListener("submit", async event => {

    // Stop the browser from refreshing the page
    event.preventDefault();

    // Collect all registration form fields
    // Object.fromEntries converts form values into an object
    const data = Object.fromEntries(new FormData(registerForm));

    // Include the selected language in the registration data
    data.language = currentLanguage;

    try {
        // Send customer information to Flask using POST
        // Flask route: /api/account/register
        // Python function: register()
        const result = await api("/api/account/register", "POST", data);

        // Clear the form after successful registration
        registerForm.reset();

        // Display the success notification
        message.textContent = result.message || t("accountCreated");

        // Load the newly created customer account
        await loadAccount();

    } catch (error) {
        // Display an error if registration fails
        message.textContent = error.message;
    }
});


// Login customer

// This runs when the customer submits the login form
loginForm.addEventListener("submit", async event => {

    // Prevent the browser from refreshing
    event.preventDefault();

    // Get the email and password from the form
    const data = Object.fromEntries(new FormData(loginForm));

    try {
        // Send login information to Flask
        // Flask route: /api/account/login
        // Python function: login()
        await api("/api/account/login", "POST", data);

        // Clear the login form
        loginForm.reset();

        // Load the customer's account after successful login
        await loadAccount();

    } catch (error) {
        // Display an error if the login fails
        message.textContent = error.message;
    }
});


// Load customer account

// This function gets customer information from Flask and displays it on the dashboard
async function loadAccount() {

    try {
        // Ask Flask for the logged-in customer's information
        // Flask route: /api/account/me
        const customer = await api("/api/account/me");

        // Customer is now logged in
        loggedIn = true;

        // Display the customer's name in the welcome message
        document.getElementById("welcome-name").textContent = customer.name;

        // Display the name on the membership card
        document.getElementById("card-name").textContent = customer.name;

        // Display the name in the profile section
        document.getElementById("customer-name").textContent = customer.name;

        // Display the customer's email
        document.getElementById("customer-email").textContent = customer.email;

        // Display the membership number generated by the database
        document.getElementById("membership-number").textContent = customer.membership_number;

        // Display the customer's loyalty points
        document.getElementById("customer-points").textContent = customer.points;

        // Open the dashboard after loading customer information
        showPage("dashboard");

        // Open Purchase History if customer came from another page
        openRequestedPage();

    } catch (error) {

        // If customer information cannot be loaded return to the login page
        loggedIn = false;
        showPage("login");
    }
}


// Purchase history

// This function gets the customer's purchases and displays them in the history page
async function showHistory() {

    // Find the purchase history container in html
    const container = document.getElementById("purchase-history");

    // Remove old purchase history content
    container.replaceChildren();

    // Show Loading while waiting for Flask
    container.textContent = t("loading");

    try {
        // Ask Flask for the customer's purchase history
        // Flask route: /api/account/history
        const purchases = await api("/api/account/history");

        // Clear the loading message
        container.replaceChildren();

        // If there are no purchases display a message
        if (purchases.length === 0) {

            const empty = document.createElement("p");
            empty.classList.add("empty-purchase-history");
            empty.textContent = t("noPurchases");

            container.appendChild(empty);
            return;
        }

        // Go through every purchase returned by Flask
        for (const purchase of purchases) {

            // Create a row for one purchase
            const row = document.createElement("div");
            row.className = "history-row";

            // Display the receipt number
            const receiptNumber = document.createElement("strong");
            receiptNumber.textContent = purchase.receipt_number;

            // Display the purchase date and time
            const date = document.createElement("span");

            // Database stores UTC time
            // Convert it into customer's local time
            date.textContent = new Date(
                purchase.created_at.replace(" ", "T") + "Z"
            ).toLocaleString(currentLanguage === "fr" ? "fr-CA" : "en-CA", {
                dateStyle: "medium",
                timeStyle: "short"
            });

            // Display total price with two decimal places
            // Example: 25 becomes $25.00
            const total = document.createElement("span");
            total.textContent = "$" + Number(purchase.total).toFixed(2);

            // Display loyalty points earned from this purchase
            const points = document.createElement("span");
            points.textContent = "+" + purchase.points_earned;

            // Create a button to view the receipt
            const button = document.createElement("button");
            button.textContent = t("viewReceipt");

            // Create a hidden area for receipt details
            const details = document.createElement("div");
            details.className = "receipt-details";
            details.hidden = true;

            // This runs when customer clicks View receipt
            button.addEventListener("click", async () => {

                // If the receipt is already open close it
                if (!details.hidden) {
                    details.hidden = true;
                    button.textContent = t("viewReceipt");
                    return;
                }

                try {
                    // Ask Flask for this purchase's receipt
                    // Example: /api/account/receipt/5
                    const receipt = await api(
                        "/api/account/receipt/" + purchase.id
                    );

                    // Remove any previous receipt details
                    details.replaceChildren();

                    // Create a list for the purchased products
                    const list = document.createElement("ul");

                    // Add each purchased product to the list
                    for (const item of receipt.items) {

                        const li = document.createElement("li");

                        // Show product name quantity and price
                        li.textContent =
                            item.product_name + " × " + item.quantity +
                            " — $" + Number(item.line_total).toFixed(2);

                        list.appendChild(li);
                    }

                    // Display the receipt list
                    details.appendChild(list);

                    // Make the receipt visible
                    details.hidden = false;

                    // Change the button text to Close receipt
                    button.textContent = t("closeReceipt");

                } catch (error) {
                    // Display an error if the receipt cannot load
                    message.textContent = error.message;
                }
            });

            // Add the receipt information to the purchase row
            row.append(
                receiptNumber, date, total, points, button
            );

            // Add the row and receipt details to the html page
            container.appendChild(row);
            container.appendChild(details);
        }

    } catch (error) {
        // Display an error if purchase history cannot load
        container.textContent = error.message;
    }
}


// Logout customer

// Find the logout button and listen for clicks
document.getElementById("logout-button")
    .addEventListener("click", async () => {

        try {
            // Tell Flask to log out the customer
            // Flask route: /api/account/logout
            await api("/api/account/logout", "POST");

            // Customer is no longer logged in
            loggedIn = false;

            // Remove requested page from URL
            window.history.replaceState(
                null,
                "",
                window.location.pathname + window.location.search
            );

            // Return to the login page
            showPage("login");

            // Display the logout notification
            message.textContent = t("loggedOut");

        } catch (error) {
            // Display an error if logout fails
            message.textContent = error.message;
        }
    });


// Start the website

// Apply the saved language
changeLanguage(currentLanguage);

// Check if customer is already logged in
// If logged in show dashboard or requested purchase history
// Otherwise show login page
loadAccount();
