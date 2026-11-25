/* Admin dashboard shell: the menu swaps the page shown in the frame, with no full page reload. */
(function () {
    "use strict";
    var frame = document.getElementById("stage");
    var links = Array.prototype.slice.call(document.querySelectorAll("a[data-section][data-src]"));
    links.forEach(function (link) { link.dataset.englishTitle = link.textContent.trim(); });
    function current() {
        var name = location.hash.slice(1) || "account";
        return links.filter(function (a) { return a.dataset.section === name; })[0] ||
            document.querySelector(".side a[data-section]");
    }
    function show() {
        var link = current();
        links.forEach(function (a) { if (a === link) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
        var target = new URL(link.dataset.src, location.href).href;
        if (frame.getAttribute("data-path") !== target) {
            frame.setAttribute("data-path", target);
            frame.src = link.dataset.src;
        }
        document.documentElement.setAttribute("data-en-title", link.dataset.englishTitle + " | Smart Store");
        document.title = window.t(link.dataset.englishTitle) + " | Smart Store";
    }
    window.addEventListener("hashchange", show);
    // The page inside the frame can be changed by its own links and forms (filters, saving a limit).
    // Keep the menu highlight in step with where the frame really is.
    frame.addEventListener("load", function () {
        var path = "", full = "";
        try { path = frame.contentWindow.location.pathname; full = frame.contentWindow.location.href; } catch (e) { return; }
        frame.setAttribute("data-path", full);
        var chosen = links.filter(function (a) { return a.hasAttribute("aria-current"); })[0];
        if (chosen && new URL(chosen.dataset.src, location.href).pathname === path) return;
        var best = null;
        links.forEach(function (a) {
            var p = new URL(a.dataset.src, location.href).pathname;
            if (path === p || (path.indexOf(p) === 0 && p.length > 1 && (!best || p.length > best.p.length))) best = { a: a, p: p };
        });
        if (best) {
            links.forEach(function (a) { if (a === best.a) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
            if (location.hash !== "#" + best.a.dataset.section) history.replaceState(null, "", "#" + best.a.dataset.section);
        }
        try { // keep the frame's language in step (store pages are translated by their own scripts)
            frame.contentDocument.documentElement.lang = document.documentElement.lang;
        } catch (e) { /* ignore */ }
    });
    document.getElementById("logout").addEventListener("click", function () {
        fetch("/api/account/logout", { method: "POST", credentials: "same-origin" })
            .catch(function () {}).then(function () { location.href = "/"; });
    });
    show();
})();
