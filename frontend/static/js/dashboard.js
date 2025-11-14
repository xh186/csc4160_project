// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 从 localStorage 获取用户名
    const username = localStorage.getItem('username');
    if (!username) {
        // 如果没有用户名，重定向到登录页面
        window.location.href = '/';
        return;
    }
    
    // 显示用户名
    document.getElementById('username').textContent = username;
    
    // 加载用户Cookie
    loadUserCookie();
    
    // 加载监控列表
    loadWatchlist();
    
    // 退出登录按钮事件
    document.getElementById('logout-btn').addEventListener('click', function() {
        localStorage.removeItem('username');
        window.location.href = '/';
    });
    
    // 名称搜索按钮事件
    const searchBtn = document.getElementById('search-name-btn');
    if (searchBtn) {
        searchBtn.addEventListener('click', function() {
            searchByName();
        });
    }

    // 添加商品监控表单提交事件
    document.getElementById('query-form').addEventListener('submit', function(e) {
        e.preventDefault();
        addToWatchlistByName();
    });
    
    // 刷新监控列表按钮事件
    document.getElementById('refresh-watchlist').addEventListener('click', function() {
        loadWatchlist();
    });
    
    // 更新Cookie按钮事件
    document.getElementById('update-cookie-btn').addEventListener('click', function() {
        updateUserCookie();
    });
    
    // 开始查询按钮事件
    document.getElementById('start-query-btn').addEventListener('click', function() {
        startQuery();
    });

    const stopBtn = document.getElementById('stop-query-btn');
    if (stopBtn) {
        stopBtn.addEventListener('click', function() {
            stopQuery();
        });
    }
});

// 加载用户Cookie
function loadUserCookie() {
    const username = localStorage.getItem('username');
    
    fetch(`/api/get_cookie?username=${encodeURIComponent(username)}`)
    .then(response => response.json())
    .then(data => {
        const cookieElement = document.getElementById('current-cookie');
        if (data.status === 'success') {
            // 完整显示cookie
            const cookie = data.cookie;
            cookieElement.textContent = cookie || 'Not set';
        } else {
            cookieElement.textContent = 'Not set';
        }
    })
    .catch(error => {
        document.getElementById('current-cookie').textContent = 'Load failed';
    });
}

// 更新用户Cookie
function updateUserCookie() {
    const username = localStorage.getItem('username');
    const newCookie = document.getElementById('new-cookie').value.trim();
    
    if (!newCookie) {
        const messageElement = document.getElementById('cookie-message');
        messageElement.textContent = 'Please enter a valid Cookie';
        messageElement.className = 'message error';
        return;
    }
    
    fetch('/api/update_cookie', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            username: username,
            buff_cookies: newCookie
        })
    })
    .then(response => response.json())
    .then(data => {
        const messageElement = document.getElementById('cookie-message');
        if (data.status === 'success') {
            messageElement.textContent = 'Cookie updated successfully';
            messageElement.className = 'message success';
            document.getElementById('new-cookie').value = '';
            loadUserCookie();
        } else {
            messageElement.textContent = data.message || 'Failed to update Cookie';
            messageElement.className = 'message error';
        }
    })
    .catch(error => {
        const messageElement = document.getElementById('cookie-message');
        messageElement.textContent = 'Request failed: ' + error.message;
        messageElement.className = 'message error';
    });
}

// 开始查询功能
function startQuery() {
    const username = localStorage.getItem('username');
    const queryStatusElement = document.getElementById('query-status');
    
    queryStatusElement.textContent = 'Starting query...';
    queryStatusElement.className = 'message info';
    
    fetch('/api/start_query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            username: username
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            queryStatusElement.textContent = 'Query started; the system will check and notify at configured frequency';
            queryStatusElement.className = 'message success';
        } else {
            queryStatusElement.textContent = data.message || 'Failed to start query';
            queryStatusElement.className = 'message error';
        }
    })
    .catch(error => {
        queryStatusElement.textContent = 'Failed to start query, please check network connection';
        queryStatusElement.className = 'message error';
    });
}

