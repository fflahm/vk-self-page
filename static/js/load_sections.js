async function loadSection(id, file) {
    const response = await fetch(file);
    const html = await response.text();
    document.getElementById(id).innerHTML = html;
}

window.addEventListener("DOMContentLoaded", async () => {

    await loadSection(
        "hero-section",
        "sections/hero.html"
    );

    await loadSection(
        "cognitive-section",
        "sections/cognitive_science.html"
    );

    await loadSection(
        "benchmark-section",
        "sections/benchmark_results.html"
    );

    await loadSection(
        "footer-section",
        "sections/footer.html"
    );

});