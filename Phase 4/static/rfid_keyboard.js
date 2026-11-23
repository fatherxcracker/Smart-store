// The CF600 must work in CDC mode (USB serial): the app asks the reader for
// tags, so each scan is controlled and no tag is counted twice.
//
// If the reader is switched to keyboard (HID) mode by mistake, it "types" every
// EPC followed by Enter, over and over, into whatever field has the cursor.
// This guard catches those fast bursts, removes the typed EPC, blocks the Enter
// (so no form is submitted) and shows a warning. Tags typed this way are NEVER
// added to a cart or a delivery.
(() => {
    const MAX_GAP_MS = 50;              // the reader types much faster than a person
    const EPC_PATTERN = /^[0-9A-F]{16,24}$/;   // RFID EPCs; longer than any UPC barcode
    let buffer = "";
    let lastKeyTime = 0;
    let banner = null;

    function warn() {
        const fr = document.documentElement.lang === "fr";
        if (!banner) {
            banner = document.createElement("div");
            banner.className = "hid-mode-warning";
            banner.setAttribute("role", "alert");
            banner.style.cssText =
                "position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:9999;" +
                "max-width:640px;padding:14px 18px;border-radius:10px;background:#fff1f1;" +
                "border:1px solid #f2c9c9;color:#a12b2b;font:600 14px/1.4 system-ui,sans-serif;" +
                "box-shadow:0 12px 30px rgba(0,0,0,.12)";
            document.body.appendChild(banner);
        }
        banner.textContent = fr
            ? "Le lecteur RFID est en mode clavier (HID). Mettez-le en mode CDC (voir README) : les étiquettes tapées ont été ignorées."
            : "The RFID reader is in keyboard (HID) mode. Switch it to CDC mode (see README): typed tags were ignored.";
        clearTimeout(banner.hideTimer);
        banner.hideTimer = setTimeout(() => banner.remove() || (banner = null), 8000);
    }

    document.addEventListener("keydown", event => {
        const now = performance.now();
        if (now - lastKeyTime > MAX_GAP_MS) buffer = "";
        lastKeyTime = now;

        if (event.key === "Enter") {
            const epc = buffer.toUpperCase();
            buffer = "";
            if (!EPC_PATTERN.test(epc)) return;   // a normal Enter typed by a person
            event.preventDefault();
            event.stopPropagation();
            // Remove the characters the reader typed into the focused field
            const field = document.activeElement;
            if (field && "value" in field && field.value.toUpperCase().endsWith(epc)) {
                field.value = field.value.slice(0, -epc.length).replace(/[\r\n]+$/, "");
                field.dispatchEvent(new Event("input", { bubbles: true }));
            }
            warn();
        } else if (event.key.length === 1) {
            buffer += event.key;
        }
    }, true);
})();