// 名称搜索
function searchByName() {
    const username = localStorage.getItem('username');
    const keyword = document.getElementById('item-name').value.trim();
    const game = document.getElementById('game').value;
    const messageElement = document.getElementById('search-message');
    const select = document.getElementById('candidate-names');

    if (!keyword) {
        messageElement.textContent = 'Please enter an item name before searching';
        messageElement.className = 'message error';
        return;
    }

    messageElement.textContent = 'Searching...';
    messageElement.className = 'message info';

    fetch('/api/search_by_name', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            username: username,
            keyword: keyword,
            game: game,
            limit: 10
        })
    })
    .then(resp => resp.json())
    .then(data => {
        if (data.status === 'success') {
            const names = Array.isArray(data.names) ? data.names : [];
            // 清空并填充候选
            select.innerHTML = '';
            if (names.length === 0) {
                const opt = document.createElement('option');
                opt.value = '';
                opt.textContent = 'No matches found';
                select.appendChild(opt);
                messageElement.textContent = 'No matches found';
                messageElement.className = 'message info';
                return;
            }
            names.forEach(n => {
                const opt = document.createElement('option');
                opt.value = n;
                opt.textContent = n;
                select.appendChild(opt);
            });
            messageElement.textContent = `Found ${names.length} candidates; please select one`; 
            messageElement.className = 'message success';
        } else {
            messageElement.textContent = data.message || 'Search failed';
            messageElement.className = 'message error';
        }
    })
    .catch(err => {
        messageElement.textContent = 'Search request failed: ' + err.message;
        messageElement.className = 'message error';
    });
}

