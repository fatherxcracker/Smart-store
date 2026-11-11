
 // Get the checkout elements from cart.html
const cartItems = document.getElementById("cart-items");
const cartMessage = document.getElementById("cart-message");
const barcodeForm = document.getElementById("barcode-form");
const barcodeInput = document.getElementById("barcode-input");
const resetButton = document.getElementById("reset-cart");
const checkoutButton = document.getElementById("checkout");
const checkoutForm = document.getElementById("checkout-form");
const membershipInput = document.getElementById("membership-number");
const paymentSelect = document.getElementById("payment-method");
const receiptPanel = document.getElementById("receipt-panel");
const receiptFrame = document.getElementById("receipt-frame");
const rfidButton = document.getElementById("rfid-scan");
const rfidAuto = document.getElementById("rfid-auto");
const rfidSection = document.querySelector(".rfid-scanner");

// Automatically fill the membership number for logged-in customers
async function loadMembershipNumber() {

    try {
        // Get the currently logged-in customer
        const response = await fetch("/api/account/me", {
            credentials: "same-origin"
        });

        // Guests do not have a membership number
        if (!response.ok) {
            membershipInput.value = "";
            return;
        }

        // Read the customer information
        const customer = await response.json();

        // Fill the membership field
        membershipInput.value = customer.membership_number || "";

    } catch (error) {
        // Leave the field empty if customer information cannot be loaded
        console.error("Could not load membership number:", error);
    }
}

// Remember the language chosen in the website
let cartLanguage =
    localStorage.getItem("smartstore-language") === "fr" ? "fr" : "en";

// Translations for messages created by cart.js
const cartWords = {

    // English translations
    en: {
        server: "Cannot reach the server.",
        unexpected: "The server returned an unexpected response. Check the Flask terminal.",
        failed: "The request failed.",
        scanning: "Scanning...",
        scan: "Scan RFID",
        auto: "Auto Scan",
        autoStop: "Stop Auto Scan",
        wait: "Please wait...",
        pay: "Complete Purchase",
        empty: "Your cart is empty",
        begin: "Scan a product to begin shopping.",
        unavailable: "Unavailable or insufficient stock.",
        remove: "Remove",
        resetConfirm: "Remove all items from your cart?",
        membership: "Membership",
        guest: "Guest checkout",
        confirmPayment: "Confirm simulated payment of",
        noCharge: "No real money will be charged.",
        uncertain: "Checkout status could not be confirmed. Check purchase history and the Flask terminal before trying again.",
        removed: "Product removed from cart",
        added: "Product added to cart",
        cleared: "Cart cleared",
        readerError: "RFID reader error",
        unknown: "Unknown product",
        noTags: "No RFID tags found",
        already: "These RFID tags have already been read",
        checkoutSuccess: "Purchase completed successfully",
        paymentRequired: "Please select a payment method"
    },

    // French translations
    fr: {
        server: "Impossible de joindre le serveur.",
        unexpected: "Le serveur a renvoyé une réponse inattendue. Vérifiez le terminal Flask.",
        failed: "La requête a échoué.",
        scanning: "Numérisation...",
        scan: "Numériser RFID",
        auto: "Numérisation automatique",
        autoStop: "Arrêter la numérisation",
        wait: "Veuillez patienter...",
        pay: "Terminer l'achat",
        empty: "Votre panier est vide",
        begin: "Numérisez un produit pour commencer.",
        unavailable: "Produit indisponible ou stock insuffisant.",
        remove: "Retirer",
        resetConfirm: "Retirer tous les articles de votre panier ?",
        membership: "Numéro de membre",
        guest: "Achat sans compte",
        confirmPayment: "Confirmer le paiement simulé de",
        noCharge: "Aucun montant réel ne sera facturé.",
        uncertain: "Impossible de confirmer le paiement. Vérifiez l'historique des achats et le terminal Flask avant de réessayer.",
        removed: "Produit retiré du panier",
        added: "Produit ajouté au panier",
        cleared: "Panier vidé",
        readerError: "Erreur du lecteur RFID",
        unknown: "Produit inconnu",
        noTags: "Aucune étiquette RFID trouvée",
        already: "Ces étiquettes RFID ont déjà été lues",
        checkoutSuccess: "Achat terminé avec succès",
        paymentRequired: "Veuillez choisir un mode de paiement"
    }
};


