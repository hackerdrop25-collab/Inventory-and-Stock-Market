/**
 * Platform Core Logic
 * Handles global interactions, table searching, and UI enhancements.
 */

class Platform {
    constructor() {
        this.init();
    }

    init() {
        this.setupTableSearch();
        this.setupThemeSwitcher();
        this.setupActiveLinks();
        this.enhanceVisuals();
    }

    /**
     * Adds dynamic search functionality to all tables with a search input
     */
    setupTableSearch() {
        const searchInputs = document.querySelectorAll('.table-search');
        searchInputs.forEach(input => {
            input.addEventListener('keyup', (e) => {
                const term = e.target.value.toLowerCase();
                const tableId = e.target.dataset.table;
                const table = document.getElementById(tableId);
                const rows = table.querySelectorAll('tbody tr');

                rows.forEach(row => {
                    const text = row.textContent.toLowerCase();
                    row.style.display = text.includes(term) ? '' : 'none';
                });
            });
        });
    }

    /**
     * Syncs the navbar active state with current URL
     */
    setupActiveLinks() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            if (link.getAttribute('href') === currentPath) {
                link.classList.add('active');
            }
        });
    }

    /**
     * Theme switching logic (supports light, dark, eye-protection)
     */
    setupThemeSwitcher() {
        const themeBtn = document.getElementById('theme-toggle');
        if (!themeBtn) return;

        const themes = ['light', 'dark', 'eye-protection'];
        let currentTheme = localStorage.getItem('theme') || 'dark';

        document.documentElement.setAttribute('data-theme', currentTheme);

        themeBtn.addEventListener('click', () => {
            let nextIndex = (themes.indexOf(currentTheme) + 1) % themes.length;
            currentTheme = themes[nextIndex];
            document.documentElement.setAttribute('data-theme', currentTheme);
            localStorage.setItem('theme', currentTheme);

            // Update icon
            this.updateThemeIcon(currentTheme, themeBtn);
        });

        this.updateThemeIcon(currentTheme, themeBtn);
    }

    updateThemeIcon(theme, btn) {
        const icon = btn.querySelector('i');
        if (!icon) return;

        icon.className = ''; // reset
        if (theme === 'light') icon.className = 'fas fa-sun';
        else if (theme === 'dark') icon.className = 'fas fa-moon';
        else icon.className = 'fas fa-shield-alt';
    }

    /**
     * Minor visual enhancements and micro-interactions
     */
    enhanceVisuals() {
        // Add hover sound or subtle feedback if needed
        // For now, just ensure glass containers are accessible
        document.querySelectorAll('.glass-panel').forEach(panel => {
            panel.addEventListener('mouseenter', () => {
                panel.style.borderColor = 'rgba(255, 255, 255, 0.2)';
            });
            panel.addEventListener('mouseleave', () => {
                panel.style.borderColor = 'rgba(255, 255, 255, 0.1)';
            });
        });
    }
}

// Initialize on Load
document.addEventListener('DOMContentLoaded', () => {
    window.platform = new Platform();
});
