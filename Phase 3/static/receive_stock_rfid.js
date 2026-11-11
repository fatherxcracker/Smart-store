
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
