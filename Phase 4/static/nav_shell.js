/* One sidebar and one top bar for every page.
   The top bar keeps only the language switch, the dark-mode button, the log-out
   button and the Smart Store logo; all page navigation lives in the sidebar.
   Store pages (cart, inventory, users, ...) get both built here, so their old
   header links are hidden and never have to be kept in step by hand. */
(function () {
    "use strict";
    var TEXT = {
        en: { account: "MY ACCOUNT", overview: "Overview", history: "Purchase history", reports: "My purchase reports",
              shop: "Shop", checkout: "Self-checkout", admin: "Administration", dashboard: "Admin dashboard",
              products: "Products & stock", users: "Users", logout: "Log Out", signIn: "Sign in" },
        fr: { account: "MON COMPTE", overview: "Aperçu", history: "Historique d'achats", reports: "Mes rapports d'achats",
              shop: "Magasin", checkout: "Caisse libre-service", admin: "Administration", dashboard: "Tableau de bord administrateur",
              products: "Produits et stock", users: "Utilisateurs", logout: "Déconnexion", signIn: "Se connecter" }
    };
    function lang() { try { return localStorage.getItem("smartstore-language") === "fr" ? "fr" : "en"; } catch (e) { return "en"; } }
    function tr(key) { return TEXT[lang()][key] || TEXT.en[key]; }
    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (text) node.textContent = text;
        return node;
    }
    try { if (window.self !== window.top) return; } catch (e) { return; }

    var top = document.querySelector(".ss-top");
    if (!top) {
        top = el("div", "ss-top");
        // Keep the page's own language switch (its script is already wired to it).
        var langs = document.querySelector(".language-switch");
        if (langs) top.appendChild(langs);
        var theme = document.getElementById("theme-toggle");
        if (!theme) { theme = el("button", "ss-btn", "Dark mode"); theme.id = "theme-toggle"; theme.type = "button"; }
        else theme.className = "ss-btn";
        top.appendChild(theme);
        var out = document.getElementById("logout-button");
        if (!out) {
            out = el("button", "ss-btn logout", tr("logout"));
            out.id = "logout-button"; out.type = "button"; out.hidden = true;
            out.addEventListener("click", function () {
                fetch("/api/account/logout", { method: "POST", credentials: "same-origin" })
                    .catch(function () {}).then(function () { location.href = "/"; });
            });
        } else out.className = "ss-btn logout";
        top.appendChild(out);
        var logo = el("a", "ss-logo");
        logo.href = "/"; logo.innerHTML = "SMART<br>STORE"; logo.setAttribute("aria-label", "Smart Store");
        top.appendChild(logo);
        document.body.insertBefore(top, document.body.firstChild);
    }

    var side = document.querySelector(".ss-side");
    var links = [];
    if (!side) {
        side = el("aside", "ss-side");
        side.setAttribute("aria-label", "Menu");
        var title = el("p", "ss-title", tr("account")); title.dataset.ss = "account"; side.appendChild(title);
        var items = [["overview", "/#dashboard", "auth"], ["history", "/#history", "auth"], ["reports", "/reports/purchases", "auth"],
                     ["signIn", "/", "guest"],
                     ["#shop"], ["checkout", "/cart"], ["#admin", "admin"],
                     ["dashboard", "/reports/", "admin"], ["products", "/inventory", "admin"], ["users", "/admin/users", "admin"]];
        items.forEach(function (item) {
            var node;
            if (item[0].charAt(0) === "#") {
                node = el("p", "ss-group", tr(item[0].slice(1)));
                node.dataset.ss = item[0].slice(1);
            } else {
                node = el("a", "ss-item", tr(item[0]));
                node.href = item[1];
                node.dataset.ss = item[0];
            }
            var flag = item[item.length - 1];
            if (flag === "admin") node.dataset.admin = "1";
            if (flag === "auth") node.dataset.auth = "1";
            if (flag === "guest") { node.dataset.guest = "1"; node.hidden = true; }
            side.appendChild(node);
            links.push(node);
        });
        document.body.insertBefore(side, top.nextSibling);
        // Highlight the entry for the page being shown.
        var path = location.pathname;
        links.forEach(function (node) {
            if (!node.href) return;
            var target = new URL(node.getAttribute("href"), location.href).pathname;
            if (target === path || (target !== "/" && path.indexOf(target) === 0)) node.classList.add("active");
        });
    }
    document.body.classList.add("ss-layout");

    function labels() {
        side.querySelectorAll("[data-ss]").forEach(function (node) { node.textContent = tr(node.dataset.ss); });
        var out = document.getElementById("logout-button");
        if (out && !out.dataset.i18n) out.textContent = tr("logout");
    }
    function role() {
        fetch("/api/account/me", { credentials: "same-origin" })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (customer) {
                var out = document.getElementById("logout-button");
                if (out && !out.dataset.i18n) out.hidden = !customer;
                side.querySelectorAll("[data-admin]").forEach(function (node) { node.hidden = !(customer && customer.is_admin); });
                side.querySelectorAll("[data-auth]").forEach(function (node) { node.hidden = !customer; });
                side.querySelectorAll("[data-guest]").forEach(function (node) { node.hidden = !!customer; });
            }).catch(function () {});
    }
    ["lang-en", "lang-fr"].forEach(function (id) {
        var button = document.getElementById(id);
        if (button) button.addEventListener("click", function () { setTimeout(labels, 0); });
    });
    window.addEventListener("storage", function (e) { if (e.key === "smartstore-language") labels(); });
    document.addEventListener("smartstore-language", labels);
    labels();
    role();
})();
