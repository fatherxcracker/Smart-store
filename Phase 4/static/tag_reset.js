// RFID tag reset / remove buttons (Inventory and RFID Tags pages).
// Asks for confirmation in the selected language and tells Flask which
// language to use for the notification.

const tagResetMessages = {
    en: {
        confirmResetAll: "Make every sold RFID tag in the store available again?\n\nOld receipts and the Sold / In stock numbers don't change. Click Reset cart on the self-checkout page afterwards.",
        confirmResetProduct: "Make all sold tags of this product available again?",
        confirmRemoveTag: "Remove this tag from the product? You can assign it again afterwards."
    },
    fr: {
        confirmResetAll: "Rendre de nouveau disponibles toutes les étiquettes RFID vendues du magasin?\n\nLes anciens reçus et les quantités vendues / en stock ne changent pas. Cliquez ensuite sur « Réinitialiser le panier » à la caisse libre-service.",
        confirmResetProduct: "Rendre de nouveau disponibles toutes les étiquettes vendues de ce produit?",
        confirmRemoveTag: "Retirer cette étiquette du produit? Vous pourrez l’attribuer de nouveau ensuite."
    }
};

document.querySelectorAll(".tag-action-form").forEach(form => {
    form.addEventListener("submit", event => {
        const language =
            localStorage.getItem("smartstore-language") === "fr" ? "fr" : "en";

        // Notification language for Flask
        const languageInput = form.querySelector('input[name="language"]');
        if (languageInput) languageInput.value = language;

        // Confirmation for the actions that change many tags or remove one
        const key = form.dataset.confirm;
        if (key && !confirm(tagResetMessages[language][key])) {
            event.preventDefault();
        }
    });
});
