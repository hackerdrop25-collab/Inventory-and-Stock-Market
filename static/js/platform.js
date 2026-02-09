/**
 * Platform Core Logic
 * Handles global interactions, table searching, and UI enhancements.
 */

class Platform {
    constructor() {
        this.apiBase = '/api';
        this.init();
    }

    init() {
        this.setupTableSearch();
        this.setupThemeSwitcher();
        this.setupActiveLinks();
        this.enhanceVisuals();
        this.loadDynamicData();
    }

    async fetchApi(endpoint) {
        if (window.nexusAnimation) window.nexusAnimation.onEvent('refresh', { endpoint });
        try {
            const response = await fetch(`${this.apiBase}${endpoint}`);
            if (!response.ok) throw new Error('Network response was not ok');
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            return null;
        }
    }

    /**
     * Determines which page we are on and loads relevant data
     */
    async loadDynamicData() {
        const path = window.location.pathname;
        if (path === '/dashboard') {
            const data = await this.fetchApi('/summary');
            if (data) this.renderDashboard(data);
        } else if (path === '/products') {
            const data = await this.fetchApi('/products');
            if (data) this.renderProducts(data);
        } else if (path === '/sales') {
            const data = await this.fetchApi('/sales');
            if (data) this.renderSales(data);
        } else if (path === '/market') {
            this.setupMarketSearch();
            this.loadMarketPage();
            // Real-time polling every 30s
            setInterval(() => this.loadMarketPage(), 30000);
        }
    }

    renderSales(data) {
        // Populate Product Dropdown
        const productSelect = document.getElementById('productSelect');
        if (productSelect) {
            const currentSelected = productSelect.value;
            productSelect.innerHTML = '<option value="" disabled selected>Choose a product...</option>' +
                data.products.map(p => `
                    <option value="${p._id}" data-price="${p.price}" data-stock="${p.quantity}">
                        ${p.name} (Stock: ${p.quantity})
                    </option>
                `).join('');
            if (currentSelected) productSelect.value = currentSelected;
        }

        // Populate Recent Transactions
        const salesTableBody = document.querySelector('#salesTable tbody');
        if (salesTableBody) {
            const oldTransactionsCount = salesTableBody.querySelectorAll('tr').length;
            salesTableBody.innerHTML = data.transactions.map((txn, index) => `
                <tr>
                    <td>${index + 1}</td>
                    <td>${txn.date}</td>
                    <td>${txn.product_name}</td>
                    <td>${txn.supplier_name || 'N/A'}</td>
                    <td>${txn.customer_name || 'N/A'}</td>
                    <td>${txn.quantity}</td>
                    <td>$${txn.total_price.toFixed(2)}</td>
                    <td>${txn.sold_by}</td>
                </tr>
            `).join('') || '<tr><td colspan="8" style="text-align: center;">No transactions found</td></tr>';

            // Trigger sale pulse if a new transaction appeared
            if (data.transactions.length > oldTransactionsCount && window.nexusAnimation) {
                window.nexusAnimation.onEvent('sale', { amount: data.transactions[0].total_price });
            }
        }
    }

    renderReports(data) {
        // Low Stock Table
        const lowStockBody = document.querySelector('#low-stock-table tbody');
        if (lowStockBody) {
            lowStockBody.innerHTML = data.low_stock.map(item => `
                <tr>
                    <td>${item.name}</td>
                    <td>${item.category}</td>
                    <td style="color: var(--danger-color); font-weight: bold;">${item.quantity}</td>
                    <td>${item.supplier}</td>
                </tr>
            `).join('') || '<tr><td colspan="4" style="text-align: center;">All stock levels are healthy</td></tr>';
        }

        // Render Chart
        this.renderChart(data.chart_labels, data.chart_data);
    }

