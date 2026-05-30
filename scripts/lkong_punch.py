#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
龙空论坛自动签到脚本 - GitHub Actions版本
"""

import requests
import json
import os
import sys
from datetime import datetime
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def lkong_punch():
    """龙空论坛签到主函数"""

    # 从环境变量中读取Cookie（GitHub Secrets）
    cookie = os.environ.get('LKONG_COOKIE')

    if not cookie:
        error_msg = "❌ 错误: 未找到LKONG_COOKIE环境变量"
        print(error_msg)
        print("请在GitHub Secrets中设置LKONG_COOKIE")
        return False

    url = "https://api.lkong.com/api"

    # 从环境变量读取请求体（可选，提供默认值）
    request_body_str = os.environ.get('LKONG_REQUEST_BODY')

    if request_body_str:
        try:
            request_body = json.loads(request_body_str)
        except json.JSONDecodeError:
            print("⚠️ LKONG_REQUEST_BODY格式错误，使用默认请求体")
            request_body = {
                "operationName": "DoPunch",
                "variables": {},
                "query": "mutation DoPunch { punch { uid punchday isPunch punchhighestday punchallday __typename } }"
            }
    else:
        request_body = {
            "operationName": "DoPunch",
            "variables": {},
            "query": "mutation DoPunch { punch { uid punchday isPunch punchhighestday punchallday __typename } }"
        }

    headers = {
        "Cookie": cookie,
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Origin": "https://www.lkong.com",
        "Referer": "https://www.lkong.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty"
    }

    print("=" * 60)
    print(f"🚀 龙空论坛自动签到 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print(f"📡 目标地址: {url}")
    print("📦 Cookie: 已配置")

    try:
        response = requests.post(
            url,
            json=request_body,
            headers=headers,
            timeout=30,
            verify=False,
            allow_redirects=True
        )

        print(f"📊 HTTP状态码: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                # print(f"📄 响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")

                # 解析签到数据
                if data.get("data") and data["data"].get("punch"):
                    punch_data = data["data"]["punch"]

                    is_punch = punch_data.get("isPunch", False)
                    punch_day = punch_data.get("punchday", 0)
                    highest_day = punch_data.get("punchhighestday", 0)
                    all_day = punch_data.get("punchallday", 0)

                    if is_punch:
                        success_msg = f"签到成功！已连签{punch_day}天"
                        print(f"🎉 {success_msg}")
                        print(f"📅 连续签到: {punch_day} 天")
                        print(f"🏆 最高连签: {highest_day} 天")
                        print(f"📊 总签到数: {all_day} 天")

                        return True
                    else:
                        # isPunch为false可能表示今天已经签到过了
                        msg = f"签到状态未知 (isPunch=false), 连签{punch_day}天"
                        print(f"⚠️ {msg}")
                        # 也记录为成功，因为可能已经签到过了
                        return True

                elif data.get("errors"):
                    # GraphQL错误
                    error_msg = f"GraphQL错误，数量: {len(data['errors'])}"
                    print(f"❌ {error_msg}")
                    return False
                else:
                    error_msg = f"响应格式异常，字段: {list(data.keys())}"
                    print(f"❌ {error_msg}")
                    return False

            except json.JSONDecodeError as e:
                error_msg = f"JSON解析失败，响应长度: {len(response.text)}"
                print(f"❌ {error_msg}")
                return False
        else:
            error_msg = f"HTTP {response.status_code}，响应长度: {len(response.text)}"
            print(f"❌ {error_msg}")
            return False

    except requests.exceptions.Timeout:
        error_msg = "请求超时"
        print(f"❌ {error_msg}")
        return False

    except requests.exceptions.ConnectionError as e:
        error_msg = f"网络连接失败: {str(e)[:100]}"
        print(f"❌ {error_msg}")
        return False

    except Exception as e:
        error_msg = f"未知错误: {type(e).__name__} - {str(e)[:100]}"
        print(f"❌ {error_msg}")
        return False

def main():
    """主函数"""
    # 执行签到
    success = lkong_punch()

    print("=" * 60)
    if success:
        print("✅ 签到任务完成")
        sys.exit(0)
    else:
        print("❌ 签到任务失败")
        sys.exit(1)  # 退出码1表示失败

if __name__ == "__main__":
    main()
