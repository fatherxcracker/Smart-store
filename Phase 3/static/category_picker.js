// Category field (add / edit product): a searchable field limited to the
// store's fixed category list. Typing filters the list; only a category from
// the list can be saved (the server checks it again).
(() => {
    const input = document.getElementById("category");
    const list = document.getElementById("category-options");
    if (!input || !list) return;

    // [{ en: "Beverages", fr: "Boissons" }, ...] from the <option> tags
    const categories = [...list.options].map(option => ({
        en: option.dataset.en,
        fr: option.dataset.fr
    }));

    const fr = () => document.documentElement.lang === "fr";
    const match = text => {
        const value = (text || "").trim().toLowerCase();
        return categories.find(c => c.en.toLowerCase() === value || c.fr.toLowerCase() === value);
    };
    // An old product may keep a category from before the fixed list until it is changed
    const keep = input.dataset.current || "";

    function showLanguage() {
        // Suggestions and the current value in the page's language
        list.innerHTML = "";
        categories.forEach(c => {
            const option = document.createElement("option");
            option.value = fr() ? c.fr : c.en;
            option.dataset.en = c.en;
            option.dataset.fr = c.fr;
            list.appendChild(option);
        });
        const current = match(input.value);
        if (current) input.value = fr() ? current.fr : current.en;
        input.placeholder = fr() ? "Rechercher une catégorie..." : "Search categories...";
        validate();
    }

    function validate() {
        const ok = match(input.value) || (keep && input.value.trim() === keep);
        input.setCustomValidity(ok || !input.value.trim() ? "" :
            (fr() ? "Choisissez une catégorie dans la liste." : "Choose a category from the list."));
    }

    input.addEventListener("input", validate);
    input.addEventListener("change", () => {
        // "beverages" -> "Beverages": snap to the exact name from the list
        const current = match(input.value);
        if (current) input.value = fr() ? current.fr : current.en;
        validate();
    });
    input.closest("form")?.addEventListener("submit", event => {
        validate();
        if (!input.checkValidity()) {
            event.preventDefault();
            input.reportValidity();
        }
    });

    // Follow the EN / FR switch
    document.getElementById("lang-en")?.addEventListener("click", () => setTimeout(showLanguage));
    document.getElementById("lang-fr")?.addEventListener("click", () => setTimeout(showLanguage));
    showLanguage();
})();
