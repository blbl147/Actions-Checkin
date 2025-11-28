#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
看雪论坛自动签到脚本 - GitHub Actions版本
"""

import re
import json
import os
import sys
import requests
import urllib3
from datetime import datetime

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

    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)

        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            f.write(json.dumps(status, ensure_ascii=False, indent=2))
        print(f"💾 状态已保存: {status}")
    except Exception as e:
        print(f"⚠️ 保存状态失败: {e}")


class KanxueSignIn:
    def __init__(self, cookie):
        self.session = requests.Session()

        # 关键修复：禁用 SSL 证书验证
        self.session.verify = False

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'Accept': 'text/plain, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://bbs.kanxue.com',
            'Referer': 'https://bbs.kanxue.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        self.session.headers.update(self.headers)

        # 解析并设置 Cookie
        cookies = self._parse_cookie(cookie)
        self.session.cookies.update(cookies)

        self.csrf_token = None

    def _parse_cookie(self, cookie_str):
        """解析 Cookie 字符串为字典"""
        cookies = {}
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key.strip()] = value.strip()
        return cookies

    def _log(self, message, level="INFO"):
        """格式化日志输出"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [{level}] {message}")

    def get_csrf_token(self):
        """从任务页面获取 csrf_token"""
        try:
            url = 'https://bbs.kanxue.com/'
            self._log("正在获取 csrf_token...")

            response = self.session.get(url, timeout=20)

            if response.status_code != 200:
                self._log(f"访问页面失败，状态码: {response.status_code}", "ERROR")
                return False

            # 多种正则尝试提取 csrf_token
            patterns = [
                r'csrf_token["\']?\s*[:=]\s*["\']([a-f0-9]{32})["\']',
                r'name=["\']csrf_token["\']\s+value=["\']([a-f0-9]{32})["\']',
                r'data-csrf=["\']([a-f0-9]{32})["\']',
                r'var\s+csrf_token\s*=\s*["\']([a-f0-9]{32})["\']',
                r'<input[^>]*name="csrf_token"[^>]*value="([a-f0-9]{32})"',
                r'"csrf_token":"([a-f0-9]{32})"'
            ]

            for i, pattern in enumerate(patterns):
                match = re.search(pattern, response.text, re.IGNORECASE)
                if match:
                    self.csrf_token = match.group(1)
                    self._log(f"✓ 成功获取 csrf_token")
                    return True

            self._log("未能提取 csrf_token", "WARNING")
            return False

        except Exception as e:
            self._log(f"获取 csrf_token 异常: {e}", "ERROR")
            return False

    def check_signin_status(self):
        """检查今日签到状态"""
        try:
            url = 'https://bbs.kanxue.com/user-is_signin.htm'
            self._log("正在检查签到状态...")

            response = self.session.get(url, timeout=15)

            if response.status_code == 200:
                try:
                    result = response.json()

                    if result.get('code') == '0' or result.get('code') == 0:
                        message = result.get('message', '')
                        if '已签到' in str(message):
                            return 'signed'
                        else:
                            return 'unsigned'
                    return 'unknown'
                except json.JSONDecodeError:
                    return 'unknown'
            else:
                return 'error'

        except Exception as e:
            self._log(f"检查签到状态异常: {e}", "ERROR")
            return 'error'

    def sign_in(self):
        """执行签到操作"""
        try:
            url = 'https://bbs.kanxue.com/user-signin.htm'

            # 如果没有 csrf_token，先获取
            if not self.csrf_token:
                if not self.get_csrf_token():
                    return False, "无法获取 csrf_token，请检查 Cookie 是否有效"

            data = {
                'csrf_token': self.csrf_token
            }

            self._log("正在执行签到...")
            response = self.session.post(url, data=data, timeout=15)

            if response.status_code == 200:
                try:
                    result = response.json()

                    if result.get('code') == '0' or result.get('code') == 0:
                        message = result.get('message', '签到成功')
                        return True, f"签到成功！连续签到 {message} 天" if str(message).isdigit() else "签到成功！"
                    else:
                        return False, f"签到失败: {result.get('message', '未知错误')}"

                except json.JSONDecodeError:
                    # 如果不是 JSON 但状态码 200，可能也算成功
                    if '成功' in response.text or 'success' in response.text.lower():
                        return True, "签到成功"
                    return False, f"返回内容解析失败"
            else:
                return False, f"请求失败，状态码: {response.status_code}"

        except Exception as e:
            self._log(f"签到请求异常: {e}", "ERROR")
            return False, f"签到异常: {e}"

    def run(self):
        """主流程"""
        print("\n" + "="*60)
        print(f"  看雪论坛自动签到")
        print(f"  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")

        # 步骤1: 检查签到状态
        status = self.check_signin_status()

        if status == 'signed':
            self._log("✓ 今日已签到，无需重复操作", "SUCCESS")
            return True, "今日已签到"
        elif status == 'error':
            self._log("检查签到状态失败，尝试直接签到...", "WARNING")

        # 步骤2: 执行签到
        success, message = self.sign_in()

        if success:
            self._log(f"✓ {message}", "SUCCESS")
        else:
            self._log(f"✗ {message}", "ERROR")

        return success, message


def kanxue_signin():
    """看雪论坛签到主函数"""

    # 从环境变量中读取Cookie
    cookie = os.environ.get('KANXUE_COOKIE')

    if not cookie:
        error_msg = "❌ 错误: 未找到KANXUE_COOKIE环境变量"
        print(error_msg)
        print("请在GitHub Secrets中设置KANXUE_COOKIE")
        save_today_status(False, error_msg)
        return False

    try:
        signer = KanxueSignIn(cookie)
        success, message = signer.run()

        print("\n" + "="*60)
        if success:
            print("  ✓ 签到任务执行成功")
            save_today_status(True, message)
        else:
            print("  ✗ 签到任务执行失败")
            save_today_status(False, message)
        print("="*60 + "\n")

        return success

    except Exception as e:
        error_msg = f"程序异常: {e}"
        print(f"\n❌ {error_msg}\n")
        import traceback
        traceback.print_exc()
        save_today_status(False, error_msg)
        return False


def main():
    """主函数"""
    # 检查今日是否已成功签到
    if load_today_status():
        print("✅ 今日已完成签到，无需重复运行")
        sys.exit(0)

    # 执行签到
    success = kanxue_signin()

    print("=" * 60)
    if success:
        print("✅ 签到任务完成")
        sys.exit(0)
    else:
        print("❌ 签到任务失败")
        sys.exit(1)


if __name__ == "__main__":
    main()