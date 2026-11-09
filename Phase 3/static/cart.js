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

// Language chosen on the customer portal (EN/FR switch), used for the receipt.
const language = localStorage.getItem("smartstore-language") === "fr" ? "fr" : "en";

// Auto-scan: read the reader again every few seconds while the box is ticked.
const AUTO_SCAN_MS = 2500;
let autoScanTimer = null;

const money = new Intl.NumberFormat("en-CA", {
    style: "currency",
    currency: "CAD"
});

let busy = false;
let currentCart = null;
let checkoutUncertain = false;

function showMessage(text, level = "success") {
    cartMessage.textContent = text;
    cartMessage.dataset.level = level;
}

async function cartRequest(url, method = "GET", body = null) {
    const options = {
        method,
        credentials: "same-origin",
        headers: {}
    };

    if (body !== null) {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
    }

    let response;

    try {
        response = await fetch(url, options);
    } catch {
        throw new Error("Cannot reach the server.");
    }

    let result;

    try {
        result = await response.json();
    } catch {
        throw new Error(
            "The server returned an unexpected response. Check the Flask terminal."
        );
    }

    if (!response.ok || !result.success) {
        const error = new Error(
            result.message || "The request failed."
        );

        error.rejected = (
            response.status >= 400 &&
            response.status < 500 &&
            result.success === false
        );

        throw error;
    }

    return result;
}

function refreshControls() {
    barcodeForm.querySelector("button").disabled = busy;
    rfidButton.disabled = busy;
    rfidButton.textContent = busy && rfidSection.classList.contains("scanning")
        ? "Scanning..."
        : "Scan all items";
    barcodeInput.disabled = busy;
    membershipInput.disabled = busy;
    paymentSelect.disabled = busy;

    resetButton.disabled = (
        busy ||
        !currentCart ||
        currentCart.items.length === 0
    );

    checkoutButton.disabled = (
        busy ||
        checkoutUncertain ||
        !currentCart ||
        !currentCart.can_checkout
    );

    checkoutButton.textContent = busy
        ? "Please wait..."
        : "Proceed to payment";

    document.querySelectorAll(".cart-remove").forEach(button => {
        button.disabled = busy;
    });
}

function setBusy(value) {
    busy = value;
    refreshControls();
}

function addCell(row, text, className = "") {
    const cell = document.createElement("td");
    cell.textContent = text;
    cell.className = className;
    row.appendChild(cell);
    return cell;
}

function renderCart(cart) {
    currentCart = cart;
    cartItems.replaceChildren();

    if (cart.items.length === 0) {
        const row = document.createElement("tr");
        const cell = addCell(row, "", "cart-empty");
        cell.colSpan = 5;

        const title = document.createElement("strong");
        title.textContent = "Your cart is empty";

        const description = document.createElement("span");
        description.textContent = "Scan a product to begin shopping.";

        cell.append(title, description);
        cartItems.appendChild(row);
    }

    for (const item of cart.items) {
        const row = document.createElement("tr");
        const nameCell = addCell(row, item.name);

        if (!item.available) {
            const warning = document.createElement("span");
            warning.className = "cart-unavailable";
            warning.textContent = "Unavailable or insufficient stock.";
            nameCell.appendChild(warning);
        }

        addCell(row, money.format(item.unit_price), "number");
        addCell(row, String(item.quantity), "number");
        addCell(row, money.format(item.line_total), "number");

        const actionCell = addCell(row, "");
        const removeButton = document.createElement("button");

        removeButton.type = "button";
        removeButton.className = "cart-remove";
        removeButton.textContent = "Remove";
        removeButton.setAttribute("aria-label", `Remove ${item.name}`);

        removeButton.addEventListener("click", () => {
            updateCart(
                `/api/cart/items/${item.product_id}`,
                "DELETE"
            );
        });

        actionCell.appendChild(removeButton);
        cartItems.appendChild(row);
    }

    for (const field of ["subtotal", "gst", "qst", "total"]) {
        document.getElementById(`cart-${field}`).textContent =
            money.format(cart[field]);
    }

    refreshControls();
}

async function loadCart() {
    try {
        const result = await cartRequest("/api/cart");
        renderCart(result.cart);
    } catch (error) {
        currentCart = null;
        refreshControls();
        showMessage(error.message, "error");
    }
}

