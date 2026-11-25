// "Add several tagged items": read every tag on the CF600 at once (CDC mode),
// show what each one is, and assign only the tags that can be added.
// The server checks everything again when the form is submitted.
(() => {
    const form = document.getElementById("bulk-tags-form");
    if (!form) return;
    const scanButton = document.getElementById("read-all-tags");
    const status = document.getElementById("bulk-status");
    const list = document.getElementById("bulk-tag-list");
    const assignButton = document.getElementById("bulk-assign");
    const productName = form.dataset.productName;

    const fr = () => document.documentElement.lang === "fr";
    const text = {
        reading: () => fr() ? "Lecture..." : "Reading...",
        server: () => fr() ? "Impossible de joindre le serveur." : "Cannot reach the server.",
        found: (n, ok) => fr()
            ? `${n} étiquette(s) lue(s), ${ok} peuvent être ajoutée(s).`
            : `${n} tag(s) read, ${ok} can be added.`,
        none: () => fr()
            ? "Aucune étiquette ne peut être ajoutée : elles sont déjà toutes sur des articles en stock."
            : "None of these tags can be added: they are all already on items in stock.",
        assign: n => fr()
            ? `Ajouter ${n} article(s) à ${productName}`
            : `Add ${n} item(s) to ${productName}`,
        reason: tag => ({
            new: fr() ? "nouvelle" : "new",
            sold: fr() ? `vendue avant (${tag.product}) : réutilisable` : `sold before (${tag.product}): reusable`,
            this_product: fr() ? "déjà sur ce produit" : "already on this product",
            other_product: fr() ? `déjà sur ${tag.product}` : `already on ${tag.product}`,
            invalid: fr() ? "EPC invalide" : "not a valid EPC",
        })[tag.status],
    };

    function reset() {
        list.replaceChildren();
        list.hidden = true;
        assignButton.hidden = true;
        form.querySelectorAll('input[name="epcs"]').forEach(input => input.remove());
    }

    scanButton.addEventListener("click", async () => {
        const label = scanButton.textContent;
        scanButton.disabled = true;
        scanButton.textContent = text.reading();
        status.className = "tag-status";
        status.textContent = "";
        reset();
        try {
            const response = await fetch(`/api/rfid/read-all?product_id=${form.dataset.productId}`,
                                         { credentials: "same-origin" });
            const result = await response.json();
            if (!result.success) {
                status.classList.add("error");
                status.textContent = window.rfidMessageForLanguage(result.message);
                return;
            }
            for (const tag of result.tags) {
                const row = document.createElement("li");
                row.className = tag.assignable ? "add" : "skip";
                const epc = document.createElement("span");
                epc.className = "tag-epc";
                epc.textContent = tag.epc;
                const reason = document.createElement("span");
                reason.className = "bulk-reason";
                reason.textContent = text.reason(tag);
                row.append(epc, reason);
                list.append(row);
                if (tag.assignable) {
                    const input = document.createElement("input");
                    input.type = "hidden";
                    input.name = "epcs";
                    input.value = tag.epc;
                    form.append(input);
                }
            }
            list.hidden = false;
            status.classList.add(result.assignable ? "success" : "error");
            status.textContent = result.assignable ? text.found(result.tags.length, result.assignable) : text.none();
            if (result.assignable) {
                assignButton.textContent = text.assign(result.assignable);
                assignButton.hidden = false;
            }
        } catch {
            status.classList.add("error");
            status.textContent = text.server();
        } finally {
            scanButton.disabled = false;
            scanButton.textContent = label;
        }
    });

    // Tell Flask which language to use for the confirmation message
    form.addEventListener("submit", () => {
        form.querySelector('input[name="language"]').value = fr() ? "fr" : "en";
        assignButton.disabled = true;
    });
})();
