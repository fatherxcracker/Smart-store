// Receive stock: every item received gets its own RFID tag.
// The reader works in CDC (USB serial) mode: "Read RFID tags" reads every tag
// on the reader at once and adds the new ones to the delivery list. Tags
// already in the list or already on an item in stock are skipped, so no tag is
// counted twice. The quantity received is the number of tags.

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
        reading: () => fr() ? "Lecture des étiquettes..." : "Reading tags...",
        added: n => fr() ? `${n} étiquette(s) ajoutée(s) (${n} article(s)).` : `${n} tag(s) added (${n} item(s)).`,
        nothingNew: () => fr() ? "Aucune nouvelle étiquette à ajouter." : "No new tags to add.",
        inList: n => fr() ? `${n} déjà dans cette livraison` : `${n} already in this delivery`,
        inStock: list => fr() ? `déjà en stock : ${list}` : `already on items in stock: ${list}`,
        invalidTag: n => fr() ? `${n} EPC invalide(s)` : `${n} invalid EPC(s)`,
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
                const response = await fetch("/api/rfid/read-all", { credentials: "same-origin" });
                const result = await response.json();
                if (!response.ok || !result.success) {
                    // No tags, or the reader isn't connected in CDC mode
                    setStatus(window.rfidMessageForLanguage(result.message || "Could not read tags."), "error");
                    return;
                }
                const current = tags();
                const added = [], alreadyListed = [], inStock = [], invalid = [];
                for (const tag of result.tags) {
                    if (tag.status === "invalid") invalid.push(tag.epc);
                    else if (!tag.assignable) inStock.push(`${tag.epc} (${tag.product})`);  // never count twice
                    else if (current.includes(tag.epc) || added.includes(tag.epc)) alreadyListed.push(tag.epc);
                    else added.push(tag.epc);
                }
                if (added.length) {
                    field.value = [...current, ...added].join("\n");
                    update();
                }
                const notes = [];
                if (alreadyListed.length) notes.push(text.inList(alreadyListed.length));
                if (inStock.length) notes.push(text.inStock(inStock.join(", ")));
                if (invalid.length) notes.push(text.invalidTag(invalid.length));
                const head = added.length ? text.added(added.length) : text.nothingNew();
                setStatus(notes.length ? `${head} ${fr() ? "Ignorées" : "Skipped"}: ${notes.join("; ")}.` : head,
                          added.length ? (notes.length ? "warning" : "success") : (inStock.length || invalid.length ? "error" : "warning"));
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
