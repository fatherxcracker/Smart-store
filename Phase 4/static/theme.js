/* Light / dark theme for every page. The choice is remembered in this browser;
   the first visit follows the operating-system setting. Loaded in <head> so the
   page never flashes the wrong colours. */
(function () {
    "use strict";
    var KEY = "smartstore-theme";
    function saved() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
    var LABELS = { en: { dark: "Dark mode", light: "Light mode", aria: "Switch between light and dark mode" },
                   fr: { dark: "Mode sombre", light: "Mode clair", aria: "Passer du mode clair au mode sombre" } };
    function language() { try { return localStorage.getItem("smartstore-language") === "fr" ? "fr" : "en"; } catch (e) { return "en"; } }
    function current() { return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light"; }
    function apply(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        var button = document.getElementById("theme-toggle");
        if (button) {
            var text = LABELS[language()];
            button.textContent = theme === "dark" ? text.light : text.dark;
            button.setAttribute("aria-label", text.aria);
            button.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
        }
    }
    var start = saved() || (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    apply(start);
    document.addEventListener("smartstore-language", function () { apply(current()); });
    function toggle() {
        var next = current() === "dark" ? "light" : "dark";
        apply(next);
        try { localStorage.setItem(KEY, next); } catch (e) { /* private mode: keep it for this page only */ }
    }
    document.addEventListener("DOMContentLoaded", function () {
        var button = document.getElementById("theme-toggle");
        if (!button) {
            // Store pages have no toolbar of ours: add a small floating switch.
            button = document.createElement("button");
            button.id = "theme-toggle";
            button.type = "button";
            button.className = "theme-float";
            button.setAttribute("aria-label", "Switch between light and dark mode");
            document.body.appendChild(button);
        }
        button.addEventListener("click", toggle);
        apply(current());
    });
})();
