const cartItems = document.getElementById("cart-items");
const cartMessage = document.getElementById("cart-message");
const barcodeForm = document.getElementById("barcode-form");
const barcodeInput = document.getElementById("barcode-input");
const resetButton = document.getElementById("reset-cart");
const checkoutButton = document.getElementById("checkout");

const money = new Intl.NumberFormat("en-CA", {
    style: "currency",
    currency: "CAD"
});

let busy = false;

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
        throw new Error("Cannot reach the server. Please try again.");
    }

    const result = await response.json();

    if (!response.ok || !result.success) {
        throw new Error(result.message || "The request failed.");
    }

    return result;
}

function addCell(row, text, className = "") {
    const cell = document.createElement("td");
    cell.textContent = text;
    cell.className = className;
    row.appendChild(cell);
    return cell;
}

function renderCart(cart) {
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
        removeButton.disabled = busy;

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

    resetButton.disabled = busy || cart.items.length === 0;

    // Enabled once we connect payment and receipt handling.
    checkoutButton.disabled = true;
}

function setBusy(value) {
    busy = value;

    barcodeForm.querySelector("button").disabled = value;
    barcodeInput.disabled = value;

    if (value) {
        resetButton.disabled = true;
        document.querySelectorAll(".cart-remove").forEach(button => {
            button.disabled = true;
        });
    }
}

async function updateCart(url, method, body = null) {
    if (busy) return;

    setBusy(true);
    let updatedCart = null;

    try {
        const result = await cartRequest(url, method, body);
        updatedCart = result.cart;

        showMessage(result.message);
        barcodeInput.value = "";
    } catch (error) {
        showMessage(error.message, "error");
    } finally {
        setBusy(false);

        if (updatedCart) {
            renderCart(updatedCart);
        } else {
            // Restore controls after a rejected request.
            await loadCart();
        }

        barcodeInput.focus();
    }
}

async function loadCart() {
    try {
        const result = await cartRequest("/api/cart");
        renderCart(result.cart);
    } catch (error) {
        showMessage(error.message, "error");
    }
}

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

loadCart();