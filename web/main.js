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
    const fetchBtn = document.getElementById('fetch-names-btn');

    let serverData = [];
    let allPriceData = []; // This will be our master list of all items.

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
                selectedServer.realms.forEach((realm, index) => {
                    const option = document.createElement('option');
                    option.value = index;
                    option.textContent = realm.realm;
                    realmSelect.appendChild(option);
                });
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

    fetchBtn.addEventListener('click', async () => {
        fetchBtn.disabled = true;
        fetchBtn.textContent = 'Fetching...';
        await window.pywebview.api.fetch_and_update_item_details();
        fetchBtn.disabled = false;
        fetchBtn.textContent = 'Fetch Item Names';
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

    function renderTable() {
        const tableBody = document.querySelector('#price-table tbody');
        const searchTerm = searchBar.value.toLowerCase();

        const dataToRender = searchTerm
            ? allPriceData.filter(item => item.name.toLowerCase().includes(searchTerm))
            : allPriceData;

        tableBody.innerHTML = ''; // Clear existing data

        if (dataToRender) {
            dataToRender.sort((a, b) => a.name.localeCompare(b.name));
            
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
                tableBody.appendChild(row);
            }
        }
    }

    // This function is exposed to Python. It updates the master data list and re-renders the table.
    function updateMasterData(newData) {
        // This function can be called on startup or after fetching names,
        // so we need to hide the server selection and show the main content.
        document.getElementById('server-selection').style.display = 'none';
        document.getElementById('main-content').style.display = 'block';

        allPriceData = newData;
        renderTable();
        return true; 
    }
    // We expose the function to Python by attaching it to the window object.
    window.updateMasterData = updateMasterData;
});
