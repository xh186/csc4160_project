from flask import Flask, request, jsonify, render_template
import yaml
import os
import hashlib
import json
import uuid
import threading
from registration import UserRegistration
from query_input import QueryInput
from server import BuffAutoNotificationServer
from BuffApiPublic import BuffAccount
from cache import MarketCache

app = Flask(__name__, 
            static_folder='../frontend/static',
            template_folder='../frontend/templates')

SHARED_CACHE_MANAGER = MarketCache(cache_dir="./shared_market_cache")

# 获取项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 加载服务器配置
SERVER_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server_config.yaml')
try:
    with open(SERVER_CONFIG_PATH, 'r') as f:
        SERVER_CONFIG = yaml.safe_load(f)
except Exception as e:
    print(f"Error loading server config: {e}")
    SERVER_CONFIG = {"user_data_base_dir": "configs"}

# 使用绝对路径确保用户数据存储在稳定位置
USER_DATA_DIR = os.path.join(project_root, SERVER_CONFIG.get("user_data_base_dir", "configs"))

# 存储查询服务器实例
query_servers = {}

# 近期搜索缓存（按用户名保存最近一次搜索结果用于名称->ID映射）
recent_search_cache = {}

# 简化搜索返回的条目，便于前端展示
def _simplify_item(item: dict) -> dict:
    name = item.get('name') or item.get('market_hash_name') or item.get('short_name')
    return {
        'id': str(item.get('id')) if item.get('id') is not None else None,
        'name': name,
        'sell_min_price': item.get('sell_min_price'),
        'sell_num': item.get('sell_num'),
        'buy_max_price': item.get('buy_max_price'),
        'buy_num': item.get('buy_num'),
        'quick_price': item.get('quick_price')
    }

# 启动查询服务器的函数
def start_query_server(username):
    try:
        # 创建并启动查询服务器，传入当前用户名
        server = BuffAutoNotificationServer()
        
        # # 设置用户名，确保使用正确的用户数据
        # user_data_path = os.path.join(USER_DATA_DIR, username, 'user_data.yaml')
        # if not os.path.exists(user_data_path):
        #     return False, f"用户数据文件不存在: {user_data_path}"
            
        # # 加载用户数据
        # with open(user_data_path, 'r', encoding='utf-8') as f:
        #     user_data = yaml.safe_load(f)
            
        # # 设置用户配置
        # server.user_name = username
        # server.user_data_path = user_data_path
                
        # 在新线程中启动服务器
        def run_server():
            server.start()  # 移除username参数，使用之前设置的用户配置
        
        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()
        
        # 保存服务器实例
        query_servers[username] = {
            'server': server,
            'thread': server_thread,
            'status': 'running'
        }
        
        return True, "查询服务已启动"
    except Exception as e:
        return False, f"启动查询服务失败: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/start_query', methods=['POST'])
def api_start_query():
    data = request.json
    username = data.get('username')
    
    if not username:
        return jsonify({"status": "error", "message": "用户名不能为空"})
    
    # 检查用户目录是否存在
    user_dir = os.path.join(USER_DATA_DIR, username)
    if not os.path.exists(user_dir):
        return jsonify({"status": "error", "message": "用户不存在"})
    
    # 检查是否已经有查询服务在运行
    if username in query_servers and query_servers[username]['status'] == 'running':
        return jsonify({"status": "success", "message": "查询服务已在运行中"})
    
    # 启动查询服务
    success, message = start_query_server(username)
    
    if success:
        return jsonify({"status": "success", "message": message})
    else:
        return jsonify({"status": "error", "message": message})

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"status": "error", "message": "邮箱和密码不能为空"})
    
    # 使用registration模块注册用户
    user_reg = UserRegistration(config_dir=USER_DATA_DIR)
    success, message = user_reg.register_user(email, password)
    
    if success:
        return jsonify({"status": "success", "message": message})
    else:
        return jsonify({"status": "error", "message": message})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"status": "error", "message": "邮箱和密码不能为空"})
    
    # 使用registration模块验证用户
    user_reg = UserRegistration(config_dir=USER_DATA_DIR)
    success, message = user_reg.verify_user(email, password)
    
    if success:
        return jsonify({"status": "success", "message": message})
    else:
        return jsonify({"status": "error", "message": message})

@app.route('/api/get_cookie', methods=['GET'])
def api_get_cookie():
    username = request.args.get('username')
    
    if not username:
        return jsonify({"status": "error", "message": "缺少用户名参数"})
    
    user_config_path = os.path.join(USER_DATA_DIR, username, 'user_data.yaml')
    
    if not os.path.exists(user_config_path):
        return jsonify({"status": "error", "message": "用户配置不存在"})
    
    try:
        with open(user_config_path, 'r', encoding='utf-8') as f:
            user_config = yaml.safe_load(f)
        
        buff_cookies = user_config.get('buff_cookies', '')
        return jsonify({"status": "success", "cookie": buff_cookies})
    except Exception as e:
        return jsonify({"status": "error", "message": f"获取Cookie失败: {e}"})

