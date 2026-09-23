const form = document.getElementById("customer-form");
const submitBtn = document.getElementById("submit-btn");
const notification = document.getElementById("notification");
const customersBody = document.getElementById("customers-body");

const blueDot = document.querySelector("#blue-led .dot");
const redDot = document.querySelector("#red-led .dot");
const buzzerDot = document.querySelector("#buzzer-indicator .dot");

function setIndicators({ blue_led, red_led, buzzer }) {
    blueDot.classList.toggle("on", !!blue_led);
    redDot.classList.toggle("on", !!red_led);
    buzzerDot.classList.toggle("on", !!buzzer);
}

function clearIndicatorsSoon() {
    setTimeout(() => {
        setIndicators({ blue_led: false, red_led: false, buzzer: false });
        // Tell the backend to physically turn the LEDs/buzzer off too.
        fetch("/api/hardware/reset", { method: "POST" }).catch(() => {});
    }, 2000);
}

function showNotification(message, isSuccess) {
    notification.textContent = message;
    notification.classList.remove("hidden", "success", "error");
    notification.classList.add(isSuccess ? "success" : "error");
}

async function loadCustomers() {
    try {
        const res = await fetch("/api/customers");
        const customers = await res.json();

        customersBody.innerHTML = "";
        customers.forEach((c) => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${c.customer_id}</td>
                <td>${escapeHtml(c.full_name)}</td>
                <td>${escapeHtml(c.address)}</td>
                <td>${escapeHtml(c.telephone_number)}</td>
                <td>${escapeHtml(c.email_address)}</td>
            `;
            customersBody.appendChild(row);
        });
    } catch (err) {
        console.error("Failed to load customers:", err);
    }
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str ?? "";
    return div.innerHTML;
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    submitBtn.disabled = true;

    const payload = {
        full_name: document.getElementById("full_name").value,
        address: document.getElementById("address").value,
        phone: document.getElementById("phone").value,
        email: document.getElementById("email").value,
    };

    try {
        const res = await fetch("/api/customers", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await res.json();

        showNotification(data.message, data.success);
        setIndicators(data.hardware);
        clearIndicatorsSoon();

        if (data.success) {
            form.reset();
            loadCustomers();
        }
    } catch (err) {
        showNotification("Could not reach the server. Is app.py running?", false);
        setIndicators({ blue_led: false, red_led: true, buzzer: true });
        clearIndicatorsSoon();
    } finally {
        submitBtn.disabled = false;
    }
});

// Initial load
loadCustomers();
