// User management pages: translation, navigation, logout and confirmations

let usersLanguage = localStorage.getItem("smartstore-language") === "fr" ? "fr" : "en";

const usersTranslations = {
    en: {
        dashboard: "Dashboard",
        history: "Purchase History",
        checkoutLink: "Self-checkout",
        inventoryLink: "Inventory",
        usersLink: "Users",
        logout: "Log Out",
        backInventory: "← Back to Inventory",
        backUsers: "← Back to Users",
        storeAdmin: "STORE ADMINISTRATION",
        usersTitle: "User Management",
        usersDesc: "See every account in the store, edit details, points and roles",
        statUsers: "accounts",
        statAdmins: "administrators",
        searchPlaceholder: "Search by name, email, phone or membership number",
        search: "Search",
        clearSearch: "Clear",
        addUser: "+ Add user",
        name: "Name",
        email: "Email",
        phoneOptional: "Phone (optional)",
        tempPassword: "Temporary password (6+ characters)",
        receiptLanguage: "Receipt language",
        makeAdmin: "Administrator",
        createAccount: "Create account",
        membership: "Membership #",
        points: "Points",
        purchases: "Purchases",
        spent: "Total spent",
        joined: "Joined",
        actions: "Actions",
        manage: "Manage",
        adminBadge: "Admin",
        youBadge: "You",
        noUsers: "No accounts found",
        memberSince: "Member since",
        profile: "Profile",
        saveChanges: "Save changes",
        loyaltyPoints: "Loyalty points",
        pointsHelp: "Set the balance directly, e.g. to correct a mistake.",
        pointsBalance: "Points balance",
        savePoints: "Save points",
        password: "Password",
        passwordHelp: "Give the customer a new temporary password.",
        newPassword: "New password (6+ characters)",
        resetPassword: "Reset password",
        role: "Role",
        isAdminText: "Administrator: can manage products, stock, tags and users.",
        isCustomerText: "Customer: can shop and see their own account.",
        grantAdmin: "Make administrator",
        removeAdmin: "Remove administrator access",
        deleteAccount: "Delete account",
        selfNote: "This is your account. Another administrator must change your role or delete it.",
        purchaseHistory: "Purchase history",
        receipt: "Receipt",
        date: "Date",
        items: "Items",
        total: "Total",
        pointsEarned: "Points earned",
        pointsUsed: "Points used",
        emailed: "Emailed",
        noPurchases: "No purchases yet",
        footer: "Smart shopping, better rewards",
        confirmMakeAdmin: "Give this account administrator access?",
        confirmRemoveAdmin: "Remove administrator access from this account?",
        confirmDeleteUser: "Delete this account? Their receipts are kept as guest receipts. This can't be undone.",
        logoutFailed: "Could not log out"
    },
    fr: {
        dashboard: "Tableau de bord",
        history: "Historique des achats",
        checkoutLink: "Caisse libre-service",
        inventoryLink: "Inventaire",
        usersLink: "Utilisateurs",
        logout: "Déconnexion",
        backInventory: "← Retour à l'inventaire",
        backUsers: "← Retour aux utilisateurs",
        storeAdmin: "ADMINISTRATION DU MAGASIN",
        usersTitle: "Gestion des utilisateurs",
        usersDesc: "Consultez tous les comptes du magasin et modifiez les informations, les points et les rôles",
        statUsers: "comptes",
        statAdmins: "administrateurs",
        searchPlaceholder: "Rechercher par nom, courriel, téléphone ou numéro de membre",
        search: "Rechercher",
        clearSearch: "Effacer",
        addUser: "+ Ajouter un utilisateur",
        name: "Nom",
        email: "Courriel",
        phoneOptional: "Téléphone (facultatif)",
        tempPassword: "Mot de passe temporaire (6 caractères ou plus)",
        receiptLanguage: "Langue des reçus",
        makeAdmin: "Administrateur",
        createAccount: "Créer le compte",
        membership: "No de membre",
        points: "Points",
        purchases: "Achats",
        spent: "Total dépensé",
        joined: "Inscription",
        actions: "Actions",
        manage: "Gérer",
        adminBadge: "Admin",
        youBadge: "Vous",
        noUsers: "Aucun compte trouvé",
        memberSince: "Membre depuis",
        profile: "Profil",
        saveChanges: "Enregistrer",
        loyaltyPoints: "Points de fidélité",
        pointsHelp: "Modifiez le solde directement, par exemple pour corriger une erreur.",
        pointsBalance: "Solde de points",
        savePoints: "Enregistrer les points",
        password: "Mot de passe",
        passwordHelp: "Donnez au client un nouveau mot de passe temporaire.",
        newPassword: "Nouveau mot de passe (6 caractères ou plus)",
        resetPassword: "Réinitialiser le mot de passe",
        role: "Rôle",
        isAdminText: "Administrateur : peut gérer les produits, le stock, les étiquettes et les utilisateurs.",
        isCustomerText: "Client : peut magasiner et consulter son propre compte.",
        grantAdmin: "Nommer administrateur",
        removeAdmin: "Retirer l'accès administrateur",
        deleteAccount: "Supprimer le compte",
        selfNote: "C'est votre compte. Un autre administrateur doit modifier votre rôle ou le supprimer.",
        purchaseHistory: "Historique des achats",
        receipt: "Reçu",
        date: "Date",
        items: "Articles",
        total: "Total",
        pointsEarned: "Points gagnés",
        pointsUsed: "Points utilisés",
        emailed: "Envoyé",
        noPurchases: "Aucun achat pour le moment",
        footer: "Magasinez mieux, gagnez plus",
        confirmMakeAdmin: "Donner l'accès administrateur à ce compte?",
        confirmRemoveAdmin: "Retirer l'accès administrateur de ce compte?",
        confirmDeleteUser: "Supprimer ce compte? Ses reçus sont conservés comme reçus d'invité. Cette action est irréversible.",
        logoutFailed: "Impossible de se déconnecter"
    }
};