    renderChart(labels, values) {
        const canvas = document.getElementById('salesChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (window.myChart) window.myChart.destroy();

        window.myChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Revenue ($)',
                    data: values,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointBackgroundColor: '#3b82f6',
                    pointRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: '#94a3b8' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#94a3b8' }
                    }
                }
            }
        });
    }

    renderDashboard(data) {
        const statsValues = document.querySelectorAll('.stat-value');
        if (statsValues.length >= 3) {
            statsValues[0].textContent = data.total_products;
            statsValues[1].textContent = data.low_stock;
            statsValues[2].textContent = `$${data.today_revenue.toFixed(2)}`;

            // Trigger alert if low stock is significant
            if (data.low_stock > 0 && window.nexusAnimation) {
                window.nexusAnimation.onEvent('low_stock', { count: data.low_stock });
            }
        }

        // Fetch Market Data for Widget
        this.fetchApi('/market/search?symbol=^GSPC').then(marketData => {
            const marketValue = document.getElementById('market-widget-value');
            const marketSub = document.getElementById('market-widget-sub');
            if (marketValue && marketData && !marketData.error) {
                marketValue.textContent = marketData.price.toLocaleString();
                const sign = marketData.change >= 0 ? '+' : '';
                marketSub.innerHTML = `S&P 500 <span style="color: ${marketData.change >= 0 ? 'var(--success-color)' : 'var(--danger-color)'}">(${sign}${marketData.change_percent}%)</span>`;

                // Trigger animation update based on market
                if (window.nexusAnimation) {
                    window.nexusAnimation.onEvent('market_update', {
                        volatility: Math.abs(marketData.change_percent),
                        isPositive: marketData.change >= 0
                    });
                }
            } else if (marketValue) {
                marketValue.textContent = "Unavailable";
            }
        });

        const recentSalesBody = document.querySelector('#recent-sales-table tbody');
        if (recentSalesBody) {
            recentSalesBody.innerHTML = data.recent_sales.map(sale => `
                <tr>
                    <td>${sale.product_name}</td>
                    <td>${sale.date}</td>
                    <td>${sale.quantity}</td>
                    <td>$${sale.total_price.toFixed(2)}</td>
                    <td>${sale.sold_by}</td>
                </tr>
            `).join('') || '<tr><td colspan="5" style="text-align: center;">No recent sales</td></tr>';
        }
    }

    renderProducts(data) {
        const productTableBody = document.querySelector('#productTable tbody');
        if (productTableBody) {
            productTableBody.innerHTML = data.products.map((p, index) => `
                <tr>
                    <td>${index + 1}</td>
                    <td>${p.name}</td>
                    <td>${p.category}</td>
                    <td>$${p.price.toFixed(2)}</td>
                    <td>
                        <span class="${p.quantity <= 5 ? 'text-danger' : 'text-success'}">
                            ${p.quantity}
                        </span>
                    </td>
                    <td>${p.supplier}</td>
                    ${window.currentRole === 'Admin' ? `
                    <td>
                        <button class="btn edit-btn" style="padding: 5px 10px; background: rgba(255,255,255,0.1);"
                            data-id="${p._id}" data-name="${p.name}"
                            data-category="${p.category}" data-price="${p.price}"
                            data-quantity="${p.quantity}" data-supplier="${p.supplier}"
                            data-serial-number="${p.serial_number || ''}">
                            <i class="fas fa-edit"></i>
                        </button>
                        <a href="/products/delete/${p._id}" class="btn btn-danger"
                            style="padding: 5px 10px;" onclick="return confirm('Are you sure?')"><i
                                class="fas fa-trash"></i></a>
                    </td>
                    ` : ''}
                </tr>
            `).join('') || '<tr><td colspan="7" style="text-align: center;">No products found</td></tr>';

            // Re-attach listeners for edit buttons
            this.setupEditButtons();
        }
    }

    setupEditButtons() {
        document.querySelectorAll('.edit-btn').forEach(button => {
            button.addEventListener('click', function () {
                const d = this.dataset;
                document.getElementById('editName').value = d.name;
                document.getElementById('editCategory').value = d.category;
                document.getElementById('editPrice').value = d.price;
                document.getElementById('editQuantity').value = d.quantity;
                document.getElementById('editSupplier').value = d.supplier;
                document.getElementById('editSerialNumber').value = d.serialNumber;
                document.getElementById('editForm').action = "/products/update/" + d.id;

                if (window.openModal) window.openModal('editModal');
            });
        });
    }

    /**
     * Adds dynamic search functionality to all tables with a search input
     */
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

    setupMarketSearch() {
        const searchBtn = document.getElementById('marketSearchBtn');
        const searchInput = document.getElementById('marketSearchInput');

        if (searchBtn && searchInput) {
            const performSearch = async () => {
                const symbol = searchInput.value.toUpperCase();
                if (!symbol) return;

                searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

                try {
                    const data = await this.fetchApi(`/market/search?symbol=${symbol}`);
                    searchBtn.innerHTML = 'Search';

                    if (data.error) {
                        alert(data.error);
                    } else {
                        this.renderSearchResult(data);
                    }
                } catch (e) {
                    searchBtn.innerHTML = 'Search';
                    console.error(e);
                }
            };

            searchBtn.addEventListener('click', performSearch);
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') performSearch();
            });
        }
    }

    renderSearchResult(item) {
        const container = document.getElementById('searchResults');
        if (!container) return;

        container.style.display = 'block';
        container.innerHTML = ''; // Clear previous

        const isPositive = item.change >= 0;
        const colorClass = isPositive ? 'text-success' : 'text-danger';
        const sign = isPositive ? '+' : '';

        container.innerHTML = `
            <div class="market-card search-result-card" style="border-color: var(--primary-color);">
                <div class="market-header">
                    <span class="symbol">${item.symbol}</span>
                    <button class="btn btn-sm btn-primary" onclick="platform.addToWatchlist('${item.symbol}')">
                        <i class="fas fa-plus"></i> Watch
                    </button>
                </div>
                <div class="name">${item.name}</div>
                <div class="price">$${item.price.toLocaleString()}</div>
                <div class="change-container ${colorClass}">
                    <span>${sign}${item.change} (${sign}${item.change_percent}%)</span>
                </div>
            </div>
        `;
    }

    async addToWatchlist(symbol) {
        try {
            await fetch(`${this.apiBase}/market/watchlist`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol: symbol })
            });
            // Refresh watchlist
            this.loadMarketPage();
            // Clear search result
            const container = document.getElementById('searchResults');
            if (container) container.style.display = 'none';
        } catch (e) {
            console.error('Error adding to watchlist', e);
        }
    }

    async removeFromWatchlist(symbol) {
        if (!confirm(`Remove ${symbol} from watchlist?`)) return;
        try {
            await fetch(`${this.apiBase}/market/watchlist?symbol=${symbol}`, {
                method: 'DELETE'
            });
            this.loadMarketPage();
        } catch (e) {
            console.error('Error removing from watchlist', e);
        }
    }

    async loadMarketPage() {
        // Load Global Indices
        const globalData = await this.fetchApi('/market');
        const watchlistData = await this.fetchApi('/market/watchlist');

        this.renderMarketList('globalIndices', globalData);
        this.renderMarketList('userWatchlist', watchlistData);
    }

    renderMarketList(elementId, data) {
        const container = document.getElementById(elementId);
        if (!container) return;

        if (!data || data.length === 0) {
            container.innerHTML = '<p class="text-muted">No data available.</p>';
            return;
        }

        container.innerHTML = data.map(item => {
            const isPositive = item.change >= 0;
            const colorClass = isPositive ? 'positive' : 'negative';
            const sign = isPositive ? '+' : '';
            const isWatchlist = elementId === 'userWatchlist';

            return `
            <div class="market-card" data-symbol="${item.symbol}">
                <div class="market-header">
                    <span class="symbol">${item.symbol}</span>
                    <span class="${colorClass}">${sign}${item.change_percent}%</span>
                </div>
                <div class="name">${item.name}</div>
                <div class="price">${item.price.toLocaleString()}</div>
                <div class="change-container ${colorClass}">
                    <span>${sign}${item.change}</span>
                </div>
                ${isWatchlist ? `
                <button class="btn-icon delete-btn" onclick="platform.removeFromWatchlist('${item.symbol}')" 
                    style="position: absolute; top: 10px; right: 10px; opacity: 0.5;">
                    <i class="fas fa-times"></i>
                </button>
                ` : ''}
            </div>
            `;
        }).join('');
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
}

// Initialize on Load
document.addEventListener('DOMContentLoaded', () => {
    window.platform = new Platform();
});
