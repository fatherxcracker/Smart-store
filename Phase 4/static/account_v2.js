/* Account page extras: sidebar, role badge, points ring, statistics and recent purchases.
   Uses its own small English/French dictionary (data-v2 attributes). */
(function () {
    "use strict";
    var TEXT = {
        en: { myAccount: "MY ACCOUNT", navOverview: "Overview", navHistory: "Purchase history", shop: "Shop", navCheckout: "Self-checkout",
              navReports: "My purchase reports", admin: "Administration", navAdmin: "Admin dashboard", navProducts: "Products & stock",
              cardHolder: "MEMBER", since: "SINCE", pts: "points", worth: "Worth", pointsHow: "1 point per full dollar spent. Redeem each point for $0.10 at checkout.",
              statOrders: "Purchases", statSpent: "Total spent", statEarned: "Points earned", statLast: "Last purchase", recent: "RECENT PURCHASES",
              seeAll: "See all", loading: "Loading…", phoneLabel: "Phone", none: "No purchases yet. Scan your items at the self-checkout to start earning points.",
              never: "Never", admin_badge: "Administrator", member_badge: "Member", toNext: "{n} more points to your next $10 reward", reward: "You have a $10 reward ready!" },
        fr: { myAccount: "MON COMPTE", navOverview: "Aperçu", navHistory: "Historique d'achats", shop: "Magasin", navCheckout: "Caisse libre-service",
              navReports: "Mes rapports d'achats", admin: "Administration", navAdmin: "Tableau de bord administrateur", navProducts: "Produits et stock",
              cardHolder: "MEMBRE", since: "DEPUIS", pts: "points", worth: "Vaut", pointsHow: "1 point par dollar entier dépensé. Échangez chaque point contre 0,10 $ à la caisse.",
              statOrders: "Achats", statSpent: "Total dépensé", statEarned: "Points gagnés", statLast: "Dernier achat", recent: "ACHATS RÉCENTS",
              seeAll: "Tout voir", loading: "Chargement…", phoneLabel: "Téléphone", none: "Aucun achat pour l'instant. Scannez vos articles à la caisse libre-service pour gagner des points.",
              never: "Jamais", admin_badge: "Administrateur", member_badge: "Membre", toNext: "Encore {n} points pour votre prochaine récompense de 10 $", reward: "Une récompense de 10 $ vous attend !" }
    };
    var customer = null, purchases = [];
    function lang() { return document.documentElement.lang === "fr" ? "fr" : "en"; }
    function tr(key) { return TEXT[lang()][key] || TEXT.en[key] || key; }
    function money(v) { var s = "$" + Number(v).toFixed(2); return lang() === "fr" ? s.replace(".", ",").replace("$", "") + " $" : s; }
    function when(v) {
        return new Date(String(v).replace(" ", "T") + "Z").toLocaleDateString(lang() === "fr" ? "fr-CA" : "en-CA", { dateStyle: "medium" });
    }
    function $(id) { return document.getElementById(id); }
    function labels() {
        document.querySelectorAll("[data-v2]").forEach(function (el) { el.textContent = tr(el.dataset.v2); });
        render();
    }
    function render() {
        if (!customer) return;
        var badge = $("role-badge");
        badge.hidden = false;
        badge.textContent = customer.is_admin ? tr("admin_badge") : tr("member_badge");
        badge.classList.toggle("admin", !!customer.is_admin);
        $("side-admin").hidden = !customer.is_admin;
        $("customer-phone").textContent = customer.phone || "--";
        $("card-since").textContent = customer.created_at ? when(customer.created_at) : "--";
        var points = Number(customer.points) || 0;
        $("points-ring").style.setProperty("--p", (points % 100));
        $("points-value").textContent = money(points * 0.10);
        $("points-next").textContent = points >= 100 ? tr("reward") : tr("toNext").replace("{n}", 100 - points);
        var spent = purchases.reduce(function (a, p) { return a + Number(p.total); }, 0);
        var earned = purchases.reduce(function (a, p) { return a + Number(p.points_earned || 0); }, 0);
        $("stat-orders").textContent = purchases.length;
        $("stat-spent").textContent = money(spent);
        $("stat-earned").textContent = earned;
        $("stat-last").textContent = purchases.length ? when(purchases[0].created_at) : tr("never");
        var list = $("recent-list");
        list.replaceChildren();
        if (!purchases.length) {
            var empty = document.createElement("li"); empty.className = "muted"; empty.textContent = tr("none"); list.appendChild(empty); return;
        }
        purchases.slice(0, 4).forEach(function (p) {
            var li = document.createElement("li");
            var left = document.createElement("div");
            var a = document.createElement("strong"); a.textContent = p.receipt_number;
            var b = document.createElement("small"); b.textContent = when(p.created_at);
            left.appendChild(a); left.appendChild(b);
            var right = document.createElement("div"); right.className = "right";
            var c = document.createElement("strong"); c.textContent = money(p.total);
            var d = document.createElement("small"); d.textContent = "+" + p.points_earned + " pts";
            right.appendChild(c); right.appendChild(d);
            li.appendChild(left); li.appendChild(right); list.appendChild(li);
        });
    }
    function load() {
        Promise.all([
            fetch("/api/account/me", { credentials: "same-origin" }).then(function (r) { return r.ok ? r.json() : null; }),
            fetch("/api/account/history", { credentials: "same-origin" }).then(function (r) { return r.ok ? r.json() : []; })
        ]).then(function (r) {
            customer = r[0]; purchases = Array.isArray(r[1]) ? r[1] : [];
            showSide(); labels();
        }).catch(function () {});
    }
    function showSide() {
        // The sidebar is always there; the account menu only shows when signed in.
        var out = $("account-nav").hidden;
        $("side-nav").hidden = out; $("side-guest").hidden = !out;
    }
    document.addEventListener("DOMContentLoaded", function () {
        labels();
        new MutationObserver(function () { showSide(); if (!$("account-nav").hidden && !customer) load(); }).observe($("account-nav"), { attributes: true, attributeFilter: ["hidden"] });
        new MutationObserver(labels).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
        $("logout-button").addEventListener("click", function () { customer = null; purchases = []; });
        if (!$("account-nav").hidden) load();
        // Refresh the numbers whenever the dashboard is opened again.
        document.addEventListener("click", function (e) {
            var b = e.target.closest && e.target.closest("[data-page=dashboard]"); if (b && customer) load();
        });
    });
})();