async function updateCart(url, method, body = null) {
    if (busy) return;

    setBusy(true);

    try {
        const result = await cartRequest(url, method, body);

        renderCart(result.cart);
        showMessage(result.message);

        barcodeInput.value = "";
        receiptPanel.hidden = true;
    } catch (error) {
        showMessage(error.message, "error");
        await loadCart();
    } finally {
        setBusy(false);
        barcodeInput.focus();
    }
}

function displayReceipt(html) {
    receiptFrame.srcdoc = `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1">
        </head>
        <body>${html}</body>
        </html>
    `;

    receiptPanel.hidden = false;
    receiptPanel.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}

// ---------------------------------------------------------
// RFID: read every tag on the CF600 at once
// ---------------------------------------------------------
async function scanRfid({ quiet = false } = {}) {
    if (busy) return;

    setBusy(true);
    rfidSection.classList.add("scanning");
    refreshControls();

    try {
        const result = await cartRequest("/api/cart/rfid/scan", "POST");
        renderCart(result.cart);

        // In auto mode, stay quiet when nothing changed.
        const unchanged = result.message.includes("already been read") ||
                          result.message.startsWith("No RFID tags");
        if (!quiet || !unchanged) {
            showMessage(result.message, result.message.includes("unknown") ? "warning" : "success");
        }
        if (!unchanged) receiptPanel.hidden = true;
    } catch (error) {
        showMessage(error.message, "error");

        // Reader missing / not set up: stop auto-scan instead of repeating the error.
        if (rfidAuto.checked && error.message.includes("reader")) {
            rfidAuto.checked = false;
            stopAutoScan();
        }
    } finally {
        rfidSection.classList.remove("scanning");
        setBusy(false);
    }
}

function startAutoScan() {
    stopAutoScan();
    scanRfid();
    autoScanTimer = setInterval(() => scanRfid({ quiet: true }), AUTO_SCAN_MS);
}

function stopAutoScan() {
    clearInterval(autoScanTimer);
    autoScanTimer = null;
}

rfidButton.addEventListener("click", () => scanRfid());

rfidAuto.addEventListener("change", () => {
    if (rfidAuto.checked) {
        startAutoScan();
    } else {
        stopAutoScan();
    }
});

barcodeForm.addEventListener("submit", event => {
    event.preventDefault();

    const upc = barcodeInput.value.trim();
    if (!upc) return;

    updateCart("/api/cart/barcode", "POST", { upc });
});

resetButton.addEventListener("click", () => {
    if (busy || !window.confirm("Remove all items from your cart?")) {
        return;
    }

    updateCart("/api/cart", "DELETE");
});

checkoutForm.addEventListener("submit", async event => {
    event.preventDefault();

    if (
        busy ||
        checkoutUncertain ||
        !currentCart ||
        !currentCart.can_checkout
    ) {
        return;
    }

    const membershipNumber = membershipInput.value.trim();
    const memberDescription = membershipNumber
        ? `Membership: ${membershipNumber}`
        : "Guest checkout";

    const confirmed = window.confirm(
        `Confirm simulated payment of ${money.format(currentCart.total)}?\n` +
        `${memberDescription}\n` +
        "No real money will be charged."
    );

    if (!confirmed) return;

    // Stop reading tags once the customer confirms the list.
    rfidAuto.checked = false;
    stopAutoScan();

    const details = {
        membership_number: membershipNumber,
        payment_method: paymentSelect.value,
        language: language
    };

    setBusy(true);

    let result;

    try {
        result = await cartRequest("/api/checkout", "POST", details);
    } catch (error) {
        if (error.rejected) {
            showMessage(error.message, "error");
        } else {
            checkoutUncertain = true;

            showMessage(
                "Checkout status could not be confirmed. " +
                "Check purchase history and the Flask terminal before trying again.",
                "error"
            );
        }

        await loadCart();
        setBusy(false);
        return;
    }

    renderCart(result.cart);
    membershipInput.value = "";

    const notes = result.notifications || [];
    const hasWarning = notes.some(note => note.level === "warning");

    showMessage(
        notes.map(note => note.message).join("\n") || result.message,
        hasWarning ? "warning" : "success"
    );

    setBusy(false);
    displayReceipt(result.receipt_html);
});

loadCart();