#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
花夏数娱自动签到脚本 (GitHub Actions版)
"""

import os
import sys
import time
import socket
import json
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ========== 配置区 ==========
class Config:
    # 读取信息
    USERNAME = os.getenv('HXSY_USERNAME')
    PASSWORD = os.getenv('HXSY_PASSWORD')
    
    LOGIN_URL = 'https://www.huaxiashuyu.com/wp-admin/admin-ajax.php'
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    CONNECT_TIMEOUT = 10
    READ_TIMEOUT = 30
    MAX_RETRIES = 3
    PROXY = os.getenv('HTTP_PROXY')
    
    # GitHub Actions 环境下关闭详细调试
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    IS_GITHUB_ACTIONS = os.getenv('GITHUB_ACTIONS') == 'true'

# ========== 创建会话 ==========
def create_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    if Config.PROXY:
        session.proxies = {'http': Config.PROXY, 'https': Config.PROXY}
        print(f"🌐 使用代理: {Config.PROXY}")

    return session

session = create_session()

# ========== 工具函数 ==========
def notify(title: str, content: str):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    message = f"[{timestamp}] {title}\n{content}"
    print('\n' + '=' * 50)
    print(message)
    print('=' * 50 + '\n')
    
    # GitHub Actions 支持
    if Config.IS_GITHUB_ACTIONS:
        summary_file = os.getenv('GITHUB_STEP_SUMMARY')
        if summary_file:
            emoji = '✅' if '成功' in content else '❌' if '失败' in content else 'ℹ️'
            with open(summary_file, 'a', encoding='utf-8') as f:
                f.write(f"## {emoji} {title}\n\n")
                f.write(f"{content}\n\n")
                f.write(f"**执行时间**: {timestamp}\n\n")

def validate_config():
    if not Config.USERNAME or not Config.PASSWORD:
        notify('❌ 配置错误', '未设置账号或密码！请检查 GitHub Secrets 配置')
        sys.exit(1)
    
    # 脱敏显示用户名
    masked_username = Config.USERNAME[:3] + '***' + Config.USERNAME[-3:] if len(Config.USERNAME) > 6 else '***'
    print(f"📧 使用账号: {masked_username}")

def check_network():
    try:
        host = 'www.huaxiashuyu.com'
        print(f"🔍 DNS解析: {host}")
        ip = socket.gethostbyname(host)
        print(f"✅ 解析成功: {ip}")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, 443))
        sock.close()

        if result == 0:
            print(f"✅ TCP连接成功\n")
            return True
        else:
            print(f"❌ TCP连接失败\n")
            return False
    except Exception as e:
        print(f"❌ 网络检测失败: {e}\n")
        return False

# ========== 智能响应判断 ==========
def is_response_success(response_data: dict, response_text: str = '') -> bool:
    if not isinstance(response_data, dict):
        return False

    status = response_data.get('status')
    if status in [1, '1', 200, '200', 'success']:
        return True

    success = response_data.get('success')
    if success in [True, 'true', 1, '1']:
        return True

    code = response_data.get('code')
    if code in [0, '0', 200, '200']:
        return True

    msg = response_data.get('msg', '').lower()
    success_keywords = ['成功', 'success', 'ok', '已签到']
    if any(keyword in msg for keyword in success_keywords):
        fail_keywords = ['失败', 'fail', 'error', '错误']
        if not any(keyword in msg for keyword in fail_keywords):
            return True

    if '成功' in response_text and '失败' not in response_text:
        return True

    return False

# ========== 登录函数 ==========
def login() -> str:
    login_data = {
        'action': 'user_login',
        'username': Config.USERNAME,
        'password': Config.PASSWORD
    }

    headers = {
        'User-Agent': Config.USER_AGENT,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest'
    }

    print(f"🔗 正在连接登录接口...")

    try:
        response = session.post(
            Config.LOGIN_URL,
            data=login_data,
            headers=headers,
            timeout=(Config.CONNECT_TIMEOUT, Config.READ_TIMEOUT),
            verify=True
        )

        # 仅在调试模式或本地环境显示详细信息
        if Config.DEBUG and not Config.IS_GITHUB_ACTIONS:
            print(f"\n{'='*60}")
            print(f"📊 HTTP状态码: {response.status_code}")
            print(f"📦 响应内容: {response.text[:300]}")
            print(f"🍪 Cookies: {response.cookies.get_dict()}")
            print(f"{'='*60}\n")

        try:
            result = response.json()
            if Config.DEBUG and not Config.IS_GITHUB_ACTIONS:
                print(f"🔍 解析后的JSON: {json.dumps(result, ensure_ascii=False, indent=2)}")
        except json.JSONDecodeError:
            print(f"❌ JSON解析失败")
            notify('❌ 登录错误', '服务器返回格式异常')
            return None

        if is_response_success(result, response.text):
            msg = result.get('msg', '登录成功')
            notify('🎉 登录成功', msg)

            cookies = response.cookies.get_dict()
            if cookies:
                cookie_str = '; '.join([f"{k}={v}" for k, v in cookies.items()])
                print(f"✅ 获取到 Cookie ({len(cookie_str)} 字符)")
                return cookie_str
            else:
                set_cookie = response.headers.get('Set-Cookie', '')
                if set_cookie:
                    cookie_str = '; '.join([c.split(';')[0] for c in set_cookie.split(', ')])
                    print(f"✅ 从响应头提取 Cookie ({len(cookie_str)} 字符)")
                    return cookie_str
                else:
                    return "no-cookie-needed"
        else:
            msg = result.get('msg', '未知错误')
            notify('🔴 登录失败', msg)
            return None

    except requests.exceptions.Timeout:
        notify('⏰ 请求超时', '连接超时，请检查网络')
        return None
    except Exception as e:
        notify('💥 登录异常', f'{type(e).__name__}: {str(e)}')
        return None

# ========== 签到函数 ==========
def sign_in(cookie: str):
    headers = {
        'User-Agent': Config.USER_AGENT,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest'
    }

    if cookie and cookie != "no-cookie-needed":
        headers['Cookie'] = cookie

    data = {'action': 'user_qiandao'}

    print(f"✍️ 正在执行签到操作...")

    try:
        response = session.post(
            Config.LOGIN_URL,
            data=data,
            headers=headers,
            timeout=(Config.CONNECT_TIMEOUT, Config.READ_TIMEOUT),
            verify=True
        )

        if Config.DEBUG and not Config.IS_GITHUB_ACTIONS:
            print(f"\n{'='*60}")
            print(f"📊 签到响应状态码: {response.status_code}")
            print(f"📦 签到响应内容: {response.text[:300]}")
            print(f"{'='*60}\n")

        try:
            result = response.json()
            if Config.DEBUG and not Config.IS_GITHUB_ACTIONS:
                print(f"🔍 签到结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        except json.JSONDecodeError:
            print(f"❌ JSON解析失败")
            notify('❌ 签到错误', '服务器返回格式异常')
            return

        if is_response_success(result, response.text):
            msg = result.get('msg', '签到成功')
            notify('✅ 签到成功', msg)
        else:
            msg = result.get('msg', '签到失败')
            if '已签' in msg or '重复' in msg:
                notify('ℹ️ 今日已签到', msg)
            else:
                notify('⚠️ 签到异常', msg)

    except Exception as e:
        notify('💥 签到异常', f'{type(e).__name__}: {str(e)}')

# ========== 主函数 ==========
def main():
    print('\n🚀 花夏数娱自动签到脚本启动...\n')
    print(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌍 运行环境: {'GitHub Actions' if Config.IS_GITHUB_ACTIONS else '本地环境'}\n")

    if not check_network():
        notify('❌ 网络异常', '无法连接到目标服务器')
        sys.exit(1)

    validate_config()

    try:
        cookie = login()
        if cookie:
            time.sleep(2)
            sign_in(cookie)
            print("\n✅ 所有任务执行完成")
        else:
            print("\n❌ 登录失败，终止执行")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断执行")
        sys.exit(0)
    except Exception as e:
        notify('💥 脚本异常', f'{type(e).__name__}: {str(e)}')
        import traceback
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main()
