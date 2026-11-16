// CF600 in keyboard (HID) mode: the reader "types" the EPC of a tag followed by Enter
// instead of answering on the serial port. This catches that fast burst of keystrokes
// anywhere on the page and fires a "rfid-scan" event with the EPC, e.g.
//     document.addEventListener("rfid-scan", event => console.log(event.detail.epc));
(() => {
    const MAX_GAP_MS = 50;  // the reader types much faster than a person
    const EPC_PATTERN = /^[0-9A-F]{8,24}$/;
    let buffer = "";
    let lastKeyTime = 0;

    document.addEventListener("keydown", event => {
        const now = performance.now();
        if (now - lastKeyTime > MAX_GAP_MS) {
            buffer = "";
        }
        lastKeyTime = now;

        if (event.key === "Enter") {
            const epc = buffer.toUpperCase();
            buffer = "";
            if (!EPC_PATTERN.test(epc)) {
                return;  // a normal Enter typed by a person
            }
            // A scan, not a person: don't submit the form
            event.preventDefault();
            event.stopPropagation();
            // Remove the characters the reader already typed into the focused field
            const field = document.activeElement;
            if (field && "value" in field && field.value.toUpperCase().endsWith(epc)) {
                field.value = field.value.slice(0, -epc.length);
            }
            document.dispatchEvent(new CustomEvent("rfid-scan", { detail: { epc } }));
        } else if (event.key.length === 1) {
            buffer += event.key;
        }
    }, true);
})();
