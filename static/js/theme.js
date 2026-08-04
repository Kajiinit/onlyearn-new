(function () {
    const root = document.documentElement;
    const themeButton = document.querySelector("[data-theme-toggle]");
    const menuButton = document.querySelector("[data-menu-toggle]");
    const menu = document.querySelector("[data-menu]");
    const savedTheme = localStorage.getItem("onlyearn-theme");

    if (savedTheme === "dark") {
        root.classList.add("dark");
    }

    if (themeButton) {
        themeButton.addEventListener("click", function () {
            root.classList.toggle("dark");
            localStorage.setItem(
                "onlyearn-theme",
                root.classList.contains("dark") ? "dark" : "light"
            );
        });
    }

    if (menuButton && menu) {
        menuButton.addEventListener("click", function () {
            menu.classList.toggle("open");
        });
    }
})();
