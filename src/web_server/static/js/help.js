const search = document.getElementById("search");
const cards = document.querySelectorAll(".command-card");
const sections = document.querySelectorAll(".command-group");
const noResults = document.getElementById("no-results");
const navLinks = document.querySelectorAll(".group-link");

search.addEventListener("input", () => {
    const q = search.value.toLowerCase().trim();
    let visible = 0;

    cards.forEach(card => {
        const matches = !q
            || card.dataset.name.includes(q)
            || card.dataset.aliases.includes(q)
            || card.dataset.desc.includes(q);
        card.style.display = matches ? "" : "none";
        if (matches) visible++;
    });

    sections.forEach(section => {
        const anyVisible = [...section.querySelectorAll(".command-card")]
            .some(c => c.style.display !== "none");
        section.style.display = anyVisible ? "" : "none";
    });

    noResults.style.display = visible === 0 ? "" : "none";
});

const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const id = entry.target.id;
            navLinks.forEach(link => {
                link.classList.toggle("active", link.getAttribute("href") === `#${id}`);
            });
        }
    });
}, {
    rootMargin: "-15% 0px -85% 0px",
});

sections.forEach(s => observer.observe(s));
