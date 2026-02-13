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
        this.enhanceVisuals();
        this.loadDynamicData();
        this.startRealtimeEngine();
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
            this.loadMarketPage();
        }
    }

    startRealtimeEngine() {
        // Poll every 5 seconds for dashboard/global updates
        this.updateHeartbeat();
        setInterval(() => this.updateHeartbeat(), 5000);

        // Faster heartrate for market page
        setInterval(() => {
            if (window.location.pathname === '/market') this.loadMarketPage();
        }, 15000);
    }

    async updateHeartbeat() {
        if (window.location.pathname !== '/dashboard') return;

        const data = await this.fetchApi('/realtime-updates');
        if (!data || data.error) return;

        this.renderStats(data.stats);
        this.renderMarketWidget(data.market);
        this.renderRecentSalesMini(data.recent_sales);

        const timestampEl = document.getElementById('last-updated');
        if (timestampEl) timestampEl.textContent = `Live: ${data.timestamp}`;
    }

    renderStats(stats) {
        const els = {
            'total-products': stats.total_products,
            'low-stock': stats.low_stock,
            'today-revenue': `$${stats.today_revenue.toFixed(2)}`
        };

        for (const [id, val] of Object.entries(els)) {
            const el = document.getElementById(id);
            if (el && el.textContent != val) {
                el.classList.add('value-update');
                el.textContent = val;
                setTimeout(() => el.classList.remove('value-update'), 1000);

                // Trigger Nexus event for significant changes
                if (id === 'today-revenue' && window.nexusAnimation) {
                    window.nexusAnimation.onEvent('sale', { amount: stats.today_revenue });
                }
            }
        }
    }

    renderMarketWidget(market) {
        const valEl = document.getElementById('market-widget-value');
        const subEl = document.getElementById('market-widget-sub');
        if (!valEl || !market || market.error) return;

        valEl.textContent = market.price.toLocaleString();
        const sign = market.change >= 0 ? '+' : '';
        subEl.innerHTML = `${market.name} <span style="color: ${market.change >= 0 ? 'var(--success-color)' : 'var(--danger-color)'}">(${sign}${market.change_percent}%)</span>`;
    }

    renderRecentSalesMini(sales) {
        const tableBody = document.querySelector('#recent-sales-table tbody');
        if (!tableBody) return;

        const currentRows = tableBody.querySelectorAll('tr');
        const newHtml = sales.map(sale => `
            <tr class="new-row">
                <td>${sale.product_name}</td>
                <td>${sale.date}</td>
                <td>${sale.quantity}</td>
                <td>$${sale.total_price.toFixed(2)}</td>
                <td>${sale.sold_by}</td>
            </tr>
        `).join('') || '<tr><td colspan="5" style="text-align: center;">No recent sales</td></tr>';

        if (tableBody.innerHTML.trim() !== newHtml.trim()) {
            tableBody.innerHTML = newHtml;
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

        // Render Global Market Pulse
        if (data.global_market) {
            this.renderGlobalPulse(data.global_market);
        }

        // Update Security Status
        if (data.security) {
            this.updateSecurityUI(data.security);
        }

        this.loadAIInsights();
    }

    renderGlobalPulse(marketData) {
        const container = document.getElementById('global-pulse-grid');
        if (!container) return;

        container.innerHTML = marketData.map(item => `
            <div class="pulse-card">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span style="font-weight: bold; font-size: 0.85rem;">${item.name}</span>
                    <span style="font-size: 0.75rem; color: var(--text-secondary);">${item.symbol}</span>
                </div>
                <div style="display: flex; align-items: baseline; gap: 8px;">
                    <span style="font-size: 1rem; font-weight: bold;">${item.price.toLocaleString()}</span>
                    <span style="color: var(--${item.color}-color); font-size: 0.75rem; font-weight: 500;">
                        ${item.change > 0 ? '+' : ''}${item.change_percent.toFixed(2)}%
                    </span>
                </div>
            </div>
        `).join('');
    }

    updateSecurityUI(security) {
        const badge = document.getElementById('security-status-badge');
        const scanner = document.getElementById('security-scanner');

        if (badge) {
            badge.textContent = security.status;
            badge.className = `status-badge ${security.status.toLowerCase()}`;
        }

        if (scanner) {
            scanner.style.display = 'block';
            setTimeout(() => scanner.style.display = 'none', 3000); // Pulse effect on update
        }

        if (window.nexusAnimation) {
            if (security.status !== 'SECURE') {
                window.nexusAnimation.onEvent('low_stock'); // Trigger alert state in background
            }
        }
    }

    async loadAIInsights() {
        const marketEl = document.getElementById('ai-market-text');
        const inventoryEl = document.getElementById('ai-inventory-text');

        if (marketEl) {
            const data = await this.fetchApi('/ai/market-insights');
            if (data && data.insights) {
                marketEl.textContent = data.insights;
                marketEl.classList.add('ai-fade-in');
            }
        }

        if (inventoryEl) {
            const data = await this.fetchApi('/ai/inventory-advice');
            if (data && data.advice) {
                // Convert markdown-ish bullets to HTML
                const formattedAdvice = data.advice
                    .replace(/^\d\.\s/gm, '• ') // Normalize numbering to bullets
                    .split('\n')
                    .filter(line => line.trim())
                    .map(line => `<div style="margin-bottom: 5px;">${line}</div>`)
                    .join('');
                inventoryEl.innerHTML = formattedAdvice;
                inventoryEl.classList.add('ai-fade-in');
            }
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
        this.setupMarketSearch();
        this.setupTradeModal();

        // Parallel fetch for speed
        const [globalData, watchlistData, portfolioData] = await Promise.all([
            this.fetchApi('/market'),
            this.fetchApi('/market/watchlist'),
            this.fetchApi('/market/portfolio')
        ]);

        this.renderIndicesTicker(globalData);
        this.renderWatchlistGrid(watchlistData);
        this.renderPortfolio(portfolioData);
        this.renderMarketStats(globalData, watchlistData);
        this.loadNews(); // General market news by default
    }

    async loadNews(symbol = '') {
        const container = document.getElementById('newsFeedContainer');
        if (!container) return;

        const data = await this.fetchApi(`/market/news${symbol ? `?symbol=${symbol}` : ''}`);
        if (!data || data.length === 0) {
            container.innerHTML = '<div class="text-muted" style="text-align: center; padding: 20px; font-size: 0.8rem;">No recent news for this symbol.</div>';
            return;
        }

        container.innerHTML = data.map(news => `
            <a href="${news.link}" target="_blank" class="news-item-link" style="text-decoration: none; color: inherit;">
                <div class="news-item" style="padding: 10px; border-radius: 8px; margin-bottom: 10px; background: rgba(255,255,255,0.02); transition: background 0.2s;">
                    <div class="news-details">
                        <div class="news-title" style="font-size: 0.85rem; font-weight: 500; margin-bottom: 5px; line-height: 1.4;">${news.title}</div>
                        <div class="news-meta" style="font-size: 0.7rem; color: var(--text-secondary);">
                            <span>${news.publisher}</span> • <span>${news.time}</span>
                        </div>
                    </div>
                </div>
            </a>
        `).join('');

        // Hover effect for news items
        container.querySelectorAll('.news-item').forEach(item => {
            item.onmouseenter = () => item.style.background = 'rgba(255,255,255,0.06)';
            item.onmouseleave = () => item.style.background = 'rgba(255,255,255,0.02)';
        });
    }

    renderIndicesTicker(data) {
        const container = document.getElementById('indicesTicker');
        if (!container || !data || data.error) return;

        container.innerHTML = data.map(item => `
            <div class="ticker-item" onclick="platform.setActiveSymbol('${item.symbol}')">
                <span class="ticker-symbol">${item.symbol}</span>
                <span class="ticker-price">${item.price.toLocaleString()}</span>
                <span class="ticker-change ${item.change >= 0 ? 'positive' : 'negative'}">
                    ${item.change >= 0 ? '+' : ''}${item.change_percent}%
                </span>
            </div>
        `).join('') + container.innerHTML; // Simple marquee effect if styled right
    }

    renderWatchlistGrid(data) {
        const container = document.getElementById('userWatchlistGrid');
        if (!container) return;

        if (!data || data.length === 0) {
            container.innerHTML = '<div class="text-muted" style="grid-column: 1/-1; text-align: center; padding: 40px;">No stocks in watchlist. Search to add.</div>';
            return;
        }

        container.innerHTML = data.map(item => `
            <div class="market-card ${this.activeSymbol === item.symbol ? 'active' : ''}" 
                 onclick="platform.setActiveSymbol('${item.symbol}')">
                <div class="market-header">
                    <span class="symbol">${item.symbol}</span>
                    <button class="btn-icon" onclick="event.stopPropagation(); platform.removeFromWatchlist('${item.symbol}')">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="name">${item.name}</div>
                <div class="price">$${item.price.toLocaleString()}</div>
                <div class="change-container ${item.change >= 0 ? 'positive' : 'negative'}">
                    ${item.change >= 0 ? '+' : ''}${item.change_percent}%
                </div>
            </div>
        `).join('');
    }

    renderPortfolio(data) {
        const container = document.getElementById('portfolioSummary');
        if (!container || !data || data.error) return;

        this.userWallet = data.wallet;

        container.innerHTML = `
            <div class="portfolio-stats">
                <div class="portfolio-item">
                    <span class="label">Balance</span>
                    <span class="value">$${data.wallet.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                </div>
                <div class="portfolio-item">
                    <span class="label">Equity</span>
                    <span class="value">$${data.portfolio_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                </div>
                <div class="portfolio-item highlight">
                    <span class="label">Total Value</span>
                    <span class="value">$${data.total_account_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                </div>
            </div>
            
            <div class="holdings-list" style="margin-top: 20px;">
                <h4 style="font-size: 0.8rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: 10px;">Holdings</h4>
                ${data.portfolio.length > 0 ? data.portfolio.map(h => `
                    <div class="holding-row" onclick="platform.setActiveSymbol('${h.symbol}')">
                        <span class="h-symbol">${h.symbol}</span>
                        <span class="h-qty">${h.quantity}</span>
                        <span class="h-pl ${h.pl >= 0 ? 'positive' : 'negative'}">
                            ${h.pl >= 0 ? '+' : ''}$${Math.abs(h.pl).toFixed(2)}
                        </span>
                    </div>
                `).join('') : '<p class="text-muted" style="font-size: 0.8rem;">No holdings yet</p>'}
            </div>
        `;
    }

    renderMarketStats(indices, watchlist) {
        const container = document.getElementById('marketStatsContainer');
        if (!container) return;

        const all = [...(indices || []), ...(watchlist || [])];
        const positiveCount = all.filter(i => (i.change || 0) >= 0).length;
        const negativeCount = all.filter(i => (i.change || 0) < 0).length;

        container.innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${positiveCount} / ${all.length}</div>
                <div class="stat-label">Advancers vs Total</div>
            </div>
            <div class="stat-card" style="margin-top: 10px;">
                <div class="stat-value" style="color: ${positiveCount >= negativeCount ? 'var(--success-color)' : 'var(--danger-color)'}">
                    ${positiveCount >= negativeCount ? 'BULLISH' : 'BEARISH'}
                </div>
                <div class="stat-label">Market Sentiment</div>
            </div>
        `;
    }

    setActiveSymbol(symbol) {
        if (this.activeSymbol === symbol) return;
        this.activeSymbol = symbol;

        // Update selection in grid
        document.querySelectorAll('.market-card').forEach(card => {
            card.classList.toggle('active', card.dataset.symbol === symbol);
        });

        this.initTradingView(symbol);
        this.updateActiveInfo(symbol);
        this.loadNews(symbol);
        this.updateIndicators(symbol);
    }

    async updateIndicators(symbol) {
        const container = document.getElementById('techIndicators');
        if (!container) return;

        container.style.display = 'none';

        const data = await this.fetchApi(`/market/indicators?symbol=${symbol}`);
        if (!data || data.error) return;

        container.style.display = 'flex';
        document.getElementById('smaVal').textContent = data.sma_20 || '--';
        document.getElementById('rsiVal').textContent = data.rsi || '--';

        const signalEl = document.getElementById('signalVal');
        signalEl.textContent = data.signal || '--';

        if (data.signal === 'OVERBOUGHT') {
            signalEl.style.background = 'rgba(239, 68, 68, 0.2)';
            signalEl.style.color = 'var(--danger-color)';
            signalEl.style.border = '1px solid var(--danger-color)';
        } else if (data.signal === 'OVERSOLD') {
            signalEl.style.background = 'rgba(16, 185, 129, 0.2)';
            signalEl.style.color = 'var(--success-color)';
            signalEl.style.border = '1px solid var(--success-color)';
        } else {
            signalEl.style.background = 'rgba(255, 255, 255, 0.05)';
            signalEl.style.color = 'var(--text-secondary)';
            signalEl.style.border = '1px solid var(--glass-border)';
        }
    }

    async updateActiveInfo(symbol) {
        const data = await this.fetchApi(`/market/search?symbol=${symbol}`);
        if (!data || data.error) return;

        document.getElementById('activeSymbolName').textContent = data.name;
        document.getElementById('activeSymbolPrice').textContent = `$${data.price.toLocaleString()}`;

        const changeEl = document.getElementById('activeSymbolChange');
        changeEl.textContent = `${data.change >= 0 ? '+' : ''}${data.change} (${data.change_percent}%)`;
        changeEl.className = `active-change ${data.change >= 0 ? 'positive' : 'negative'}`;

        // Enable trading buttons
        const buyBtn = document.getElementById('buyBtn');
        const sellBtn = document.getElementById('sellBtn');
        if (buyBtn) {
            buyBtn.disabled = false;
            buyBtn.onclick = () => this.openTradeModal(data, 'BUY');
        }
        if (sellBtn) {
            sellBtn.disabled = false;
            sellBtn.onclick = () => this.openTradeModal(data, 'SELL');
        }

        if (window.nexusAnimation) {
            window.nexusAnimation.onEvent('market_update', {
                volatility: Math.abs(data.change_percent),
                isPositive: data.change >= 0
            });
        }
    }

    initTradingView(symbol) {
        const container = document.getElementById('tradingview_widget');
        if (!container || !window.TradingView) return;

        container.innerHTML = ''; // Clear placeholder

        // Format symbol for TV (add exchange prefix if needed, yfinance symbols might need mapping)
        let tvSymbol = symbol;
        if (symbol.startsWith('^')) {
            const indexMap = { '^GSPC': 'SPX', '^IXIC': 'NASDAQ:IXIC', '^DJI': 'DJ:DJI', '^NSEI': 'NSE:NIFTY' };
            tvSymbol = indexMap[symbol] || symbol.replace('^', '');
        } else if (symbol.includes('-USD')) {
            tvSymbol = 'COINBASE:' + symbol.replace('-USD', 'USD');
        }

        new TradingView.widget({
            "autosize": true,
            "symbol": tvSymbol,
            "interval": "D",
            "timezone": "Etc/UTC",
            "theme": localStorage.getItem('theme') || 'dark',
            "style": "1",
            "locale": "en",
            "toolbar_bg": "#f1f3f6",
            "enable_publishing": false,
            "hide_side_toolbar": false,
            "allow_symbol_change": true,
            "container_id": "tradingview_widget"
        });
    }

    setupTradeModal() {
        if (this.tradeModalInitialized) return;

        const modal = document.getElementById('tradeModal');
        const closeBtn = document.querySelector('.close-modal');
        const form = document.getElementById('tradeForm');
        const qtyInput = document.getElementById('tradeQuantity');

        if (!modal || !closeBtn || !form) return;

        closeBtn.onclick = () => modal.style.display = 'none';
        window.onclick = (event) => { if (event.target == modal) modal.style.display = 'none'; };

        qtyInput.oninput = () => {
            const total = (parseFloat(qtyInput.value) || 0) * this.currentTradePrice;
            document.getElementById('tradeTotal').textContent = `$${total.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
        };

        form.onsubmit = async (e) => {
            e.preventDefault();
            const btn = document.getElementById('confirmTradeBtn');
            const originalText = btn.textContent;
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';

            try {
                const response = await fetch(`${this.apiBase}/market/trade`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        symbol: this.currentTradeSymbol,
                        quantity: qtyInput.value,
                        type: this.currentTradeType
                    })
                });
                const result = await response.json();

                if (result.success) {
                    alert(result.message);
                    modal.style.display = 'none';
                    this.loadMarketPage(); // Refresh
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (err) {
                console.error(err);
                alert('Transaction failed');
            } finally {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        };

        this.tradeModalInitialized = true;
    }

    openTradeModal(stock, type) {
        const modal = document.getElementById('tradeModal');
        this.currentTradeSymbol = stock.symbol;
        this.currentTradePrice = stock.price;
        this.currentTradeType = type;

        document.getElementById('tradeModalTitle').textContent = `${type === 'BUY' ? 'Buy' : 'Sell'} ${stock.symbol}`;
        document.getElementById('tradeSymbol').textContent = stock.symbol;
        document.getElementById('tradePrice').textContent = `$${stock.price.toLocaleString()}`;
        document.getElementById('tradeWallet').textContent = `$${this.userWallet.toLocaleString()}`;

        const qtyInput = document.getElementById('tradeQuantity');
        qtyInput.value = 1;
        document.getElementById('tradeTotal').textContent = `$${stock.price.toLocaleString()}`;

        const confirmBtn = document.getElementById('confirmTradeBtn');
        confirmBtn.className = `btn btn-block ${type === 'BUY' ? 'btn-success' : 'btn-danger'}`;
        confirmBtn.textContent = `Confirm ${type}`;

        modal.style.display = 'block';
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
