import os
import yaml
import hashlib
import re
from typing import Dict, Any, Tuple, Optional

class UserRegistration:
    """
    处理用户注册和账户管理的类
    
    提供用户注册、验证和数据管理功能，支持邮箱作为用户名
    """
    
    def __init__(self, config_dir: str = None):
        """
        初始化用户注册系统
        
        Args:
            config_dir: 用户配置文件存储目录，默认为项目根目录下的 'configs'
        """
        # 获取项目根目录（buff_auto_notification 的父目录）
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # 使用项目根目录下的 configs 文件夹
        self.config_dir = config_dir or os.path.join(project_root, 'configs')
        os.makedirs(self.config_dir, exist_ok=True)
    
    def register_user(self, email: str, password: str) -> Tuple[bool, str]:
        """
        注册新用户
        
        Args:
            email: 用户邮箱（作为用户名）
            password: 用户密码
            
        Returns:
            Tuple[bool, str]: (是否成功, 成功/错误消息)
        """
        # 验证邮箱格式
        if not self._validate_email(email):
            return False, "邮箱格式不正确"
        
        # 检查用户是否已存在
        user_dir = os.path.join(self.config_dir, email)
        config_path = os.path.join(user_dir, 'user_data.yaml')
        
        if os.path.exists(config_path):
            return False, "用户已存在"
        
        # 创建用户目录
        os.makedirs(user_dir, exist_ok=True)
        
        # 创建用户数据
        user_data = {
            'password_hash': self._hash_password(password),
            'buff_cookies': '',
            'notification_settings': {
                'email': email,  # 设置邮箱为用户登录的邮箱
                'check_frequency_minutes': 30
            },
            'watchlist': {}
        }
        
        # 保存用户数据
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(user_data, f, sort_keys=False)
            return True, "用户注册成功"
        except Exception as e:
            return False, f"注册失败: {str(e)}"
    
    def verify_user(self, email: str, password: str) -> Tuple[bool, str]:
        """
        验证用户凭据
        
        Args:
            email: 用户邮箱
            password: 用户密码
            
        Returns:
            Tuple[bool, str]: (是否成功, 成功/错误消息)
        """
        # 验证邮箱格式
        if not self._validate_email(email):
            return False, "邮箱格式不正确"
        
        # 检查用户是否存在
        config_path = os.path.join(self.config_dir, email, 'user_data.yaml')
        if not os.path.exists(config_path):
            return False, "用户不存在"
        
        # 加载用户数据
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_data = yaml.safe_load(f)
        except Exception as e:
            return False, f"读取用户数据失败: {str(e)}"
        
        # 验证密码
        stored_hash = user_data.get('password_hash')
        if not stored_hash or self._hash_password(password) != stored_hash:
            return False, "密码不正确"
        
        return True, "验证成功"
    
    def get_user_data(self, email: str) -> Optional[Dict[str, Any]]:
        """
        获取用户数据
        
        Args:
            email: 用户邮箱（作为用户名）
            
        Returns:
            Optional[Dict[str, Any]]: 用户数据字典，如果用户不存在则返回 None
        """
        config_path = os.path.join(self.config_dir, email, 'user_data.yaml')
        if not os.path.exists(config_path):
            return None
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception:
            return None
    
    def _validate_email(self, email: str) -> bool:
        """
        验证邮箱格式
        
        Args:
            email: 要验证的邮箱
            
        Returns:
            bool: 邮箱格式是否正确
        """
        # 邮箱格式验证
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _hash_password(self, password: str) -> str:
        """
        对密码进行哈希处理
        
        Args:
            password: 原始密码
            
        Returns:
            str: 密码哈希值
        """
        return hashlib.sha256(password.encode('utf-8')).hexdigest()


# 为前端提供的 API 接口
def register_api(email: str, password: str) -> Dict[str, Any]:
    """
    用户注册 API
    
    Args:
        email: 用户邮箱
        password: 用户密码
        
    Returns:
        Dict[str, Any]: 包含状态和消息的响应字典
    """
    registration = UserRegistration()
    success, message = registration.register_user(email, password)
    return {
        'success': success,
        'message': message
    }

def login_api(email: str, password: str) -> Dict[str, Any]:
    """
    用户登录 API
    
    Args:
        email: 用户邮箱
        password: 用户密码
        
    Returns:
        Dict[str, Any]: 包含状态、消息和用户数据的响应字典
    """
    registration = UserRegistration()
    success, message = registration.verify_user(email, password)
    
    response = {
        'success': success,
        'message': message
    }
    
    if success:
        user_data = registration.get_user_data(email)
        if user_data:
            # 移除敏感信息
            if 'password_hash' in user_data:
                del user_data['password_hash']
            response['user_data'] = user_data
    
    return response


# 如果直接运行此脚本，提供简单的命令行测试功能
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("用法: python registration.py [register|login] 邮箱 密码")
        sys.exit(1)
    
    action = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3] if len(sys.argv) > 3 else ""
    
    if action == "register":
        result = register_api(email, password)
        print(f"注册结果: {result['success']}, 消息: {result['message']}")
    elif action == "login":
        result = login_api(email, password)
        print(f"登录结果: {result['success']}, 消息: {result['message']}")
        if result['success'] and 'user_data' in result:
            print(f"用户数据: {result['user_data']}")
    else:
        print("无效的操作，请使用 'register' 或 'login'")