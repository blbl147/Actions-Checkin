import os
import sys
import time
import json
import random
import logging
import requests
import urllib3
from datetime import datetime
from bs4 import BeautifulSoup
from typing import Optional, Dict, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('yuchen.log', encoding='utf-8')
    ]
)
log = logging.getLogger(__name__)

# ==================== 状态管理 ====================
STATUS_FILE = "status.json"

def load_today_status() -> bool:
    """加载今日签到状态"""
    if not os.path.exists(STATUS_FILE):
        return False
    
    try:
        with open(STATUS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            today = datetime.now().strftime('%Y-%m-%d')
            
            if data.get('date') == today and data.get('success'):
                log.info(f"✅ 今日({today})已成功签到，跳过本次运行")
                return True
    except Exception as e:
        log.warning(f"读取状态文件失败: {e}")
    
    return False

def save_today_status(success: bool, message: str = "", accounts_detail: List[Dict] = None) -> None:
    """保存今日签到状态"""
    today = datetime.now().strftime('%Y-%m-%d')
    status = {
        'date': today,
        'success': success,
        'message': message,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'accounts_detail': accounts_detail or []
    }
    
    try:
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
        log.info(f"💾 状态已保存: success={success}, message={message}")
    except Exception as e:
        log.error(f"保存状态失败: {e}")

# ==================== 工具函数 ====================
def sleep_random(min_sec: int = 3, max_sec: int = 8) -> None:
    """随机延迟，避免被检测"""
    delay = random.uniform(min_sec, max_sec)
    log.debug(f"等待 {delay:.2f} 秒...")
    time.sleep(delay)


class LoginResultHandler:
    """处理登录返回结果"""
    def __init__(self, response_json: dict):
        self.success = response_json.get('success', 'error')
        self.msg = response_json.get('msg', '未知错误')


# ==================== 配置管理 ====================
class Config:
    """从环境变量读取配置"""

    @staticmethod
    def get_accounts() -> List[Dict[str, str]]:
        """从环境变量读取账号配置（支持多账号）"""
        accounts = []

        # 方式1: 单账号配置
        username = os.getenv('YUCHEN_USERNAME', '').strip()
        password = os.getenv('YUCHEN_PASSWORD', '').strip()

        if username and password:
            accounts.append({
                'username': username,
                'password': password,
                'user_agent': os.getenv('USER_AGENT',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            })
            log.info(f"✅ 从环境变量读取到 1 个账号: {username}")

        # 方式2: 多账号配置（使用JSON格式）
        accounts_json = os.getenv('YUCHEN_ACCOUNTS', '').strip()
        if accounts_json:
            try:
                multi_accounts = json.loads(accounts_json)
                accounts.extend(multi_accounts)
                log.info(f"✅ 从YUCHEN_ACCOUNTS读取到 {len(multi_accounts)} 个账号")
            except json.JSONDecodeError:
                log.warning("⚠️ YUCHEN_ACCOUNTS格式错误，已忽略")

        if not accounts:
            log.error("❌ 未检测到任何账号配置！")
            log.info("配置方式1: 设置 YUCHEN_USERNAME 和 YUCHEN_PASSWORD")
            log.info("配置方式2: 设置 YUCHEN_ACCOUNTS (JSON数组)")

        return accounts


# ==================== 主业务类 ====================
class YuChen:
    """雨晨iOS资源签到类"""

    def __init__(self, **kwargs):
        self.url: str = "yc.yuchengyouxi.com"
        self.username: str = kwargs.get('username', '')
        self.password: str = kwargs.get('password', '')
        self.user_agent: str = kwargs.get('user_agent',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # 签到结果记录
        self.signin_success = False
        self.signin_message = ""
        self.credit_info = ""

        # 创建session并配置
        self.session = requests.session()
        self.session.verify = False

        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        log.debug(self.__str__())

    def __str__(self):
        masked_pwd = self.password[:2] + '*' * (len(self.password) - 2) if len(self.password) > 2 else '***'
        return f'username={self.username}, password={masked_pwd}'

    def headers(self) -> Dict[str, str]:
        """增强请求头，模拟真实浏览器"""
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Host": self.url,
            "Origin": "https://" + self.url,
            "Referer": "https://" + self.url + "/",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": self.user_agent
        }

    def get_token(self) -> Optional[str]:
        """获取登录所需token"""
        try:
            url = f"https://{self.url}/login"

            response = self.session.get(
                url=url,
                headers=self.headers(),
                timeout=30,
                verify=False,
                allow_redirects=True
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            token_input = soup.find('input', {'name': 'token'})

            if token_input:
                token = token_input.get('value')
                log.debug(f"token: {token}")
                return token
            else:
                log.error("未找到token输入框")
                return None
        except Exception as e:
            log.error(f"获取token失败: {e}")
            return None

    def yu_chen_login(self) -> bool:
        """登录网站"""
        try:
            token = self.get_token()
            if not token:
                log.error("无法获取token，登录失败")
                return False

            url = f"https://{self.url}/wp-admin/admin-ajax.php"
            data = {
                "user_login": self.username,
                "password": self.password,
                "rememberme": "1",
                "redirect": f"https://{self.url}/",
                "action": "userlogin_form",
                "token": token
            }

            response = self.session.post(
                url=url,
                data=data,
                headers=self.headers(),
                timeout=30,
                verify=False
            )
            response.raise_for_status()

            result = response.json()
            log.debug(f"登录响应: {result}")

            message = LoginResultHandler(result)
            if message.success == "error":
                log.error(f"登录失败: {message.msg}")
                return False

            log.info("✅ 登录成功")
            return True

        except Exception as e:
            log.error(f"登录异常: {e}")
            return False

    def yu_chen_check(self) -> None:
        """签到"""
        try:
            url = f"https://{self.url}/wp-admin/admin-ajax.php"
            data = {"action": "daily_sign"}

            response = self.session.post(
                url=url,
                data=data,
                headers=self.headers(),
                timeout=30,
                verify=False
            )
            response.raise_for_status()

            result = response.json()
            log.debug(f"签到响应: {result}")

            message = LoginResultHandler(result)
            self.signin_message = message.msg
            
            # 判断签到是否成功
            if message.success != "error":
                self.signin_success = True
                log.info(f"✅ 签到结果: {message.msg}")
            else:
                self.signin_success = False
                log.warning(f"⚠️ 签到结果: {message.msg}")

        except Exception as e:
            self.signin_success = False
            self.signin_message = f"签到请求失败: {str(e)}"
            log.error(f"签到失败: {e}")

    def yu_chen_info(self) -> None:
        """获取积分信息"""
        try:
            url = f"https://{self.url}/users?tab=credit"
            response = self.session.get(
                url=url,
                headers=self.headers(),
                timeout=30,
                verify=False
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            tips_div = soup.find('div', {'class': 'header_tips'})

            if tips_div:
                text = tips_div.text.strip()
                self.credit_info = text
                log.info(f"💰 {text}")
            else:
                log.warning("未找到积分信息")

        except Exception as e:
            log.error(f"获取积分信息失败: {e}")

    def run(self) -> Dict:
        """执行完整流程，返回执行结果"""
        result = {
            'username': self.username,
            'success': False,
            'message': '',
            'credit_info': ''
        }

        if not self.username or not self.password:
            result['message'] = "账号信息不完整"
            log.warning("❌ 账号信息不完整，跳过")
            return result

        if self.yu_chen_login():
            sleep_random(2, 5)
            self.yu_chen_check()
            sleep_random(1, 3)
            self.yu_chen_info()
            
            result['success'] = self.signin_success
            result['message'] = self.signin_message
            result['credit_info'] = self.credit_info
        else:
            result['message'] = "登录失败"

        return result


# ==================== 主函数 ====================
def main():
    log.info("=" * 60)
    log.info("🚀 雨晨iOS资源自动签到脚本启动")
    log.info(f"⏰ 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 60)

    # 检查今日是否已成功签到
    if load_today_status():
        log.info("✅ 今日已完成签到，程序退出")
        sys.exit(0)

    # 获取账号配置
    accounts = Config.get_accounts()

    if not accounts:
        log.error("❌ 未配置任何账号！")
        save_today_status(False, "未配置账号")
        sys.exit(1)

    log.info(f"检测到 {len(accounts)} 个账号\n")

    # 执行签到
    success_count = 0
    fail_count = 0
    accounts_detail = []

    for i, account_config in enumerate(accounts, 1):
        log.info(f"\n{'='*60}")
        log.info(f"📱 账号 {i}/{len(accounts)} 开始执行")
        log.info(f"{'='*60}")

        try:
            yuchen = YuChen(**account_config)
            result = yuchen.run()
            
            accounts_detail.append(result)
            
            if result['success']:
                success_count += 1
                log.info(f"✅ 账号 {i} ({result['username']}) 签到成功")
            else:
                fail_count += 1
                log.error(f"❌ 账号 {i} ({result['username']}) 签到失败: {result['message']}")

            # 账号间延迟
            if i < len(accounts):
                sleep_random(5, 10)

        except Exception as e:
            fail_count += 1
            log.error(f"❌ 账号 {i} 执行异常: {e}", exc_info=True)
            accounts_detail.append({
                'username': account_config.get('username', 'unknown'),
                'success': False,
                'message': f"执行异常: {str(e)}"
            })

    # 总结
    log.info(f"\n{'='*60}")
    log.info(f"📊 执行完毕")
    log.info(f"   - 成功: {success_count} 个账号")
    log.info(f"   - 失败: {fail_count} 个账号")
    log.info(f"{'='*60}")

    # 保存状态
    all_success = (fail_count == 0 and success_count > 0)
    summary_msg = f"成功{success_count}个，失败{fail_count}个"
    save_today_status(all_success, summary_msg, accounts_detail)

    # 退出码
    sys.exit(0 if all_success else 1)


if __name__ == '__main__':
    main()
