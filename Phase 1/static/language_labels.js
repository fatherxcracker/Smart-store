// Translate labels that have an explicit French counterpart in the template.
(() => {
    const root = document.documentElement;
    const key = "smartstore-language";
    const choices = [...document.querySelectorAll("[data-language-choice]")];
    const fields = ["text", "aria-label", "title", "placeholder"];
    const labels = fields.flatMap(field => {
        const suffix = field === "text" ? "" : "-" + field;
        return [...document.querySelectorAll(`[data-fr${suffix}]`)].map(element => ({
            element, field,
            english: element.getAttribute("data-en" + suffix) ??
                (field === "text" ? element.textContent : element.getAttribute(field)),
            french: element.getAttribute("data-fr" + suffix)
        }));
    });

    function render() {
        const french = root.lang === "fr";
        for (const { element, field, english, french: translated } of labels) {
            const value = french ? translated : english;
            if (field === "text") {
                if (element.textContent !== value) element.textContent = value;
            } else if (element.getAttribute(field) !== value) {
                element.setAttribute(field, value);
            }
        }
        for (const button of choices) button.setAttribute("aria-pressed", button.dataset.languageChoice === root.lang);
    }

    function setLanguage(value, save) {
        const language = value === "fr" ? "fr" : "en";
        root.lang = language;
        if (save) {
            try { localStorage.setItem(key, language); } catch { /* storage is optional */ }
        }
        render();
        document.dispatchEvent(new CustomEvent("smartstore-language", { detail: language }));
    }

    if (choices.length) {
        let stored;
        try { stored = localStorage.getItem(key); } catch { /* storage is optional */ }
        setLanguage(stored, false);
        for (const button of choices) button.addEventListener("click", () => setLanguage(button.dataset.languageChoice, true));
        window.addEventListener("storage", event => {
            if (event.key === key) setLanguage(event.newValue, false);
        });
    } else {
        render();
        new MutationObserver(render).observe(root, { attributes: true, attributeFilter: ["lang"] });
    }
})();