// Get a translation in the selected language
function cartText(key) {
    return cartWords[cartLanguage][key] || key;
}


// Format prices in Canadian dollars
function formatMoney(amount) {
    return new Intl.NumberFormat(
        cartLanguage === "fr" ? "fr-CA" : "en-CA",
        {
            style: "currency",
            currency: "CAD"
        }
    ).format(Number(amount) || 0);
}


// Auto scan reads the RFID reader every 2.5 seconds
const AUTO_SCAN_MS = 2500;

let autoScanTimer = null;
let autoScanEnabled = false;
let busy = false;
let currentCart = null;
let checkoutUncertain = false;
let lastMessageKey = null;
let lastMessageLevel = "success";


// Show a message above the shopping cart
function showMessage(text, level = "success", key = null) {

    cartMessage.textContent = key ? cartText(key) : text;

    cartMessage.dataset.level = level;

    lastMessageKey = key;
    lastMessageLevel = level;
}


// Send requests to the Flask API
async function cartRequest(url, method = "GET", body = null) {

    const options = {
        method,
        credentials: "same-origin",
        headers: {}
    };

    // Send JSON when there is information to send
    if (body !== null) {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
    }

    let response;

    try {
        // Send the request to Flask
        response = await fetch(url, options);

    } catch {
        // Show an error if Flask cannot be reached
        throw new Error(cartText("server"));
    }

    let result;

    try {
        // Convert the response into JavaScript data
        result = await response.json();

    } catch {
        // Show an error if Flask returns invalid JSON
        throw new Error(cartText("unexpected"));
    }

    // Check if Flask returned an error
    if (!response.ok || !result.success) {

        const error = new Error(
            result.message || cartText("failed")
        );

        // Remember if Flask rejected the request
        error.rejected =
            response.status >= 400 &&
            response.status < 500 &&
            result.success === false;

        throw error;
    }

    return result;
}


// Update buttons when scanning or checkout is busy
function refreshControls() {

    // Disable barcode button while busy
    barcodeForm.querySelector("button").disabled = busy;

    // Disable RFID button while busy
    rfidButton.disabled = busy;

    // Change RFID button text during scanning
    rfidButton.textContent =
        busy && rfidSection?.classList.contains("scanning")
            ? cartText("scanning")
            : cartText("scan");

    // Keep the stop button available during automatic scanning
    rfidAuto.disabled = busy && !autoScanEnabled;

    // Change automatic scanning button text
    rfidAuto.textContent =
        autoScanEnabled
            ? cartText("autoStop")
            : cartText("auto");

    // Remember whether automatic scanning is active
    rfidAuto.setAttribute(
        "aria-pressed",
        String(autoScanEnabled)
    );

    // Disable inputs while busy
    barcodeInput.disabled = busy;
    membershipInput.disabled = busy;
    paymentSelect.disabled = busy;

    // Reset Cart stays available even when the cart is empty: it also
    // clears the remembered RFID tags (removed items stay "already read").
    resetButton.disabled = busy;

    // Disable checkout if Flask says checkout is unavailable
    checkoutButton.disabled =
        busy ||
        checkoutUncertain ||
        !currentCart ||
        !currentCart.can_checkout;

    // Update checkout button text
    checkoutButton.textContent =
        busy ? cartText("wait") : cartText("pay");

    // Disable Remove buttons while busy
    document.querySelectorAll(".cart-remove").forEach(button => {
        button.disabled = busy;
    });
}


// Change the busy status
function setBusy(value) {

    busy = value;

    refreshControls();
}


// Add a cell to the shopping cart table
function addCell(row, value, className = "") {

    const cell = document.createElement("td");

    cell.textContent = value;
    cell.className = className;

    row.appendChild(cell);

    return cell;
}


