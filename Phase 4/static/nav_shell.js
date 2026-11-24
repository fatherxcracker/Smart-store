/* Build the shared header and sidebar for store pages. */
(function () {
    "use strict";
    var TEXT = {
        en: { account: "MY ACCOUNT", overview: "Overview", history: "Purchase history", reports: "My purchase reports",
              profile: "My profile", checkout: "Self-checkout", admin: "Administration", dashboard: "Admin dashboard",
              products: "Products & stock", users: "Users", logout: "Log Out", signIn: "Sign in" },
        fr: { account: "MON COMPTE", overview: "Aperçu", history: "Historique d'achats", reports: "Mes rapports d'achats",
              profile: "Mon profil", checkout: "Caisse libre-service", admin: "Administration", dashboard: "Tableau de bord administrateur",
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
        var logo = el("a", "ss-logo");
        logo.href = "/"; logo.innerHTML = "SMART<br>STORE"; logo.setAttribute("aria-label", "Smart Store");
        top.appendChild(logo);
        var signIn = el("a", "ss-btn", tr("signIn"));
        signIn.href = "/";
        signIn.dataset.ss = "signIn";
        top.appendChild(signIn);
        // Keep the page's own language switch (its script is already wired to it).
        var langs = document.querySelector(".language-switch");
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
        if (langs) top.appendChild(langs);
        var checkout = el("a", "ss-btn ss-checkout", tr("checkout"));
        checkout.href = "/cart";
        checkout.dataset.ss = "checkout";
        top.appendChild(checkout);
        document.body.insertBefore(top, document.body.firstChild);
    }

    var side = document.querySelector(".ss-side");
    var links = [];
    if (!side) {
        side = el("aside", "ss-side");
        side.setAttribute("aria-label", "Menu");
        side.hidden = true;
        var title = el("p", "ss-title", tr("account")); title.dataset.ss = "account"; side.appendChild(title);
        var items = [["overview", "/#dashboard", "auth"], ["history", "/#history", "auth"], ["reports", "/reports/purchases", "auth"],
                     ["profile", "/#profile", "auth"],
                     ["#admin", "admin"],
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
            if (flag === "admin") node.hidden = true;
            side.appendChild(node);
            links.push(node);
        });
        top.after(side);
    }
    document.body.classList.add("ss-layout");

    function highlight(accountPage) {
        var path = location.pathname;
        var section = accountPage || location.hash || "#dashboard";
        if (section.charAt(0) !== "#") section = "#" + section;
        links.forEach(function (node) {
            if (!node.href) return;
            var target = new URL(node.href);
            var active = target.pathname === "/" ? path === "/" && target.hash === section :
                path === target.pathname || path.startsWith(target.pathname.replace(/\/$/, "") + "/");
            node.classList.toggle("active", active);
            if (active) node.setAttribute("aria-current", "page");
            else node.removeAttribute("aria-current");
        });
    }

    var accountNav = document.querySelector(".customer-account #account-nav");
    if (accountNav) {
        function syncAccountSidebar() { side.hidden = accountNav.hidden; }
        new MutationObserver(syncAccountSidebar).observe(accountNav, { attributes: true, attributeFilter: ["hidden"] });
        document.addEventListener("smartstore-account-page", function (event) { highlight(event.detail); });
        syncAccountSidebar();
    }
    window.addEventListener("hashchange", function () { highlight(); });
    highlight();

    function labels() {
        top.querySelectorAll("[data-ss]").forEach(function (node) { node.textContent = tr(node.dataset.ss); });
        if (side) side.querySelectorAll("[data-ss]").forEach(function (node) { node.textContent = tr(node.dataset.ss); });
        var out = document.getElementById("logout-button");
        if (out && !out.dataset.i18n) out.textContent = tr("logout");
    }
    function role() {
        fetch("/api/account/me", { credentials: "same-origin" })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (customer) {
                var out = document.getElementById("logout-button");
                if (out && !out.dataset.i18n) out.hidden = !customer;
                document.querySelectorAll(".ss-top [data-admin], .ss-side [data-admin]").forEach(function (node) { node.hidden = !(customer && customer.is_admin); });
                if (!side) return;
                if (signIn) signIn.hidden = !!customer;
                if (!accountNav) side.hidden = !customer;
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
