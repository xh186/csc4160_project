// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // Check login state
    const username = localStorage.getItem('username');
    if (username) {
        // Logged in, redirect to dashboard
        window.location.href = '/dashboard';
        return;
    }
});

// Tabs switching
function showTab(tabId) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        content.classList.remove('active');
    });
    
    // Deactivate all tab buttons
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(button => {
        button.classList.remove('active');
    });
    
    // Show selected tab content
    document.getElementById(tabId).classList.add('active');
    
    // Activate selected tab button
    document.querySelector(`.tab-btn[onclick="showTab('${tabId}')"]`).classList.add('active');
}

// 注册表单提交处理
document.getElementById('register-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const confirmPassword = document.getElementById('register-confirm-password').value;
    const messageElement = document.getElementById('register-message');
    
    // 清除之前的消息
    messageElement.textContent = '';
    messageElement.className = 'message';
    
    // 验证密码是否匹配
    if (password !== confirmPassword) {
        messageElement.textContent = 'Passwords do not match';
        messageElement.classList.add('error');
        return;
    }
    
    // 发送注册请求
    fetch('/api/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            messageElement.textContent = 'Registration successful! Please log in';
            messageElement.classList.add('success');
            // 重置表单
            document.getElementById('register-form').reset();
            // 切换到登录标签
            setTimeout(() => showTab('login'), 1500);
        } else {
            messageElement.textContent = data.message || 'Registration failed, please retry';
            messageElement.classList.add('error');
        }
    })
    .catch(error => {
        messageElement.textContent = 'Server error, please try again later';
        messageElement.classList.add('error');
        console.error('Error:', error);
    });
});

// Login form submit handler
document.getElementById('login-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const messageElement = document.getElementById('login-message');
    
    // Clear previous messages
    messageElement.textContent = '';
    messageElement.className = 'message';
    
    // Send login request
    fetch('/api/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            messageElement.textContent = 'Login successful! Redirecting...';
            messageElement.classList.add('success');
            
            // Save username to localStorage
            localStorage.setItem('username', email);
            
            // Redirect to dashboard
            setTimeout(function() {
                window.location.href = '/dashboard';
            }, 1000);
        } else {
            messageElement.textContent = data.message || 'Login failed, please check email and password';
            messageElement.classList.add('error');
        }
    })
    .catch(error => {
        messageElement.textContent = 'Server error, please try again later';
        messageElement.classList.add('error');
        console.error('Error:', error);
    });
});