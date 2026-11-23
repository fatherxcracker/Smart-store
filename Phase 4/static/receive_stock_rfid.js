// Receive stock: every item received gets its own RFID tag.
// The reader works in CDC (USB serial) mode: "Read one RFID tag" asks the
// server to read the reader, which must have exactly ONE tag on it, so each
// click adds one item. The quantity received is the number of tags.

(() => {
    const readButton = document.getElementById("receive-read-tag");
    const field = document.getElementById("epcs");
    const quantity = document.getElementById("quantity");
    const counter = document.getElementById("epc-count");
    const status = document.getElementById("receive-tag-status");
    if (!field || !quantity) return;
    const form = field.closest("form");

    const fr = () => document.documentElement.lang === "fr";
    const text = {
        reading: () => fr() ? "Lecture de l'étiquette..." : "Reading tag...",
        added: epc => fr() ? `Étiquette ${epc} ajoutée (1 article).` : `Tag ${epc} added (1 item).`,
        inList: epc => fr() ? `L'étiquette ${epc} est déjà dans cette livraison.` : `Tag ${epc} is already in this delivery.`,
        noServer: () => fr() ? "Impossible de joindre le serveur." : "Cannot reach the server.",
        duplicate: epc => fr() ? `L'étiquette ${epc} est inscrite deux fois.` : `Tag ${epc} is listed twice.`,
        invalid: epc => fr() ? `EPC invalide : ${epc} (hexadécimal, 24 caractères max).` : `Invalid EPC: ${epc} (hexadecimal, max 24 characters).`,
        none: () => fr() ? "Lisez l'étiquette RFID d'au moins un article." : "Read the RFID tag of at least one item.",
        count: n => fr() ? `${n} étiquette(s) = ${n} article(s) reçu(s).` : `${n} tag(s) = ${n} item(s) received.`
    };

    const tags = () => field.value.split(/\r?\n/).map(v => v.trim().toUpperCase()).filter(Boolean);

    function setStatus(message, kind) {
        status.textContent = message;
        status.className = kind ? `tag-status ${kind}` : "";
    }

    // Quantity = number of tags; flag duplicates and invalid EPCs before submitting
    function update() {
        const list = tags();
        quantity.value = list.length;
        if (counter) counter.textContent = text.count(list.length);

        const seen = new Set();
        let problem = "";
        for (const epc of list) {
            if (!/^[0-9A-F]{1,24}$/.test(epc)) { problem = text.invalid(epc); break; }
            if (seen.has(epc)) { problem = text.duplicate(epc); break; }
            seen.add(epc);
        }
        if (!problem && list.length === 0) problem = text.none();
        field.setCustomValidity(problem);
    }

    if (readButton) {
        readButton.addEventListener("click", async () => {
            readButton.disabled = true;
            setStatus(text.reading());
            try {
                const response = await fetch("/api/rfid/read");
                const result = await response.json();
                if (!response.ok || !result.success) {
                    // 0 tags, more than one tag, or the reader isn't connected in CDC mode
                    setStatus(result.message || "Could not read tag.", "error");
                } else if (result.in_use_by) {
                    // Tag already on an unsold item in stock: never count it twice
                    setStatus(result.message, "error");
                } else if (tags().includes(result.epc)) {
                    setStatus(text.inList(result.epc), "warning");
                } else {
                    field.value = [...tags(), result.epc].join("\n");
                    update();
                    setStatus(text.added(result.epc), "success");
                }
            } catch {
                setStatus(text.noServer(), "error");
            } finally {
                readButton.disabled = false;
            }
        });
    }

    field.addEventListener("input", update);
    form?.addEventListener("submit", event => {
        update();
        if (!field.checkValidity()) {
            event.preventDefault();
            field.reportValidity();
        }
    });
    // Re-translate the counter when the language switch is used
    document.getElementById("lang-en")?.addEventListener("click", () => setTimeout(update));
    document.getElementById("lang-fr")?.addEventListener("click", () => setTimeout(update));
    update();
})();