@app.route('/api/update_cookie', methods=['POST'])
def api_update_cookie():
    data = request.json
    username = data.get('username')
    buff_cookies = data.get('buff_cookies')
    
    if not username or not buff_cookies:
        return jsonify({"status": "error", "message": "缺少必要参数"})
    
    user_config_path = os.path.join(USER_DATA_DIR, username, 'user_data.yaml')
    
    if not os.path.exists(user_config_path):
        return jsonify({"status": "error", "message": "用户配置不存在"})
    
    try:
        with open(user_config_path, 'r', encoding='utf-8') as f:
            user_config = yaml.safe_load(f)
        
        user_config['buff_cookies'] = buff_cookies
        
        with open(user_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(user_config, f, default_flow_style=False, allow_unicode=True)
        
        return jsonify({"status": "success", "message": "Cookie更新成功"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"更新Cookie失败: {e}"})

@app.route('/api/add_query', methods=['POST'])
def api_add_query():
    data = request.json
    username = data.get('username')
    goods_id = data.get('goods_id')
    game = data.get('game', 'dota2')
    price_min = data.get('price_min')
    price_max = data.get('price_max')
    sort_by = data.get('sort_by', 'price.asc')
    
    if not username or not goods_id:
        return jsonify({"status": "error", "message": "缺少必要参数"})
    
    try:
        # 从用户配置中获取cookie
        user_config_path = os.path.join(USER_DATA_DIR, username, 'user_data.yaml')
        if not os.path.exists(user_config_path):
            return jsonify({"status": "error", "message": "用户配置不存在"})
            
        with open(user_config_path, 'r', encoding='utf-8') as f:
            user_config = yaml.safe_load(f)
        
        buff_cookies = user_config.get('buff_cookies', '')
        if not buff_cookies:
            return jsonify({"status": "error", "message": "请先在Cookie设置中设置Buff Cookie"})
            
        # 使用QueryInput类添加查询
        query_input = QueryInput()
        success, message = query_input.api_add_query(
            username=username,
            buff_cookies=buff_cookies,
            email=username,  # 直接使用用户名（邮箱）作为邮箱地址
            goods_id=goods_id,
            game=game,
            price_min=price_min,
            price_max=price_max,
            sort_by=sort_by
        )
        
        if success:
            return jsonify({"status": "success", "message": message})
        else:
            return jsonify({"status": "error", "message": message})
    except Exception as e:
        return jsonify({"status": "error", "message": f"添加查询失败: {str(e)}"})

@app.route('/api/get_watchlist', methods=['GET'])
def api_get_watchlist():
    username = request.args.get('username')
    
    if not username:
        return jsonify({"status": "error", "message": "缺少用户名参数"})
    
    try:
        # 读取用户数据文件
        user_data_path = os.path.join(USER_DATA_DIR, username, 'user_data.yaml')
        if not os.path.exists(user_data_path):
            return jsonify({"status": "error", "message": "用户数据不存在"})
        
        with open(user_data_path, 'r', encoding='utf-8') as f:
            user_data = yaml.safe_load(f)
        
        # 获取监视列表
        watchlist = user_data.get('watchlist', {})
        return jsonify({"status": "success", "watchlist": watchlist})
    except Exception as e:
        return jsonify({"status": "error", "message": f"获取监视列表失败: {str(e)}"})

@app.route('/api/delete_watchlist_item', methods=['POST'])
def api_delete_watchlist_item():
    data = request.json
    username = data.get('username')
    item_id = data.get('item_id')
    
    if not username or not item_id:
        return jsonify({"status": "error", "message": "缺少必要参数"})
    
    try:
        # 读取用户数据文件
        user_data_path = os.path.join(USER_DATA_DIR, username, 'user_data.yaml')
        if not os.path.exists(user_data_path):
            return jsonify({"status": "error", "message": "用户数据不存在"})
        
        with open(user_data_path, 'r', encoding='utf-8') as f:
            user_data = yaml.safe_load(f)
        
        # 删除监视列表项
        watchlist = user_data.get('watchlist', {})
        if item_id in watchlist:
            del watchlist[item_id]
            user_data['watchlist'] = watchlist
            
            # 保存更新后的用户数据
            with open(user_data_path, 'w', encoding='utf-8') as f:
                yaml.dump(user_data, f, default_flow_style=False, allow_unicode=True)
            
            return jsonify({"status": "success", "message": "成功删除监视项"})
        else:
            return jsonify({"status": "error", "message": "监视项不存在"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"删除监视项失败: {str(e)}"})

@app.route('/api/search_by_name', methods=['POST'])
def api_search_by_name():
    data = request.json or {}
    username = data.get('username')
    keyword = data.get('keyword')
    game = data.get('game', 'dota2')
    limit = int(data.get('limit', 10))

    if not username or not keyword:
        return jsonify({"status": "error", "message": "缺少必要参数: username 或 keyword"})

    # 读取用户配置以获取 Cookie
    user_config_path = os.path.join(USER_DATA_DIR, username, 'user_data.yaml')
    if not os.path.exists(user_config_path):
        return jsonify({"status": "error", "message": "用户配置不存在"})

    try:
        with open(user_config_path, 'r', encoding='utf-8') as f:
            user_config = yaml.safe_load(f)
        buff_cookies = user_config.get('buff_cookies', '')
        if not buff_cookies:
            return jsonify({"status": "error", "message": "请先在Cookie设置中设置Buff Cookie"})

        # 调用 Buff API 搜索
        buff = BuffAccount(buffcookie=buff_cookies)
        items = buff.search_goods_list(key=keyword, game_name=game) or []
        print(f"Search results for user {username}, keyword '{keyword}': {items}")
        SHARED_CACHE_MANAGER.upsert_cache(items)
        # 规范为列表
        if isinstance(items, dict):
            items = items.get('items', [])
        # 取前 limit 项并简化
        simplified = [_simplify_item(it) for it in items[:limit]]
        # 缓存最近搜索结果用于后续名称->ID映射
        recent_search_cache[username] = {
            'keyword': keyword,
            'game': game,
            'items': simplified
        }
        # 返回仅名称列表（按需求），但内部已缓存映射
        name_list = [it['name'] for it in simplified if it.get('name')]
        return jsonify({"status": "success", "names": name_list})
    except Exception as e:
        return jsonify({"status": "error", "message": f"搜索失败: {str(e)}"})

@app.route('/api/add_watchlist_by_name', methods=['POST'])
def api_add_watchlist_by_name():
    data = request.json or {}
    username = data.get('username')
    selected_name = data.get('selected_name')
    # 允许前端指定 game，否则尝试沿用最近搜索，最后回落到 'dota2'
    game = data.get('game') or (recent_search_cache.get(username, {}).get('game')) or 'dota2'
    price_min = data.get('price_min')
    price_max = data.get('price_max')
    sort_by = data.get('sort_by', 'price.asc')

    if not username or not selected_name:
        return jsonify({"status": "error", "message": "缺少必要参数: username 或 selected_name"})

    # 读取用户配置以获取 Cookie
    user_config_path = os.path.join(USER_DATA_DIR, username, 'user_data.yaml')
    if not os.path.exists(user_config_path):
        return jsonify({"status": "error", "message": "用户配置不存在"})

    try:
        with open(user_config_path, 'r', encoding='utf-8') as f:
            user_config = yaml.safe_load(f)
        buff_cookies = user_config.get('buff_cookies', '')
        if not buff_cookies:
            return jsonify({"status": "error", "message": "请先在Cookie设置中设置Buff Cookie"})

        # 1) 先从最近缓存里找名称->ID
        goods_id = None
        cached = recent_search_cache.get(username)
        if cached and isinstance(cached.get('items'), list):
            for it in cached['items']:
                # 与返回给前端的名称一致的匹配逻辑
                if it.get('name') == selected_name and it.get('id'):
                    goods_id = it['id']
                    break

        # 2) 若未命中或缓存不存在，回退到实时搜索
        if not goods_id:
            buff = BuffAccount(buffcookie=buff_cookies)
            items = buff.search_goods_list(key=selected_name, game_name=game) or []
            if isinstance(items, dict):
                items = items.get('items', [])
            for it in items:
                name = it.get('name') or it.get('market_hash_name') or it.get('short_name')
                if name == selected_name and it.get('id') is not None:
                    goods_id = str(it['id'])
                    break
            # 如果仍未找到，退一步：选择第一条结果
            if not goods_id and items:
                first = items[0]
                if first.get('id') is not None:
                    goods_id = str(first['id'])

        if not goods_id:
            return jsonify({"status": "error", "message": "未能解析所选名称对应的商品ID"})

        # 3) 调用现有逻辑写入 watchlist
        query_input = QueryInput()
        success, message = query_input.api_add_query(
            username=username,
            buff_cookies=buff_cookies,
            email=username,
            goods_id=goods_id,
            game=game,
            price_min=price_min,
            price_max=price_max,
            sort_by=sort_by,
            item_name=selected_name
        )
        if success:
            return jsonify({"status": "success", "message": message, "goods_id": goods_id})
        else:
            return jsonify({"status": "error", "message": message})
    except Exception as e:
        return jsonify({"status": "error", "message": f"添加到watchlist失败: {str(e)}"})


if __name__ == '__main__':
    # 确保用户数据目录存在
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    app.run(debug=True, port=5002)