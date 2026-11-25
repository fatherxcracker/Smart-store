(() => {
    const screen = document.querySelector("[data-fit-screen], main");
    if (!screen) return;

    const root = document.documentElement;
    const pagers = new Map();
    const narrow = window.matchMedia("(max-width: 600px)");
    const lists = [
        ["tbody", "tr:not(.receipt-row)", 6],
        ["#purchase-history", ".history-row", 4],
        ["#notifications, #notes, #low-list", "li, div", 4],
        ["[data-page-list]", null, 4],
        ["[data-screen-sections]", ":not(script)", 1]
    ];
    let pending = false;

    function paginate(list, selector, size) {
        const rows = Array.from(list.children).filter(row => !selector || row.matches(selector));
        let pager = pagers.get(list);
        if (!pager && rows.length <= size) return;
        if (!pager) {
            const controls = document.createElement("div");
            controls.className = "screen-pager";
            controls.setAttribute("role", "group");
            const previous = document.createElement("button");
            const next = document.createElement("button");
            const status = document.createElement("span");
            status.setAttribute("aria-live", "polite");
            pager = { controls, previous, next, status, page: 0 };
            for (const [button, direction] of [[previous, -1], [next, 1]]) {
                button.type = "button";
                button.addEventListener("click", () => {
                    pager.page += direction;
                    refresh();
                });
            }
            controls.append(previous, status, next);
            (list.closest("table") || list).after(controls);
            pagers.set(list, pager);
        }

        const french = root.lang.startsWith("fr");
        const pages = Math.max(1, Math.ceil(rows.length / size));
        pager.page = Math.min(pager.page, pages - 1);
        pager.controls.hidden = pages === 1 || list.hidden;
        pager.controls.toggleAttribute("data-screen-page-active", pager.page > 0);
        pager.controls.setAttribute("aria-label", french ? "Pagination des résultats" : "Results pagination");
        pager.previous.disabled = pager.page === 0;
        pager.next.disabled = pager.page === pages - 1;
        for (const [element, label] of [
            [pager.previous, french ? "Précédent" : "Previous"],
            [pager.next, french ? "Suivant" : "Next"],
            [pager.status, `Page ${pager.page + 1} / ${pages}`]
        ]) {
            if (element.textContent !== label) element.textContent = label;
        }

        rows.forEach((row, index) => {
            const offPage = Math.floor(index / size) !== pager.page;
            row.toggleAttribute("data-off-screen-page", offPage);
            const detail = row.nextElementSibling;
            if (detail?.matches(".receipt-row, .receipt-details")) {
                detail.toggleAttribute("data-off-screen-page", offPage);
            }
        });
    }

    function refresh() {
        pending = false;
        for (const list of pagers.keys()) {
            if (!list.isConnected) pagers.delete(list);
        }
        for (const [selector, children, size] of lists) {
            for (const list of screen.querySelectorAll(selector)) {
                const pageSize = list.hasAttribute("data-screen-sections") && !narrow.matches
                    ? Infinity : Number(list.dataset.pageList) || size;
                paginate(list, children, pageSize);
            }
        }

        // Measure the screen at its normal size, then use only the scale it needs.
        screen.style.removeProperty("--screen-scale");
        let scale = 1;
        for (let pass = 0; pass < 6; pass++) {
            const extra = root.scrollHeight - root.clientHeight;
            const height = screen.getBoundingClientRect().height;
            if (extra <= 0 || height <= 1) break;
            scale *= Math.max(0.1, (height - extra - 2) / height);
            screen.style.setProperty("--screen-scale", scale);
        }
    }

    function schedule() {
        if (!pending) {
            pending = true;
            requestAnimationFrame(refresh);
        }
    }

    screen.classList.add("screen-fit");
    new MutationObserver(records => {
        if (records.some(record => !record.target.closest?.(".screen-pager") &&
            !(record.target === screen && record.attributeName === "style"))) schedule();
    }).observe(document.body, {
        subtree: true, childList: true, characterData: true,
        attributes: true, attributeFilter: ["class", "hidden", "open", "style", "src"]
    });
    new MutationObserver(schedule).observe(root, { attributes: true, attributeFilter: ["lang"] });
    window.addEventListener("resize", schedule);
    window.addEventListener("load", schedule);
    document.fonts?.ready.then(schedule);
    schedule();
})();
