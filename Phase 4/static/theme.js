(() => {
    const key = "smartstore-theme";
    const root = document.documentElement;
    let button;

    function updateButton() {
        if (!button) return;
        const dark = root.dataset.theme === "dark";
        const french = root.lang.startsWith("fr");
        button.textContent = french
            ? (dark ? "Mode clair" : "Mode sombre")
            : (dark ? "Light Mode" : "Dark Mode");
    }

    function setTheme(theme) {
        root.dataset.theme = theme === "dark" ? "dark" : "light";
        updateButton();
    }

    try {
        setTheme(localStorage.getItem(key));
    } catch {
        setTheme("light");
    }
    window.addEventListener("storage", event => {
        if (event.key === key) setTheme(event.newValue);
    });

    document.addEventListener("DOMContentLoaded", () => {
        if (root.classList.contains("embedded")) return;
        const header = document.querySelector(".ss-top") ||
            document.querySelector("header nav") || document.querySelector("header");
        if (!header) return;

        button = document.createElement("button");
        button.type = "button";
        button.className = "ss-btn theme-toggle";
        const language = header.querySelector(".language-switch, .langs");
        if (language) language.after(button);
        else header.append(button);
        updateButton();

        button.addEventListener("click", () => {
            setTheme(root.dataset.theme === "dark" ? "light" : "dark");
            try {
                localStorage.setItem(key, root.dataset.theme);
            } catch {
                // The current page can still switch themes when storage is unavailable.
            }
        });
        new MutationObserver(updateButton).observe(root, { attributes: true, attributeFilter: ["lang"] });
    });
})();