// Display products and totals returned by Flask
function renderCart(cart) {

    // Remember the latest cart
    currentCart = cart;

    // Clear previous cart rows
    cartItems.replaceChildren();

    // Display a message when the cart is empty
    if (cart.items.length === 0) {

        const row = document.createElement("tr");

        const cell = addCell(row, "", "cart-empty");
        cell.colSpan = 5;

        const title = document.createElement("strong");
        title.textContent = cartText("empty");

        const description = document.createElement("span");
        description.textContent = cartText("begin");

        cell.append(title, description);

        cartItems.appendChild(row);
    }

    // Display every product in the cart
    for (const item of cart.items) {

        const row = document.createElement("tr");

        // Display product name
        const nameCell = addCell(row, item.name);

        // Show warning if product is unavailable
        if (!item.available) {

            const warning = document.createElement("span");

            warning.className = "cart-unavailable";
            warning.textContent = cartText("unavailable");

            nameCell.appendChild(warning);
        }

        // Match cart.html columns Product Quantity Price Total
        addCell(row, String(item.quantity), "number");
        addCell(row, formatMoney(item.unit_price), "number");
        addCell(row, formatMoney(item.line_total), "number");

        // Create the Remove button
        const actionCell = addCell(row, "");

        const removeButton = document.createElement("button");

        removeButton.type = "button";
        removeButton.className = "cart-remove";
        removeButton.textContent = cartText("remove");

        // Add accessible button description
        removeButton.setAttribute(
            "aria-label",
            `${cartText("remove")} ${item.name}`
        );

        // Remove selected product from the cart
        removeButton.addEventListener("click", () => {

            updateCart(
                `/api/cart/items/${item.product_id}`,
                "DELETE",
                null,
                "removed"
            );
        });

        actionCell.appendChild(removeButton);

        cartItems.appendChild(row);
    }

    // Update subtotal and taxes
    for (const field of ["subtotal", "gst", "qst", "total"]) {

        document.getElementById(`cart-${field}`).textContent =
            formatMoney(cart[field]);
    }

    refreshControls();
}


// Load the cart from Flask
async function loadCart() {

    try {
        // Ask Flask for the current cart
        const result = await cartRequest("/api/cart");

        // Display the products
        renderCart(result.cart);

    } catch (error) {

        currentCart = null;

        refreshControls();

        showMessage(error.message, "error");
    }
}


// Add or remove products and update the cart
async function updateCart(url, method, body = null, messageKey = null) {

    if (busy) return;

    setBusy(true);

    try {
        // Send the cart change to Flask
        const result = await cartRequest(url, method, body);

        // Display the updated cart
        renderCart(result.cart);

        // Show the result message
        showMessage(
            result.message || cartText(messageKey || "added"),
            "success",
            messageKey
        );

        // Clear barcode input
        barcodeInput.value = "";

        // Hide old receipt
        receiptPanel.hidden = true;

    } catch (error) {

        showMessage(error.message, "error");

        // Reload cart after an error
        await loadCart();

    } finally {

        setBusy(false);

        barcodeInput.focus();
    }
}


