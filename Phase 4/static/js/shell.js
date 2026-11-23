/* Admin dashboard shell: the menu swaps the page shown in the frame, with no full page reload. */
(function () {
    "use strict";
    var frame = document.getElementById("stage");
    var links = Array.prototype.slice.call(document.querySelectorAll(".side a[data-section]"));
    function current() {
        var name = (location.hash || "").replace("#", "");
        return links.filter(function (a) { return a.dataset.section === name; })[0] || links[0];
    }
    function show() {
        var link = current();
        links.forEach(function (a) { if (a === link) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
        var target = new URL(link.dataset.src, location.href).pathname;
        if (frame.getAttribute("data-path") !== target) {
            frame.setAttribute("data-path", target);
            frame.src = link.dataset.src;
        }
        var title = link.textContent.trim();
        document.title = title + " | Smart Store";
    }
    window.addEventListener("hashchange", show);
    // The page inside the frame can be changed by its own links and forms (filters, saving a limit).
    // Keep the menu highlight in step with where the frame really is.
    frame.addEventListener("load", function () {
        var path = "";
        try { path = frame.contentWindow.location.pathname; } catch (e) { return; }
        frame.setAttribute("data-path", path);
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
    // Language: Phase 4 pages follow the shared setting live; store pages need a reload to pick it up.
    var ready = false;
    frame.addEventListener("load", function () { ready = true; });
    document.addEventListener("smartstore-language", function () {
        if (!ready) return;
        try {
            var path = frame.contentWindow.location.pathname;
            if (path.indexOf("/reports") !== 0 && path.indexOf("/monitoring") !== 0 && path.indexOf("/sensors") !== 0) frame.contentWindow.location.reload();
        } catch (e) { /* ignore */ }
    });
    document.getElementById("logout").addEventListener("click", function () {
        fetch("/api/account/logout", { method: "POST", credentials: "same-origin" })
            .catch(function () {}).then(function () { location.href = "/"; });
    });
    show();
})();
