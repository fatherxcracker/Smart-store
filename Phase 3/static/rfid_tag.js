// Product form: read the EPC of a single RFID tag from the CF600 reader.
const readTagButton = document.getElementById("read-tag");
const epcInput = document.getElementById("epc");
const tagStatus = document.getElementById("tag-status");

readTagButton.addEventListener("click", async () => {
    readTagButton.disabled = true;
    readTagButton.textContent = "Reading...";
    tagStatus.textContent = "";
    tagStatus.className = "tag-status";

    try {
        const response = await fetch("/api/rfid/read");
        const result = await response.json();

        if (result.success) {
            epcInput.value = result.epc;
            tagStatus.classList.add(result.in_use_by ? "warning" : "success");
        } else {
            tagStatus.classList.add("error");
        }
        tagStatus.textContent = result.message;
    } catch {
        tagStatus.classList.add("error");
        tagStatus.textContent = "Cannot reach the server.";
    } finally {
        readTagButton.disabled = false;
        readTagButton.textContent = "Read tag from RFID reader";
    }
});
