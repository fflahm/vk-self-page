async function loadSection(id, file) {
    const response = await fetch(file);
    const html = await response.text();
    document.getElementById(id).innerHTML = html;
}

function initOverviewInteractions() {
    const root = document.querySelector(".overview-interactive");
    if (!root) {
        return;
    }

    const triggers = root.querySelectorAll("[data-overview-target]");
    const details = root.querySelectorAll("[data-overview-detail]");

    const setActiveOverview = (target) => {
        triggers.forEach((trigger) => {
            const isActive = trigger.dataset.overviewTarget === target;
            trigger.classList.toggle("is-active", isActive);
            trigger.setAttribute("aria-pressed", String(isActive));
        });

        details.forEach((detail) => {
            detail.classList.toggle("is-active", detail.dataset.overviewDetail === target);
        });

        root.classList.add("is-ready");
    };

    triggers.forEach((trigger) => {
        trigger.setAttribute("role", "button");
        trigger.setAttribute("aria-pressed", "false");

        trigger.addEventListener("click", () => {
            setActiveOverview(trigger.dataset.overviewTarget);
        });

        trigger.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                setActiveOverview(trigger.dataset.overviewTarget);
            }
        });
    });

    setActiveOverview("self-1");
}

window.addEventListener("DOMContentLoaded", async () => {

    await loadSection(
        "hero-section",
        "sections/hero.html"
    );

    // await loadSection(
    //     "bg-section",
    //     "sections/bg.html"
    // );

    await loadSection(
        "overview-section",
        "sections/overview.html"
    );
    initOverviewInteractions();

    await loadSection(
        "paradigm-section",
        "sections/paradigm.html"
    );

    await loadSection(
        "benchmark-section",
        "sections/benchmark_results.html"
    );

    const script = document.createElement("script");
    script.src = "static/js/benchmark_table.js";
    script.type = "module";

    document.body.appendChild(script);

    await loadSection(
        "footer-section",
        "sections/footer.html"
    );

});