// Display the receipt HTML returned by Flask
function displayReceipt(html) {

    // Display the receipt in the iframe
    receiptFrame.srcdoc = `
        <!DOCTYPE html>
        <html lang="${cartLanguage}">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1">
        </head>
        <body>${html}</body>
        </html>
    `;

    // Show receipt panel
    receiptPanel.hidden = false;

    // Scroll to receipt
    receiptPanel.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


// RFID scanning

// Read every RFID tag on the CF600 reader
async function scanRfid({ quiet = false } = {}) {

    if (busy) return;

    setBusy(true);

    // Mark RFID section as scanning if it exists
    rfidSection?.classList.add("scanning");

    refreshControls();

    try {
        // Ask Flask to scan RFID tags
        // A manual scan re-adds removed items; auto-scan (quiet) does not.
        const result = await cartRequest(
            "/api/cart/rfid/scan",
            "POST",
            { manual: !quiet }
        );

        // Update cart with scanned products
        renderCart(result.cart);

        // Check if the reader found nothing new
        const raw = result.message || "";

        const unchanged =
            raw.includes("already been read") ||
            raw.startsWith("No RFID tags");

        // Avoid repeating messages during automatic scanning
        if (!quiet || !unchanged) {

            const key =
                raw.startsWith("No RFID tags")
                    ? "noTags"
                    : raw.includes("already been read")
                        ? "already"
                        : null;

            showMessage(
                raw,
                raw.includes("unknown") || raw.includes("Ignored:") ? "warning" : "success",
                key
            );
        }

        // Hide old receipt if new products were scanned
        if (!unchanged) {
            receiptPanel.hidden = true;
        }

    } catch (error) {

        showMessage(error.message, "error");

        // Stop automatic scanning if the reader is unavailable
        if (
            autoScanEnabled &&
            error.message.toLowerCase().includes("reader")
        ) {
            stopAutoScan();
        }

    } finally {

        rfidSection?.classList.remove("scanning");

        setBusy(false);
    }
}


// Start automatic RFID scanning
function startAutoScan() {

    stopAutoScan();

    autoScanEnabled = true;

    // Scan immediately
    scanRfid();

    // Scan again every 2.5 seconds
    autoScanTimer = setInterval(
        () => scanRfid({ quiet: true }),
        AUTO_SCAN_MS
    );

    refreshControls();
}


// Stop automatic RFID scanning
function stopAutoScan() {

    clearInterval(autoScanTimer);

    autoScanTimer = null;
    autoScanEnabled = false;

    refreshControls();
}


// Scan when customer clicks Scan RFID
rfidButton.addEventListener("click", () => {
    scanRfid();
});


// Auto Scan is a button in the updated cart.html
rfidAuto.addEventListener("click", () => {

    // Stop scanning if already active
    if (autoScanEnabled) {
        stopAutoScan();

    } else {
        // Start automatic scanning
        startAutoScan();
    }
});


// USB barcode scanners usually type digits quickly and finish with Enter.
// Detect a complete UPC anywhere on this page without moving focus while the
// customer is typing into the membership field or choosing a payment method.
let scannerBuffer = "";
let scannerLastKey = 0;
let scannerTarget = null;
let scannerOriginalValue = null;
let scannerSelection = null;

function resetScannerBuffer() {
    scannerBuffer = "";
    scannerLastKey = 0;
    scannerTarget = null;
    scannerOriginalValue = null;
    scannerSelection = null;
}

document.addEventListener("keydown", event => {
    if (event.isComposing || event.ctrlKey || event.altKey || event.metaKey) {
        resetScannerBuffer();
        return;
    }

    const now = performance.now();
    if (/^[0-9]$/.test(event.key)) {
        if (!scannerBuffer || now - scannerLastKey > 80 || scannerTarget !== event.target) {
            resetScannerBuffer();
            scannerTarget = event.target;
            if (event.target instanceof HTMLInputElement && event.target.type === "text") {
                scannerOriginalValue = event.target.value;
                scannerSelection = [event.target.selectionStart, event.target.selectionEnd];
            }
        }
        scannerBuffer += event.key;
        scannerLastKey = now;
        if (scannerBuffer.length > 13) resetScannerBuffer();
        return;
    }

    if (event.key === "Enter" && now - scannerLastKey <= 150 &&
        (scannerBuffer.length === 12 || scannerBuffer.length === 13)) {
        const upc = scannerBuffer;
        // Undo scanner keystrokes in another text field, preserving user input.
        if (scannerOriginalValue !== null && scannerTarget !== barcodeInput) {
            scannerTarget.value = scannerOriginalValue;
            if (scannerSelection[0] !== null) {
                scannerTarget.setSelectionRange(...scannerSelection);
            }
        }
        event.preventDefault();
        event.stopPropagation();
        resetScannerBuffer();
        if (busy) {
            showMessage("Please wait until the current action finishes, then scan again.", "error");
        } else {
            updateCart("/api/cart/barcode", "POST", { upc }, "added");
        }
        return;
    }
    resetScannerBuffer();
}, true);

// Add a product when barcode form is submitted
barcodeForm.addEventListener("submit", event => {

    // Stop page refresh
    event.preventDefault();

    // Get barcode entered by customer
    const upc = barcodeInput.value.trim();

    // Add product through Flask
    if (upc) {
        updateCart(
            "/api/cart/barcode",
            "POST",
            { upc },
            "added"
        );
    }
});


// Clear the cart after confirmation
resetButton.addEventListener("click", () => {

    // Do nothing if checkout is busy
    if (busy) return;

    // Ask customer to confirm
    const confirmed = window.confirm(
        cartText("resetConfirm")
    );

    if (!confirmed) return;

    // Delete cart contents through Flask
    updateCart(
        "/api/cart",
        "DELETE",
        null,
        "cleared"
    );
});


// Complete the simulated payment
checkoutForm.addEventListener("submit", async event => {

    // Stop page refresh
    event.preventDefault();

    // Check if checkout is available
    if (
        busy ||
        checkoutUncertain ||
        !currentCart ||
        !currentCart.can_checkout
    ) {
        return;
    }

    // Check that a payment method was selected
    if (!paymentSelect.value) {

        showMessage(
            cartText("paymentRequired"),
            "warning",
            "paymentRequired"
        );

        return;
    }

    // Get membership number
    const membershipNumber = membershipInput.value.trim();

    // Create membership description
    const memberDescription = membershipNumber
        ? `${cartText("membership")}: ${membershipNumber}`
        : cartText("guest");

    // Ask customer to confirm simulated payment
    const confirmed = window.confirm(
        `${cartText("confirmPayment")} ${formatMoney(currentCart.total)}?\n` +
        `${memberDescription}\n` +
        `${cartText("noCharge")}`
    );

    if (!confirmed) return;

    // Stop scanning after customer confirms purchase
    stopAutoScan();

    // Send checkout information to Flask
    const details = {
        membership_number: membershipNumber,
        payment_method: paymentSelect.value,
        language: cartLanguage
    };

    setBusy(true);

    let result;

    try {
        // Send checkout request
        const response = await cartRequest(
            "/api/checkout",
            "POST",
            details
        );

        result = response;

    } catch (error) {

        // Flask rejected the payment
        if (error.rejected) {

            showMessage(error.message, "error");

        } else {

            // Server response was uncertain
            checkoutUncertain = true;

            showMessage(
                cartText("uncertain"),
                "error",
                "uncertain"
            );
        }

        // Reload the cart
        await loadCart();

        setBusy(false);

        return;
    }

    // Update cart after checkout
    renderCart(result.cart);

    // Clear membership field
    await loadMembershipNumber();

    // Get notifications from Flask
    const notes = result.notifications || [];

    // Check if any notifications are warnings
    const hasWarning = notes.some(
        note => note.level === "warning"
    );

    // Show checkout result
    showMessage(
        notes.map(note => note.message).join("\n") ||
        result.message ||
        cartText("checkoutSuccess"),
        hasWarning ? "warning" : "success"
    );

    setBusy(false);

    // Display the receipt returned by Flask
    displayReceipt(result.receipt_html);
});


// Update dynamic cart text when customer switches EN or FR
window.addEventListener("smartstore-language-change", event => {

    // Get the newly selected language
    cartLanguage =
        event.detail?.language === "fr" ? "fr" : "en";

    // Translate cart rows and totals
    if (currentCart) {

        renderCart(currentCart);

    } else {

        refreshControls();
    }

    // Translate the last message if it has a translation key
    if (lastMessageKey) {

        showMessage(
            cartText(lastMessageKey),
            lastMessageLevel,
            lastMessageKey
        );
    }
});


// Make the scanner field ready on page load without interrupting later input.
barcodeInput.focus();

// Load the cart and membership number when the page opens
loadCart();
loadMembershipNumber();