function usersText(key) {
    return usersTranslations[usersLanguage][key] || usersTranslations.en[key] || key;
}

function changeUsersLanguage(language) {
    usersLanguage = language === "fr" ? "fr" : "en";
    localStorage.setItem("smartstore-language", usersLanguage);
    document.documentElement.lang = usersLanguage;

    document.querySelectorAll("[data-i18n]").forEach(element => {
        const key = element.dataset.i18n;
        if (usersTranslations[usersLanguage][key]) element.textContent = usersText(key);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach(element => {
        element.placeholder = usersText(element.dataset.i18nPlaceholder);
    });

    document.getElementById("lang-en").classList.toggle("selected", usersLanguage === "en");
    document.getElementById("lang-fr").classList.toggle("selected", usersLanguage === "fr");
}

document.getElementById("lang-en").addEventListener("click", () => changeUsersLanguage("en"));
document.getElementById("lang-fr").addEventListener("click", () => changeUsersLanguage("fr"));

// Admin forms: confirm risky actions and tell Flask which language to answer in
document.querySelectorAll(".admin-form").forEach(form => {
    form.addEventListener("submit", event => {
        const languageInput = form.querySelector('input[name="language"]');
        if (languageInput) languageInput.value = usersLanguage;

        const key = form.dataset.confirm;
        if (key && !confirm(usersText(key))) event.preventDefault();
    });
});

// Show Dashboard / Purchase History / Log Out (the admin is logged in)
async function checkUsersLogin() {
    try {
        const response = await fetch("/api/account/me", { credentials: "same-origin" });
        document.getElementById("account-nav").hidden = !response.ok;
        document.getElementById("logout-button").hidden = !response.ok;
    } catch {
        document.getElementById("account-nav").hidden = true;
        document.getElementById("logout-button").hidden = true;
    }
}

document.getElementById("logout-button").addEventListener("click", async () => {
    try {
        const response = await fetch("/api/account/logout", { method: "POST", credentials: "same-origin" });
        if (!response.ok) throw new Error();
        window.location.href = document.body.dataset.homeUrl;
    } catch {
        alert(usersText("logoutFailed"));
    }
});

// Purchase history: click a receipt number to show / hide that receipt
document.querySelectorAll(".receipt-toggle").forEach(button => {
    button.addEventListener("click", () => {
        const row = document.getElementById(button.getAttribute("aria-controls"));
        row.hidden = !row.hidden;
        button.setAttribute("aria-expanded", String(!row.hidden));
    });
});

changeUsersLanguage(usersLanguage);
checkUsersLogin();
