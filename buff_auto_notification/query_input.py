#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import yaml
import json
import uuid
from typing import Dict, Any, List, Optional

class QueryInput:
    """
    用于接收用户输入的查询条件并将其存储到用户配置的 watchlist 中
    """
    
    def __init__(self):
        # 获取项目根目录
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_dir = os.path.join(self.project_root, 'configs')
        
        # 游戏选项
        self.game_options = {
            '1': 'csgo',
            '2': 'dota2',
            '3': 'pubg'
        }
        
        # 排序选项
        self.sort_options = {
            '1': 'default',
            '2': 'price.asc',  # 价格从低到高
            '3': 'price.desc'  # 价格从高到低
        }
    
    def add_query_to_watchlist(self, username: str, query_data: Dict[str, Any]) -> bool:
        """
        将查询条件添加到用户的 watchlist 中
        
        Args:
            username: 用户名
            query_data: 查询条件数据
            
        Returns:
            bool: 是否成功添加
        """
        user_config_path = os.path.join(self.config_dir, username, 'user_data.yaml')
        
        # 检查用户配置文件是否存在
        if not os.path.exists(user_config_path):
            print(f"用户 {username} 的配置文件不存在")
            return False
        
        try:
            # 读取用户配置
            with open(user_config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
            
            # 确保 watchlist 存在
            if 'watchlist' not in user_config:
                user_config['watchlist'] = {}
            
            # 生成唯一的查询 ID
            query_id = str(uuid.uuid4())[:8]
            
            # 添加查询到 watchlist
            user_config['watchlist'][query_id] = query_data
            
            # 保存更新后的配置
            with open(user_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(user_config, f, default_flow_style=False, allow_unicode=True)
            
            return True
        except Exception as e:
            print(f"添加查询条件时出错: {e}")
            return False
    
    def api_add_query(self, username: str, goods_id: str, game: str, 
                     email: str, buff_cookies: str, 
                     price_min: Optional[float] = None, 
                     price_max: Optional[float] = None,
                     sort_by: str = 'default',
                     item_name: Optional[str] = None) -> tuple:
        """
        API 接口：添加查询条件到用户的 watchlist
        
        Args:
            username: 用户名
            goods_id: 商品 ID
            game: 游戏名称
            email: 通知邮箱
            buff_cookies: Buff 网站的 cookies
            price_min: 最低价格
            price_max: 最高价格
            sort_by: 排序方式
            
        Returns:
            tuple: (成功状态, 消息)
        """
        # 构建查询条件数据
        conditions = []
        
        # 添加价格条件
        if price_min is not None:
            conditions.append({
                'condition_type': 'price_threshold',
                'target_field': 'sell_min_price',
                'operator': '>',
                'value': float(price_min)
            })
        
        if price_max is not None:
            conditions.append({
                'condition_type': 'price_threshold',
                'target_field': 'sell_min_price',
                'operator': '<',
                'value': float(price_max)
            })
        
        # 更新用户的 cookies 和 email
        user_config_path = os.path.join(self.config_dir, username, 'user_data.yaml')
        try:
            with open(user_config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
            
            # 更新 cookies 和 email
            user_config['buff_cookies'] = buff_cookies
            
            if 'notification_settings' not in user_config:
                user_config['notification_settings'] = {}
            
            user_config['notification_settings']['email'] = email
            
            # 确保 watchlist 存在
            if 'watchlist' not in user_config:
                user_config['watchlist'] = {}
            
            # 直接使用商品ID作为键
            user_config['watchlist'][goods_id] = {
                'conditions': conditions,
                'game': game,
                'goods_id': goods_id,
                'item_name': item_name or f"商品 {goods_id}"
            }
            
            # 保存更新后的配置
            with open(user_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(user_config, f, default_flow_style=False, allow_unicode=True)
                
            return True, "成功添加查询条件"
        except Exception as e:
            return False, f"更新用户配置时出错: {e}"
    
    def cli_interface(self):
        """
        命令行界面，用于测试
        """
        print("===== Buff 商品查询条件输入 =====")
        
        # 获取用户名
        username = input("请输入用户名: ")
        
        # 获取 Buff cookies
        buff_cookies = input("请输入 Buff cookies (格式如 session=xxxxx): ")
        
        # 获取通知邮箱
        email = input("请输入通知邮箱: ")
        
        # 选择游戏
        print("\n请选择游戏:")
        for key, value in self.game_options.items():
            print(f"{key}. {value}")
        game_choice = input("请选择 (默认为 csgo): ") or '1'
        game = self.game_options.get(game_choice, 'csgo')
        
        # 获取商品 ID
        goods_id = input("\n请输入商品 ID: ")
        
        # 获取价格范围
        price_min_input = input("\n请输入最低价格 (可选): ")
        price_min = float(price_min_input) if price_min_input else None
        
        price_max_input = input("请输入最高价格 (可选): ")
        price_max = float(price_max_input) if price_max_input else None
        
        # 选择排序方式
        print("\n请选择排序方式:")
        for key, value in self.sort_options.items():
            print(f"{key}. {value}")
        sort_choice = input("请选择 (默认为 default): ") or '1'
        sort_by = self.sort_options.get(sort_choice, 'default')
        
        # 添加到 watchlist
        result = self.api_add_query(
            username=username,
            goods_id=goods_id,
            game=game,
            email=email,
            buff_cookies=buff_cookies,
            price_min=price_min,
            price_max=price_max,
            sort_by=sort_by
        )
        
        print(f"\n{result['message']}")

# 如果直接运行此脚本，启动命令行界面
if __name__ == "__main__":
    query_input = QueryInput()
    query_input.cli_interface()