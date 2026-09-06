// SPDX-License-Identifier: MIT OR Apache-2.0
// Keep mdBook's chapter shortcuts from stealing a focused diagram's scroll keys.
document.addEventListener("keydown", (event) => {
    if (!(event.target instanceof Element) || event.altKey || event.ctrlKey || event.metaKey) {
        return;
    }

    const diagram = event.target.closest(".diagram-scroll");
    if (!diagram || (event.key !== "ArrowLeft" && event.key !== "ArrowRight")) {
        return;
    }

    event.preventDefault();
    event.stopPropagation();
    diagram.scrollBy({ left: event.key === "ArrowRight" ? 80 : -80 });
}, true);
