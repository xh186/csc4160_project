// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 检查是否已登录
    const username = localStorage.getItem('username');
    if (username) {
        // 已登录，跳转到仪表盘
        window.location.href = '/dashboard';
        return;
    }
});

// 切换标签页功能
function showTab(tabId) {
    // 隐藏所有标签内容
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        content.classList.remove('active');
    });
    
    // 取消所有标签按钮的活跃状态
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(button => {
        button.classList.remove('active');
    });
    
    // 显示选中的标签内容
    document.getElementById(tabId).classList.add('active');
    
    // 设置选中的标签按钮为活跃状态
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
        messageElement.textContent = '两次输入的密码不一致';
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
            messageElement.textContent = '注册成功！请登录';
            messageElement.classList.add('success');
            // 重置表单
            document.getElementById('register-form').reset();
            // 切换到登录标签
            setTimeout(() => showTab('login'), 1500);
        } else {
            messageElement.textContent = data.message || '注册失败，请重试';
            messageElement.classList.add('error');
        }
    })
    .catch(error => {
        messageElement.textContent = '服务器错误，请稍后重试';
        messageElement.classList.add('error');
        console.error('Error:', error);
    });
});

// 登录表单提交处理
document.getElementById('login-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const messageElement = document.getElementById('login-message');
    
    // 清除之前的消息
    messageElement.textContent = '';
    messageElement.className = 'message';
    
    // 发送登录请求
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
            messageElement.textContent = '登录成功！正在跳转...';
            messageElement.classList.add('success');
            
            // 保存用户名到本地存储
            localStorage.setItem('username', email);
            
            // 跳转到仪表盘页面
            setTimeout(function() {
                window.location.href = '/dashboard';
            }, 1000);
        } else {
            messageElement.textContent = data.message || '登录失败，请检查账号和密码';
            messageElement.classList.add('error');
        }
    })
    .catch(error => {
        messageElement.textContent = '服务器错误，请稍后重试';
        messageElement.classList.add('error');
        console.error('Error:', error);
    });
});