// Translate labels that have an explicit French counterpart in the template.
(() => {
    const root = document.documentElement;
    const key = "smartstore-language";
    const rfidFrench = {
        "Cannot reach the server.": "Impossible de joindre le serveur.",
        "Could not read tags.": "Impossible de lire les étiquettes RFID.",
        "Could not read tag.": "Impossible de lire l'étiquette RFID.",
        "Unknown product.": "Produit inconnu.",
        "The RFID reader is busy. Try again.": "Le lecteur RFID est occupé. Réessayez.",
        "pyserial is not installed. Run: pip install -r requirements.txt": "pyserial n'est pas installé. Exécutez : pip install -r requirements.txt",
        "No RFID tags detected. Put the items on the reader and try again.": "Aucune étiquette RFID détectée. Placez les articles sur le lecteur et réessayez.",
        "No RFID tag detected. Hold the tag on the reader and try again.": "Aucune étiquette RFID détectée. Gardez l'étiquette sur le lecteur et réessayez."
    };

    window.rfidMessageForLanguage = text => {
        if (root.lang !== "fr" || typeof text !== "string") return text;
        if (Object.hasOwn(rfidFrench, text)) return rfidFrench[text];
        return text
            .replace(/^RFID reader not found\..+"RFID reader setup"\.(?: \(tried (.+)\))?$/, (_, port) =>
                "Lecteur RFID introuvable. Branchez-le en mode CDC (USB s\u00e9rie), selon le guide README." +
                (port ? " Port essay\u00e9 : " + port : ""))
            .replace(/^No permission to open (.+)\. Run: sudo usermod -aG dialout \$USER, then log out and in\.$/, (_, port) =>
                "Permission refus\u00e9e pour " + port + ". Ex\u00e9cutez sudo usermod -aG dialout $USER, puis reconnectez-vous.")
            .replace(/^(\d+) tags detected\. Put only one tag on the reader\.$/, "$1 \u00e9tiquettes d\u00e9tect\u00e9es. Placez une seule \u00e9tiquette sur le lecteur.")
            .replace(/^Tag (\S+) is already on an item in stock \("([^"]+)"\)\. Use another tag\.$/, "L'\u00e9tiquette $1 est d\u00e9j\u00e0 utilis\u00e9e sur un article en stock ($2). Utilisez une autre \u00e9tiquette.")
            .replace(/^Tag (\S+) read\. It was sold as "([^"]+)" \(receipt ([^)]+)\)\. Using it on a new item adds that item to stock\.$/, "\u00c9tiquette $1 lue. Elle a \u00e9t\u00e9 vendue avec $2 (re\u00e7u $3). La r\u00e9utiliser sur un nouvel article ajoute celui-ci au stock.")
            .replace(/^Tag (\S+) read\.$/, "\u00c9tiquette $1 lue.");
    };

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
        window.addEventListener("storage", event => {
            if (event.key !== key) return;
            const language = event.newValue === "fr" ? "fr" : "en";
            if (root.lang !== language) document.getElementById("lang-" + language)?.click();
        });
        document.addEventListener("submit", event => {
            const form = event.target;
            if (form.method !== "post") return;
            let field = form.querySelector('input[name="language"]');
            if (!field) {
                field = document.createElement("input");
                field.type = "hidden";
                field.name = "language";
                form.append(field);
            }
            field.value = root.lang === "fr" ? "fr" : "en";
        }, true);
        render();
        new MutationObserver(render).observe(root, { attributes: true, attributeFilter: ["lang"] });
    }
})();
