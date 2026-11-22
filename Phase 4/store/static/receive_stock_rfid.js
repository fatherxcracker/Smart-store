
// Reads one RFID tag and adds it to the delivery list
const receiveReadTag = document.getElementById("receive-read-tag");
if (receiveReadTag) {
    receiveReadTag.addEventListener("click", async () => {
        const status = document.getElementById("receive-tag-status");
        const field = document.getElementById("epcs");
        // Stops another scan while the reader is busy
        receiveReadTag.disabled = true;
        status.textContent = "Reading tag...";
        try {
            const response = await fetch("/api/rfid/read");
            const result = await response.json();
            if (!response.ok || !result.success) {
                status.textContent = result.message || "Could not read tag.";
            } else if (result.in_use_by) {
                status.textContent = result.message;
            } else {
                // Keeps one tag per line and removes empty lines
                const tags = field.value.split(/\r?\n/).map(value => value.trim().toUpperCase()).filter(Boolean);
                // Avoids adding the same physical item twice
                if (tags.includes(result.epc)) {
                    status.textContent = "This tag is already in the delivery list.";
                } else {
                    tags.push(result.epc);
                    field.value = tags.join("\n");
                    status.textContent = "Tag added to the delivery list.";
                }
            }
        } catch (error) {
            status.textContent = "Cannot reach the server.";
        } finally {
            receiveReadTag.disabled = false;
        }
    });
}

// Reader in keyboard mode: every tag held on the reader is added to the delivery list
document.addEventListener("rfid-scan", event => {
    const status = document.getElementById("receive-tag-status");
    const field = document.getElementById("epcs");
    if (!field) return;
    const tags = field.value.split(/\r?\n/).map(value => value.trim().toUpperCase()).filter(Boolean);
    if (tags.includes(event.detail.epc)) {
        status.textContent = "This tag is already in the delivery list.";
    } else {
        tags.push(event.detail.epc);
        field.value = tags.join("\n");
        status.textContent = `Tag ${event.detail.epc} added to the delivery list.`;
    }
});

// One EPC per item: show "EPCs: 4 / 40" and refuse to submit until they match
(() => {
    const field = document.getElementById("epcs");
    const quantity = document.getElementById("quantity");
    const counter = document.getElementById("epc-count");
    if (!field || !quantity || !counter) return;
    const form = field.closest("form");

    const countEpcs = () => field.value.split(/\r?\n/).filter(line => line.trim()).length;

    function updateCount() {
        const wanted = parseInt(quantity.value, 10) || 0;
        const have = countEpcs();
        counter.textContent = `EPCs: ${have} / ${wanted}` + (have === wanted && wanted > 0 ? " ✓" : "");
        field.setCustomValidity(
            have === wanted ? "" : `Every item needs one RFID tag: quantity is ${wanted} but ${have} EPC(s) entered.`
        );
    }

    field.addEventListener("input", updateCount);
    quantity.addEventListener("input", updateCount);
    document.addEventListener("rfid-scan", () => setTimeout(updateCount));
    form?.addEventListener("submit", event => {
        updateCount();
        if (!field.checkValidity()) {
            event.preventDefault();
            field.reportValidity();
        }
    });
    updateCount();
})();
