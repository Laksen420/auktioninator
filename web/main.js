document.addEventListener('DOMContentLoaded', () => {
    // This event listener is for pywebview
    window.addEventListener('pywebviewready', () => {
        populateServers();
    });

    const serverSelect = document.getElementById('server-select');
    const realmSelect = document.getElementById('realm-select');
    const confirmBtn = document.getElementById('confirm-selection');
    const serverSelectionDiv = document.getElementById('server-selection');
    const mainContentDiv = document.getElementById('main-content');
    const searchBar = document.getElementById('search-bar');
    const searchBtn = document.getElementById('search-btn');
    const fetchBtn = document.getElementById('fetch-names-btn');

    let serverData = [];
    let allPriceData = []; // This will be our master list of all items.
    let sortColumn = 'name'; // Default sort column
    let sortDirection = 'asc'; // Default sort direction
    let priceChart = null; // To hold the chart instance

    // Tab switching logic
    document.querySelectorAll('.tab-link').forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            
            // Update button active state
            document.querySelectorAll('.tab-link').forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            // Show/hide tab content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.style.display = content.id === tabName ? 'block' : 'none';
            });
        });
    });

    async function populateServers() {
        try {
            serverData = await window.pywebview.api.get_server_list();
            if (serverData && serverData.length > 0) {
                serverData.forEach((server, index) => {
                    const option = document.createElement('option');
                    option.value = index;
                    option.textContent = server.server;
                    serverSelect.appendChild(option);
                });
                populateRealms();
            } else {
                console.error("No server data received from backend.");
            }
        } catch (error) {
            console.error("Failed to fetch server list:", error);
        }
    }

    function populateRealms() {
        const selectedServerIndex = serverSelect.value;
        if (serverData && serverData[selectedServerIndex]) {
            const selectedServer = serverData[selectedServerIndex];
            realmSelect.innerHTML = ''; // Clear previous options
            if (selectedServer.realms && selectedServer.realms.length > 0) {
                let kezanIndex = -1;
                selectedServer.realms.forEach((realm, index) => {
                    const option = document.createElement('option');
                    option.value = index;
                    option.textContent = realm.realm;
                    realmSelect.appendChild(option);
                    // Check for Kezan, case-insensitive
                    if (realm.realm.toLowerCase() === 'kezan') {
                        kezanIndex = index;
                    }
                });
                
                // If Kezan was found, set it as the selected realm
                if (kezanIndex !== -1) {
                    realmSelect.value = kezanIndex;
                }
            }
        }
    }

    serverSelect.addEventListener('change', populateRealms);

    confirmBtn.addEventListener('click', async () => {
        const selectedServerIndex = serverSelect.value;
        const selectedRealmIndex = realmSelect.value;

        if (selectedServerIndex !== "" && selectedRealmIndex !== "") {
            const server = serverData[selectedServerIndex];
            const realm = server.realms[selectedRealmIndex];

            // Show a loading indicator
            serverSelectionDiv.innerHTML = '<h2>Loading initial auction data...</h2>';

            // Tell the backend to start fetching. The backend will call `updateMasterData` when it's ready.
            window.pywebview.api.set_server_and_realm(server.server_slug, realm.realm_slug);
        }
    });

    // Add event listeners for sorting
    document.querySelectorAll('.sortable-header th').forEach(header => {
        header.addEventListener('click', () => {
            const newSortColumn = header.dataset.sortBy;
            if (sortColumn === newSortColumn) {
                sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                sortColumn = newSortColumn;
                sortDirection = 'asc';
            }
            renderTable();
        });
    });

    fetchBtn.addEventListener('click', async () => {
        fetchBtn.disabled = true;
        fetchBtn.textContent = 'Fetching...';
        await window.pywebview.api.fetch_and_update_item_details();
        fetchBtn.disabled = false;
        fetchBtn.textContent = 'Fetch Item Names';
    });

    searchBtn.addEventListener('click', async () => {
        const searchTerm = searchBar.value.trim();
        if (!searchTerm) {
            return;
        }

        searchBtn.disabled = true;
        // Simple text loading state
        const originalContent = searchBtn.innerHTML;
        searchBtn.textContent = '...';

        try {
            const searchResults = await window.pywebview.api.search_item(searchTerm);
            
            if (searchResults && searchResults.length > 0) {
                const existingIds = new Set(allPriceData.map(item => item.id));
                
                searchResults.forEach(newItem => {
                    if (!existingIds.has(newItem.id)) {
                        allPriceData.push(newItem);
                        existingIds.add(newItem.id); // Add to set to handle duplicates within searchResults
                    }
                });
                
                // Re-render the table. The existing filter logic will pick up the new items.
                renderTable();
            } else {
                // Optional: handle no results found, e.g., show a message
                console.log("No new items found from search.");
            }

        } catch (error) {
            console.error("Error during item search:", error);
        } finally {
            searchBtn.disabled = false;
            searchBtn.innerHTML = originalContent; // Restore original SVG
        }
    });

    searchBar.addEventListener('input', renderTable);

    function formatPrice(copper) {
        const gold = Math.floor(copper / 10000);
        const silver = Math.floor((copper % 10000) / 100);
        const bronze = copper % 100;

        let html = '';
        if (gold > 0) {
            html += `<span class="gold">${gold}g</span> `;
        }
        if (silver > 0) {
            html += `<span class="silver">${silver}s</span> `;
        }
        html += `<span class="bronze">${bronze}c</span>`;

        return html;
    }

    function updatePriceDistributionChart(priceData) {
        const ctx = document.getElementById('price-distribution-chart').getContext('2d');
        
        const priceRanges = {
            "0-1g": 0,
            "1-10g": 0,
            "10-50g": 0,
            "50-100g": 0,
            "100-500g": 0,
            "500g+": 0
        };

        priceData.forEach(item => {
            const gold = item.price / 10000;
            if (gold < 1) priceRanges["0-1g"]++;
            else if (gold < 10) priceRanges["1-10g"]++;
            else if (gold < 50) priceRanges["10-50g"]++;
            else if (gold < 100) priceRanges["50-100g"]++;
            else if (gold < 500) priceRanges["100-500g"]++;
            else priceRanges["500g+"]++;
        });

        if (priceChart) {
            priceChart.destroy();
        }

        priceChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: Object.keys(priceRanges),
                datasets: [{
                    label: '# of Items',
                    data: Object.values(priceRanges),
                    backgroundColor: 'rgba(0, 170, 255, 0.5)',
                    borderColor: 'rgba(0, 170, 255, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    function renderTable() {
        const tableBody = document.querySelector('#price-table tbody');
        const searchTerm = searchBar.value.toLowerCase();

        const dataToRender = searchTerm
            ? allPriceData.filter(item => 
                item.name.toLowerCase().includes(searchTerm) ||
                item.id.toString().includes(searchTerm)
              )
            : allPriceData;

        tableBody.innerHTML = ''; // Clear existing data

        if (dataToRender) {
            // Sorting logic
            dataToRender.sort((a, b) => {
                let aValue = a[sortColumn];
                let bValue = b[sortColumn];
                
                // For name and icon, sort alphabetically
                if (typeof aValue === 'string') {
                    aValue = aValue.toLowerCase();
                    bValue = bValue.toLowerCase();
                }

                if (aValue < bValue) {
                    return sortDirection === 'asc' ? -1 : 1;
                }
                if (aValue > bValue) {
                    return sortDirection === 'asc' ? 1 : -1;
                }
                return 0;
            });

            // Update header classes for sort indicators
            document.querySelectorAll('.sortable-header th').forEach(th => {
                th.classList.remove('sorted-asc', 'sorted-desc');
                if (th.dataset.sortBy === sortColumn) {
                    th.classList.add(sortDirection === 'asc' ? 'sorted-asc' : 'sorted-desc');
                }
            });
            
            for (const item of dataToRender) {
                const row = document.createElement('tr');
                const iconName = item.icon.toLowerCase().replace(/\\/g, '/').split('/').pop();
                const iconUrl = `https://wow.zamimg.com/images/wow/icons/large/${iconName}.jpg`;
                
                row.innerHTML = `
                    <td><img src="${iconUrl}" class="item-icon" alt="${item.name}"></td>
                    <td class="q${item.quality}">${item.name}</td>
                    <td>${item.id}</td>
                    <td>${formatPrice(item.price)}</td>
                `;
                row.dataset.itemId = item.id; // Add data-item-id attribute
                tableBody.appendChild(row);
            }
        }
    }

    // This function is exposed to Python. It updates the master data list and re-renders the table.
    function updateMasterData(newData) {
        // This function can be called on startup or after fetching names,
        // so we need to hide the server selection and show the main content.
        document.getElementById('server-selection').style.display = 'none';
        document.getElementById('app-container').style.display = 'block';

        allPriceData = newData;
        renderTable();
        updatePriceDistributionChart(allPriceData); // Update the chart
        return true; 
    }
    // We expose the function to Python by attaching it to the window object.
    window.updateMasterData = updateMasterData;

    // --- Price History Chart Logic ---

    const tableBody = document.querySelector('#price-table tbody');

    tableBody.addEventListener('click', async (event) => {
        let targetRow = event.target.closest('tr');
        if (!targetRow || !targetRow.dataset.itemId) return; // Not a valid item row

        // Toggle details row
        const existingDetailsRow = targetRow.nextElementSibling;
        if (existingDetailsRow && existingDetailsRow.classList.contains('details-row')) {
            existingDetailsRow.remove();
            targetRow.classList.remove('active-row');
            return;
        }

        // Remove any other open details rows
        document.querySelectorAll('.details-row').forEach(row => row.remove());
        document.querySelectorAll('.active-row').forEach(row => row.classList.remove('active-row'));
        
        targetRow.classList.add('active-row');

        const itemId = targetRow.dataset.itemId;
        const template = document.getElementById('details-row-template');
        const detailsRow = template.content.cloneNode(true);
        targetRow.after(detailsRow);

        const canvas = targetRow.nextElementSibling.querySelector('.price-history-chart');
        
        try {
            const historyData = await window.pywebview.api.get_item_price_history(itemId);
            if (historyData && historyData.length > 0) {
                renderPriceHistoryChart(canvas, historyData);
            } else {
                canvas.getContext('2d').fillText('No price history available.', 10, 50);
            }
        } catch (error) {
            console.error(`Failed to fetch or render price history for item ${itemId}:`, error);
            canvas.getContext('2d').fillText('Error loading chart.', 10, 50);
        }
    });

    function renderPriceHistoryChart(canvas, historyData) {
        const timestamps = historyData.map(d => new Date(d.timestamp));
        const minPrices = historyData.map(d => d.min_buyout_price / 10000); // Convert to gold

        new Chart(canvas, {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: 'Minimum Buyout Price (Gold)',
                    data: minPrices,
                    borderColor: 'gold',
                    backgroundColor: 'rgba(255, 215, 0, 0.1)',
                    tension: 0.1
                }]
            },
            options: {
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'day',
                            tooltipFormat: 'MMM D, YYYY h:mm a'
                        },
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: 'Price (Gold)'
                        }
                    }
                }
            }
        });
    }
});