// 通过选定名称添加到监控列表
function addToWatchlistByName() {
    const username = localStorage.getItem('username');
    const formData = new FormData(document.getElementById('query-form'));
    const selectedName = document.getElementById('candidate-names').value;
    const game = formData.get('game');
    const messageElement = document.getElementById('query-message');

    if (!selectedName) {
        messageElement.textContent = 'Please select a candidate name before adding';
        messageElement.className = 'message error';
        return;
    }

    const payload = {
        username: username,
        selected_name: selectedName,
        game: game,
        sort_by: formData.get('sort_by')
    };

    // 可选价格
    if (formData.get('price_min')) {
        payload.price_min = parseFloat(formData.get('price_min'));
    }
    if (formData.get('price_max')) {
        payload.price_max = parseFloat(formData.get('price_max'));
    }

    fetch('/api/add_watchlist_by_name', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
    .then(resp => resp.json())
    .then(data => {
        if (data.status === 'success') {
            messageElement.textContent = data.message + (data.goods_id ? ` (ID: ${data.goods_id})` : '');
            messageElement.className = 'message success';
            document.getElementById('query-form').reset();
            // 重置候选列表
            const select = document.getElementById('candidate-names');
            select.innerHTML = '';
            const opt = document.createElement('option');
            opt.value = '';
            opt.textContent = 'Please search and select first';
            select.appendChild(opt);
            // 刷新监控列表
            loadWatchlist();
        } else {
            messageElement.textContent = data.message || 'Add failed';
            messageElement.className = 'message error';
        }
    })
    .catch(err => {
        messageElement.textContent = 'Request failed: ' + err.message;
        messageElement.className = 'message error';
    });
}

// 加载监控列表
function loadWatchlist() {
    const username = localStorage.getItem('username');
    
    // 发送请求到后端获取监控列表
    fetch(`/api/get_watchlist?username=${encodeURIComponent(username)}`)
    .then(response => response.json())
    .then(data => {
        const watchlistBody = document.getElementById('watchlist-body');
        const messageElement = document.getElementById('watchlist-message');
        
        if (data.status === 'success') {
            // 清空现有列表
            watchlistBody.innerHTML = '';
            
            // 检查是否有监控项
            if (Object.keys(data.watchlist).length === 0) {
                messageElement.textContent = 'Watchlist is empty';
                messageElement.className = 'message info';
                return;
            }
            
            // 添加每个监控项到表格
            Object.entries(data.watchlist).forEach(([id, item]) => {
                const row = document.createElement('tr');
                
                // ID 列
                const idCell = document.createElement('td');
                idCell.textContent = id;
                row.appendChild(idCell);
                
                // 名称列 (显示物品名称)
                const nameCell = document.createElement('td');
                nameCell.textContent = item.item_name || item.goods_id || id; // 优先显示物品名称
                row.appendChild(nameCell);
                
                // 游戏列
                const gameCell = document.createElement('td');
                gameCell.textContent = item.game || '-';
                row.appendChild(gameCell);
                
                // 上限列
                const maxPriceCell = document.createElement('td');
                let maxPrice = 'No limit';
                
                // 下限列
                const minPriceCell = document.createElement('td');
                let minPrice = 'No limit';
                
                // 解析conditions数组
                if (item.conditions && Array.isArray(item.conditions)) {
                    item.conditions.forEach(condition => {
                        if (condition.condition_type === 'price_threshold' && 
                            condition.target_field === 'sell_min_price') {
                            
                            if (condition.operator === '<') {
                                maxPrice = `¥${condition.value}`;
                            } else if (condition.operator === '>') {
                                minPrice = `¥${condition.value}`;
                            }
                        }
                    });
                }
                
                maxPriceCell.textContent = maxPrice;
                row.appendChild(maxPriceCell);
                
                minPriceCell.textContent = minPrice;
                row.appendChild(minPriceCell);
                
                // 操作列
                const actionCell = document.createElement('td');
                const deleteButton = document.createElement('button');
                deleteButton.textContent = 'Delete';
                deleteButton.className = 'btn btn-small btn-danger';
                deleteButton.addEventListener('click', function() {
                    deleteWatchlistItem(id);
                });
                actionCell.appendChild(deleteButton);
                row.appendChild(actionCell);
                
                watchlistBody.appendChild(row);
            });
            
            messageElement.textContent = '';
            messageElement.className = 'message';
        } else {
            messageElement.textContent = data.message || 'Failed to fetch watchlist';
            messageElement.className = 'message error';
        }
    })
    .catch(error => {
        const messageElement = document.getElementById('watchlist-message');
        messageElement.textContent = 'Request failed: ' + error.message;
        messageElement.className = 'message error';
    });
}

// 删除监控列表项
function deleteWatchlistItem(itemId) {
    const username = localStorage.getItem('username');
    
    // 发送请求到后端删除监控项
    fetch('/api/delete_watchlist_item', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            username: username,
            item_id: itemId
        })
    })
    .then(response => response.json())
    .then(data => {
        const messageElement = document.getElementById('watchlist-message');
        if (data.status === 'success') {
            messageElement.textContent = 'Item deleted';
            messageElement.className = 'message success';
            // 刷新监控列表
            loadWatchlist();
        } else {
            messageElement.textContent = data.message || 'Failed to delete item';
            messageElement.className = 'message error';
        }
    })
    .catch(error => {
        const messageElement = document.getElementById('watchlist-message');
        messageElement.textContent = 'Request failed: ' + error.message;
        messageElement.className = 'message error';
    });
}

function stopQuery() {
    const username = localStorage.getItem('username');
    const queryStatusElement = document.getElementById('query-status');
    queryStatusElement.textContent = 'Stopping query...';
    queryStatusElement.className = 'message info';
    fetch('/api/stop_query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            username: username
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            queryStatusElement.textContent = 'Query stopped';
            queryStatusElement.className = 'message success';
        } else {
            queryStatusElement.textContent = data.message || 'Failed to stop query';
            queryStatusElement.className = 'message error';
        }
    })
    .catch(error => {
        queryStatusElement.textContent = 'Failed to stop query, please check network connection';
        queryStatusElement.className = 'message error';
    });
}