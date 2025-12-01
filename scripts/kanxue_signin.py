#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
看雪论坛自动签到脚本 
支持 GitHub Actions 
"""

import json
import requests
import urllib3
from datetime import datetime
import os
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class KanxueSignIn:
    def __init__(self, cookie):
        self.session = requests.Session()
        self.session.verify = False
        
        # 禁用代理（重要：避免 GitHub Actions 环境问题）
        self.session.trust_env = False
        self.session.proxies = {'http': None, 'https': None}

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://bbs.kanxue.com',
            'Referer': 'https://bbs.kanxue.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
        self.session.headers.update(self.headers)

        # 解析 Cookie
        cookies = {}
        for item in cookie.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key.strip()] = value.strip()
        self.session.cookies.update(cookies)

    def _log(self, message, level="INFO"):
        """格式化日志输出"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [{level}] {message}")

    def check_signin_status(self):
        """检查今日签到状态"""
        try:
            url = 'https://bbs.kanxue.com/user-is_signin.htm'
            self._log("正在检查签到状态...")
            
            # 添加延时，避免触发反爬虫
            time.sleep(1)
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                code = str(result.get('code', ''))
                message = str(result.get('message', ''))
                
                self._log(f"签到状态: {result}")
                
                if code == '0' and '已签到' in message:
                    return 'signed'
                elif code == '1':
                    return 'unsigned'
                else:
                    return 'unknown'
            else:
                self._log(f"状态检查失败，HTTP {response.status_code}", "WARNING")
                return 'error'
                
        except Exception as e:
            self._log(f"检查签到状态异常: {e}", "ERROR")
            return 'error'

    def sign_in(self):
        """执行签到操作"""
        try:
            url = 'https://bbs.kanxue.com/user-signin.htm'
            self._log("正在执行签到...")
            
            # 添加延时
            time.sleep(2)
            
            # 直接 POST 空参数（看雪论坛不需要 csrf_token）
            response = self.session.post(url, data={}, timeout=15)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    code = str(result.get('code', ''))
                    message = result.get('message', '')
                    
                    self._log(f"签到响应: {result}")
                    
                    if code == '0':
                        # 签到成功
                        if str(message).isdigit():
                            return True, f"签到成功！连续签到 {message} 天"
                        else:
                            return True, f"签到成功！{message}"
                    else:
                        return False, f"签到失败: {message}"
                        
                except json.JSONDecodeError:
                    self._log(f"返回内容: {response.text}", "WARNING")
                    # 如果不是 JSON 但包含成功标识
                    if '成功' in response.text or 'success' in response.text.lower():
                        return True, "签到成功（非标准响应）"
                    return False, f"返回内容解析失败: {response.text[:100]}"
            elif response.status_code == 403:
                return False, "触发反爬虫限制 (403)，请稍后重试"
            else:
                return False, f"请求失败，状态码: {response.status_code}"
                
        except Exception as e:
            self._log(f"签到请求异常: {e}", "ERROR")
            return False, f"签到异常: {e}"

    def run(self):
        """主流程"""
        print("\n" + "="*60)
        print("  看雪论坛自动签到")
        print(f"  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")

        # 检查签到状态
        status = self.check_signin_status()
        
        if status == 'signed':
            self._log("✓ 今日已签到，无需重复操作", "SUCCESS")
            return True, "今日已签到"
        elif status == 'error':
            self._log("状态检查失败，尝试直接签到...", "WARNING")
        else:
            self._log("今日尚未签到，准备执行签到操作", "INFO")

        # 执行签到
        success, message = self.sign_in()
        
        if success:
            self._log(f"✓ {message}", "SUCCESS")
            return True, message
        else:
            self._log(f"✗ {message}", "ERROR")
            return False, message


def main():
    """主函数"""
    # 优先从环境变量读取 Cookie（用于 GitHub Actions）
    cookie = os.getenv('KANXUE_COOKIE', '')

    # 如果环境变量为空，从这里读取（仅本地测试）
    if not cookie:
        cookie = 'bendi'

    # 清理 Cookie 字符串
    cookie = ' '。join(cookie.split())

    if not cookie or '你的完整Cookie' in cookie:
        print("❌ 错误: 请配置 KANXUE_COOKIE 环境变量或在脚本中填入 Cookie\n")
        print("获取方法:")
        print("1. 浏览器登录 https://bbs.kanxue.com/")
        print("2. F12 打开开发者工具 → Network")
        print("3. 刷新页面，找到任意请求")
        print("4. 复制 Request Headers 中的 Cookie 值\n")
        return

    try:
        signer = KanxueSignIn(cookie)
        success, message = signer.run()

        print("\n" + "="*60)
        if success:
            print(f"  ✅ {message}")
        else:
            print(f"  ❌ {message}")
            print("  提示: 请检查 Cookie 是否正确或已过期")
        print("="*60 + "\n")

        exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断执行")
        exit(1)
    except Exception as e:
        print(f"\n❌ 程序异常: {e}\n")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == '__main__':
    main()
