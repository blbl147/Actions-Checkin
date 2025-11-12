#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
看雪论坛自动签到脚本 - GitHub Actions版本
"""

import requests
import json
import os
import sys
from datetime import datetime
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 状态文件路径
STATUS_FILE = "status/status_kanxue.json"

def load_today_status():
    """加载今日签到状态"""
    if not os.path.exists(STATUS_FILE):
        return False

    try:
        with open(STATUS_FILE, 'r', encoding='utf-8') as f:
            data = f.read().strip()
            if not data:
                return False
            status = json.loads(data)
            # 检查是否是今天的记录
            today = datetime.now().strftime('%Y-%m-%d')
            if status.get('date') == today and status.get('success'):
                print(f"✅ 今日({today})已成功签到，跳过本次运行")
                return True
    except Exception as e:
        print(f"⚠️ 读取状态文件失败: {e}")

    return False

def save_today_status(success, message=""):
    """保存今日签到状态"""
    today = datetime.now().strftime('%Y-%m-%d')
    status = {
        'date': today,
        'success': success,
        'message': message,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # 确保status目录存在
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
    
    try:
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            f.write(json.dumps(status, ensure_ascii=False, indent=2))
        print(f"💾 状态已保存: {status}")
    except Exception as e:
        print(f"⚠️ 保存状态失败: {e}")

def check_cookie(cookie):
    """检查Cookie格式"""
    if not cookie or not len(cookie):
        error_msg = "❌ 错误: Cookie为空"
        print(error_msg)
        return False, error_msg

    pairs = cookie.split(';')
    for pair_str in pairs:
        pair = pair_str.strip()
        if pair and '=' not in pair:
            error_msg = f"❌ Cookie格式错误: {pair}"
            print(error_msg)
            return False, error_msg

    print("✅ Cookie检查通过")
    return True, "Cookie格式正确"

def kanxue_checkin():
    """看雪论坛签到主函数"""
    
    # 从环境变量读取配置
    cookie = os.environ.get('KANXUE_COOKIE')
    pushplus_token = os.environ.get('PUSHPLUS_TOKEN')

    if not cookie:
        error_msg = "❌ 错误: 未找到KANXUE_COOKIE环境变量"
        print(error_msg)
        save_today_status(False, error_msg)
        return False

    # 检查Cookie格式
    cookie_valid, cookie_msg = check_cookie(cookie)
    if not cookie_valid:
        save_today_status(False, cookie_msg)
        return False

    url = "https://bbs.kanxue.com/user-signin.htm"
    
    headers = {
        'User-Agent': 'HD1910(Android/7.1.2) (pediy.UNICFBC0DD/1.0.5) Weex/0.26.0 720x1280',
        'Cookie': cookie,
        'Connection': 'keep-alive',
        'Accept': '*/*'
    }

    print("=" * 60)
    print(f"🚀 看雪论坛自动签到 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print(f"📡 目标地址: {url}")
    print(f"📦 Cookie长度: {len(cookie)} 字符")

    try:
        response = requests.post(
            url,
            headers=headers,
            timeout=30,
            verify=False
        )

        print(f"📊 HTTP状态码: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"📄 响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")

                message = data.get('message', '')
                code = data.get('code')

                if code == 0 or message == '您今日已签到成功':
                    if code == 0:
                        success_msg = f"签到成功！获得{message}雪币"
                        print(f"🎉 {success_msg}")
                    else:
                        success_msg = "今日已签到，无需重复签到"
                        print(f"ℹ️ {success_msg}")

                    # 发送推送通知
                    if pushplus_token:
                        send_pushplus(pushplus_token, success_msg, code)
                    else:
                        print("⚠️ 未设置PUSHPLUS_TOKEN，跳过推送")

                    save_today_status(True, success_msg)
                    return True
                else:
                    error_msg = f"签到失败: {message}"
                    print(f"❌ {error_msg}")
                    save_today_status(False, error_msg)
                    return False

            except json.JSONDecodeError as e:
                error_msg = f"JSON解析失败: {response.text[:200]}"
                print(f"❌ {error_msg}")
                save_today_status(False, error_msg)
                return False
        else:
            error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            print(f"❌ {error_msg}")
            save_today_status(False, error_msg)
            return False

    except requests.exceptions.Timeout:
        error_msg = "请求超时"
        print(f"❌ {error_msg}")
        save_today_status(False, error_msg)
        return False

    except requests.exceptions.ConnectionError as e:
        error_msg = f"网络连接失败: {str(e)}"
        print(f"❌ {error_msg}")
        save_today_status(False, error_msg)
        return False

    except Exception as e:
        error_msg = f"未知错误: {type(e).__name__} - {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        save_today_status(False, error_msg)
        return False

def send_pushplus(token, msg, code):
    """发送PushPlus通知"""
    if code == 0:
        title = '看雪论坛签到成功'
        content = f'🎉🎉🎉签到成功，获得{msg}雪币'
    else:
        title = '看雪论坛签到提醒'
        content = '📢您已签到，无需重复签到'

    data = {
        "token": token，
        "title": title，
        "content": content,
        "template": "json"
    }

    # 打印脱敏的推送数据（用于调试）
    debug_data = data.copy()
    if debug_data.get('token'):
        token_str = debug_data['token']
        if len(token_str) > 8:
            debug_data['token'] = token_str[:4] + '*' * (len(token_str) - 8) + token_str[-4:]
    print(f'📤 推送数据: {debug_data}')

    try:
        response = requests.post(
            'http://www.pushplus.plus/send'，
            json=data,
            timeout=10
        )
        
        if response。status_code == 200:
            result = response.json()
            print(f'✅ PushPlus推送成功: {result.get("msg", "未知")}')
        else:
            print(f'⚠️ PushPlus推送失败，状态码: {response.status_code}')
    except requests。exceptions。RequestException as e:
        print(f'⚠️ PushPlus推送异常: {str(e)}')
    except Exception as e:
        print(f'⚠️ PushPlus推送未知错误: {str(e)}')

def main():
    """主函数"""
    # 检查今日是否已成功签到
    if load_today_status():
        print("✅ 今日已完成签到，无需重复运行")
        sys.exit(0)

    # 执行签到
    success = kanxue_checkin()

    print("=" * 60)
    if success:
        print("✅ 签到任务完成")
        sys.exit(0)
    else:
        print("❌ 签到任务失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
