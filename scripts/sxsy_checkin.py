#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
尚香书苑 (SXSY) 自动签到脚本 - 优化版
支持自动从发布页获取最新网址
"""

import os
import sys
import time
import json
import random
import logging
import re
import warnings
import requests
import urllib3
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from typing import Optional, Dict, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from io import BytesIO
from urllib.parse import urljoin, unquote, urlparse

# 尝试导入OCR相关库（可选）
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    log_msg = "⚠️ OCR库未安装，将跳过图片识别功能"

# 注：曾用 curl_cffi 模拟 Chrome 指纹试图绕过 Cloudflare，但实测站点是按机房 IP 信誉弹 JS 质询，
# 换指纹无效（详见 README），故移除。

# 禁用SSL警告和XML解析警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

BASE_DIR = Path(__file__).resolve().parents[1]
STATUS_DIR = BASE_DIR / "status"
LOCAL_RELEASE_DIR = BASE_DIR / "gt"

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

# ==================== 配置常量 ====================
RELEASE_PAGE_URL = "https://sxsy.org/"  # 发布页地址
DEFAULT_DOMAIN = "sxsy13.com"  # 默认域名
DOMAIN_CACHE_FILE = STATUS_DIR / "sxsy_domain.json"  # 域名缓存文件

# ==================== 域名管理 ====================
DOMAIN_PATTERN = re.compile(r's\s*x\s*s\s*y\s*(\d{1,4})\s*(?:\.|。|\s)?\s*c\s*o\s*m', re.IGNORECASE)
IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'}


def domain_from_text(text: str, source: str = "") -> Optional[str]:
    """从文本中提取 sxsy数字.com，多个候选时取数字最大的域名。"""
    if not text:
        return None

    matches = DOMAIN_PATTERN.findall(text)
    if not matches:
        return None

    latest_num = max(int(num) for num in matches)
    domain = f"sxsy{latest_num}.com"
    if source:
        log.info(f"✅ 从{source}提取到域名: {domain}")
    return domain


def load_cached_domain() -> Optional[str]:
    """从缓存加载已持久化的默认域名。"""
    if not DOMAIN_CACHE_FILE.exists():
        return None

    try:
        with DOMAIN_CACHE_FILE.open('r', encoding='utf-8') as f:
            data = json.load(f)
        domain = data.get('domain', '').strip().lower()
        if not domain_from_text(domain):
            log.warning(f"域名缓存格式异常，已忽略: {domain}")
            return None

        update_time = data.get('update_time', '')
        log.info(f"📌 读取到缓存域名: {domain} (更新时间: {update_time})")
        return domain
    except Exception as e:
        log.warning(f"读取域名缓存失败: {e}")
        return None


def save_domain_cache(domain: str, source: str = "release_page") -> None:
    """保存域名到缓存"""
    try:
        DOMAIN_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            'domain': domain.lower(),
            'base_url': f"https://{domain.lower()}",
            'source': source,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        with DOMAIN_CACHE_FILE.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log.info(f"💾 域名已缓存: {domain}")
    except Exception as e:
        log.error(f"保存域名缓存失败: {e}")


def extract_domain_from_image_bytes(image_bytes: bytes, source: str) -> Optional[str]:
    """从图片内容中提取域名（使用 OCR）。"""
    if not OCR_AVAILABLE:
        log.warning("OCR库未安装，跳过图片识别")
        return None

    try:
        image = Image.open(BytesIO(image_bytes))
        variants = [image]

        try:
            resample_filter = Image.Resampling.LANCZOS
        except AttributeError:
            resample_filter = Image.LANCZOS

        gray = image.convert('L')
        variants.append(gray.resize((gray.width * 4, gray.height * 4), resample_filter))
        variants.append(
            gray.point(lambda pixel: 0 if pixel < 180 else 255, mode='1')
                .resize((gray.width * 4, gray.height * 4), resample_filter)
        )

        config = '--psm 7 -c tessedit_char_whitelist=sxsySXSY0123456789.comCOM'
        for variant in variants:
            text = pytesseract.image_to_string(variant, lang='eng', config=config)
            log.debug(f"OCR识别结果({source}): {text}")
            domain = domain_from_text(text, f"图片OCR({source})")
            if domain:
                return domain

        log.warning(f"⚠️ 图片中未识别到域名: {source}")
        return None

    except Exception as e:
        log.warning(f"图片识别失败({source}): {e}")
        return None


def extract_domain_from_image_url(img_url: str, session: requests.Session) -> Optional[str]:
    """下载线上图片并识别域名。"""
    try:
        log.info(f"🖼️ 尝试从线上图片提取域名: {img_url}")
        response = session.get(img_url, timeout=20, verify=False)
        response.raise_for_status()
        return extract_domain_from_image_bytes(response.content, img_url)
    except Exception as e:
        log.warning(f"下载图片失败({img_url}): {e}")
        return None


def extract_domain_from_image_file(image_path: Path) -> Optional[str]:
    """识别本地图片中的域名。"""
    try:
        log.info(f"🖼️ 尝试从本地图片提取域名: {image_path}")
        return extract_domain_from_image_bytes(image_path.read_bytes(), str(image_path))
    except Exception as e:
        log.warning(f"读取本地图片失败({image_path}): {e}")
        return None


def resolve_local_asset(html_path: Path, src: str) -> Optional[Path]:
    """将保存页里的图片路径解析为本地文件路径。"""
    if not src:
        return None

    parsed = urlparse(src)
    if parsed.scheme or parsed.netloc:
        return None

    local_part = unquote(parsed.path).lstrip('/\\')
    if not local_part:
        return None

    return (html_path.parent / local_part).resolve()


def extract_domain_from_html(content: str, base_url: str, session: Optional[requests.Session] = None,
                             html_path: Optional[Path] = None) -> Optional[str]:
    """从发布页 HTML 文本、链接和图片中提取域名。"""
    domain = domain_from_text(content, "发布页文本")
    if domain:
        return domain

    soup = BeautifulSoup(content, 'html.parser')

    for tag in soup.find_all(['a', 'img']):
        for attr in ('href', 'src', 'data-src'):
            value = tag.get(attr)
            domain = domain_from_text(value or '', f"发布页{attr}属性")
            if domain:
                return domain

    log.info("📸 未在发布页文本或链接中找到域名，尝试从图片识别")
    seen_images = set()
    for img in soup.find_all('img'):
        img_src = img.get('src') or img.get('data-src')
        if not img_src:
            continue

        if html_path:
            image_path = resolve_local_asset(html_path, img_src)
            if image_path and image_path.exists() and image_path not in seen_images:
                seen_images.add(image_path)
                domain = extract_domain_from_image_file(image_path)
                if domain:
                    return domain
        elif session:
            img_url = urljoin(base_url, img_src)
            if img_url not in seen_images:
                seen_images.add(img_url)
                domain = extract_domain_from_image_url(img_url, session)
                if domain:
                    return domain

    return None


def fetch_latest_domain_from_local_release_page() -> Optional[str]:
    """从仓库保存的 gt 发布页兜底提取域名。"""
    if not LOCAL_RELEASE_DIR.exists():
        log.warning(f"本地发布页目录不存在: {LOCAL_RELEASE_DIR}")
        return None

    html_files = sorted(
        list(LOCAL_RELEASE_DIR.rglob('*.html')) + list(LOCAL_RELEASE_DIR.rglob('*.htm'))
    )

    for html_path in html_files:
        try:
            content = html_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            log.warning(f"读取本地发布页失败({html_path}): {e}")
            continue

        domain = extract_domain_from_html(
            content=content,
            base_url=html_path.as_uri(),
            html_path=html_path
        )
        if domain:
            log.info(f"✅ 从本地发布页获取到最新域名: {domain}")
            return domain

    for image_path in sorted(LOCAL_RELEASE_DIR.rglob('*')):
        if image_path.suffix.lower() in IMAGE_SUFFIXES:
            domain = extract_domain_from_image_file(image_path)
            if domain:
                log.info(f"✅ 从本地发布页图片获取到最新域名: {domain}")
                return domain

    log.warning("⚠️ 未能从本地 gt 发布页提取到域名")
    return None


def fetch_latest_domain_from_release_page() -> Optional[str]:
    """从线上发布页获取最新域名；线上失败或无结果时使用本地 gt 兜底。"""
    log.info(f"🔍 正在从发布页获取最新域名: {RELEASE_PAGE_URL}")

    try:
        session = requests.Session()
        session.verify = False

        response = session.get(
            RELEASE_PAGE_URL,
            timeout=30,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        response.raise_for_status()

        domain = extract_domain_from_html(response.text, RELEASE_PAGE_URL, session=session)
        if domain:
            log.info(f"✅ 从线上发布页获取到最新域名: {domain}")
            return domain

    except Exception as e:
        log.error(f"❌ 从线上发布页获取域名失败: {e}")

    log.info("尝试使用本地 gt 保存页作为发布页兜底")
    return fetch_latest_domain_from_local_release_page()


def refresh_domain_after_failure(current_domain: str) -> Optional[str]:
    """默认域名访问或签到失败后，从发布页刷新域名（不立即持久化，成功后才写回）。"""
    new_domain = fetch_latest_domain_from_release_page()
    if new_domain:
        return new_domain

    cached_domain = load_cached_domain()
    if cached_domain and cached_domain != current_domain:
        log.warning(f"发布页解析失败，使用缓存域名兜底: {cached_domain}")
        return cached_domain

    return None


def get_working_domain() -> str:
    """默认域名：优先使用已持久化的域名（昨天成功的新域名），无缓存才用内置默认。"""
    cached = load_cached_domain()
    if cached:
        log.info(f"默认先使用已保存域名: {cached}")
        return cached
    log.info(f"默认先使用内置域名: {DEFAULT_DOMAIN}")
    return DEFAULT_DOMAIN


def test_domain_availability(domain: str) -> bool:
    """测试域名是否可用"""
    try:
        url = f"https://{domain}"
        response = requests.get(
            url,
            timeout=10,
            verify=False,
            allow_redirects=True,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        # 检查是否返回正常页面
        if response.status_code == 200 and len(response.content) > 1000:
            log.debug(f"✅ 域名 {domain} 可用")
            return True
        else:
            log.debug(f"❌ 域名 {domain} 返回异常: {response.status_code}")
            return False
    except Exception as e:
        log.debug(f"❌ 域名 {domain} 不可用: {e}")
        return False

# ==================== 工具函数 ====================
def sleep_random(min_sec: int = 2, max_sec: int = 5) -> None:
    """随机延迟，避免被检测"""
    delay = random.uniform(min_sec, max_sec)
    log.debug(f"等待 {delay:.2f} 秒...")
    time.sleep(delay)

def mask_cookie(cookie: str) -> str:
    """对Cookie进行脱敏处理"""
    if not cookie or len(cookie) <= 20:
        return "***"
    return f"{cookie[:10]}...{cookie[-10:]}"

def solve_arithmetic(text: str) -> Optional[str]:
    """解析并计算算术验证题"""
    match = re.search(r'(-?\d+)\s*([+\-xX*/])\s*(-?\d+)\s*=', text)
    if not match:
        return None

    left = int(match.group(1))
    op = match.group(2)
    right = int(match.group(3))

    try:
        if op == '+':
            answer = left + right
        elif op == '-':
            answer = left - right
        elif op in ['x', 'X', '*']:
            answer = left * right
        elif op == '/':
            if right == 0:
                return None
            answer = left / right
        else:
            return None

        return str(int(answer))
    except:
        return None

# ==================== 配置管理 ====================
class Config:
    """从环境变量读取配置"""

    @staticmethod
    def get_accounts() -> List[Dict[str, str]]:
        """从环境变量读取账号配置（支持多账号）"""
        accounts = []

        # 方式1: 单账号配置（使用Cookie）
        cookie = os.getenv('SXSY_COOKIE', '').strip()
        if cookie:
            accounts.append({
                'cookie': cookie,
                'user_agent': os.getenv('USER_AGENT',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36')
            })
            log.info(f"✅ 从环境变量读取到 1 个账号")

        # 方式2: 多账号配置（使用JSON格式）
        accounts_json = os.getenv('SXSY_ACCOUNTS', '').strip()
        if accounts_json:
            try:
                multi_accounts = json.loads(accounts_json)
                accounts.extend(multi_accounts)
                log.info(f"✅ 从SXSY_ACCOUNTS读取到 {len(multi_accounts)} 个账号")
            except json.JSONDecodeError:
                log.warning("⚠️ SXSY_ACCOUNTS格式错误，已忽略")

        if not accounts:
            log.error("❌ 未检测到任何账号配置！")
            log.info("配置方式1: 设置 SXSY_COOKIE")
            log.info("配置方式2: 设置 SXSY_ACCOUNTS (JSON数组)")

        return accounts


# ==================== 主业务类 ====================
class SXSYCheckin:
    """尚香书苑签到类"""

    def __init__(self, domain: str = None, **kwargs):
        self.domain: str = (domain or DEFAULT_DOMAIN).strip().lower()
        self.base_url: str = f"https://{self.domain}"
        self.cookie: str = kwargs.get('cookie', '')
        self.user_agent: str = kwargs.get('user_agent',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36')

        # 签到结果记录
        self.signin_success = False
        self.signin_message = ""
        self.formhash = ""
        self.math_verify = ""
        self.domain_changed = False

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

        # 设置Cookie
        if self.cookie:
            for item in self.cookie.split(';'):
                item = item.strip()
                if '=' in item:
                    key, value = item.split('=', 1)
                    self.session.cookies.set(key.strip(), value.strip())

        log.info(f"🌐 使用域名: {self.domain}")
        log.debug(f"Cookie: {mask_cookie(self.cookie)}")

    def headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Host": self.domain,
            "Referer": f"{self.base_url}/forum.php",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": self.user_agent,
            "X-Requested-With": "XMLHttpRequest",
            "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"'
        }

    def update_domain(self, new_domain: str) -> None:
        """切换到新域名（仅在签到成功后才会被持久化）"""
        if new_domain != self.domain:
            log.info(f"🔄 更新域名: {self.domain} -> {new_domain}")
            self.domain = new_domain.lower()
            self.base_url = f"https://{self.domain}"
            self.domain_changed = True

    def get_sign_page(self) -> bool:
        """访问签到页面，获取formhash和验证题"""
        try:
            url = f"{self.base_url}/plugin.php?id=k_misign:sign"

            response = self.session.get(
                url=url,
                headers=self.headers(),
                timeout=30,
                verify=False,
                allow_redirects=True
            )
            response.raise_for_status()

            # 检查是否已签到
            if '已签到' in response.text or '已签到' in response.text:
                log.info("✅ 今天已经签到过了")
                self.signin_success = True
                self.signin_message = "今天已经签到过了"
                return False

            # 提取formhash
            formhash_match = re.search(r'formhash=([a-f0-9]+)', response.text)
            if formhash_match:
                self.formhash = formhash_match.group(1)
                log.debug(f"formhash: {self.formhash}")
            else:
                self.signin_message = "未找到formhash"
                log.error("未找到formhash")
                return False

            # 提取算术验证题
            math_match = re.search(r'请输入答案:\s*(-?\d+)\s*([+\-xX*/])\s*(-?\d+)\s*=', response.text)
            if math_match:
                question = f"{math_match.group(1)} {math_match.group(2)} {math_match.group(3)} ="
                answer = solve_arithmetic(question)
                if answer:
                    self.math_verify = answer
                    log.info(f"🧮 算术验证: {question} {answer}")
                else:
                    log.warning("⚠️ 无法计算验证题")
            else:
                log.debug("未检测到算术验证题")

            return True

        except requests.exceptions.RequestException as e:
            self.signin_message = f"访问签到页面失败: {e}"
            log.error(f"访问签到页面失败: {e}")
            # 如果是连接错误，可能是域名失效
            if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                log.warning("⚠️ 可能是域名失效，将尝试获取最新域名")
            return False
        except Exception as e:
            self.signin_message = f"访问签到页面异常: {e}"
            log.error(f"访问签到页面异常: {e}")
            return False

    def do_checkin(self) -> None:
        """执行签到操作"""
        try:
            # 构建签到URL
            url = f"{self.base_url}/plugin.php"
            params = {
                'id': 'k_misign:sign',
                'operation': 'qiandao',
                'formhash': self.formhash,
                'format': 'global_usernav_extra',
                'inajax': '1',
                'ajaxtarget': 'k_misign_topb'
            }

            # 如果有算术验证，添加答案
            if self.math_verify:
                params['mathverify_answer'] = self.math_verify

            response = self.session.get(
                url=url,
                params=params,
                headers=self.headers(),
                timeout=30,
                verify=False
            )
            response.raise_for_status()

            # 解析响应
            response_text = response.text
            log.debug(f"签到响应: {response_text[:200]}")

            # 判断签到结果
            if '签到成功' in response_text or '恭喜' in response_text:
                self.signin_success = True
                self.signin_message = "签到成功"
                log.info("✅ 签到成功")
            elif '已签到' in response_text or '已经签到' in response_text or '今日已签' in response_text:
                self.signin_success = True
                self.signin_message = "今天已经签到过了"
                log.info("✅ 今天已经签到过了")
            elif '验证码错误' in response_text or '答案错误' in response_text:
                self.signin_success = False
                self.signin_message = "验证码错误"
                log.error("❌ 验证码错误")
            else:
                # 尝试从XML响应中提取信息
                if '<root>' in response_text:
                    soup = BeautifulSoup(response_text, 'html.parser')
                    content = soup.get_text()
                    if content:
                        self.signin_message = content.strip()
                        # 判断是否包含成功关键词
                        if any(keyword in content for keyword in ['签到', '成功', '已签', '今日']):
                            self.signin_success = True
                            log.info(f"✅ {content.strip()}")
                        else:
                            self.signin_success = False
                            log.warning(f"⚠️ {content.strip()}")
                    else:
                        self.signin_success = False
                        self.signin_message = "签到响应异常"
                        log.warning(f"⚠️ 签到响应异常，响应长度: {len(response_text)}")
                else:
                    self.signin_success = False
                    self.signin_message = "签到响应异常"
                    log.warning(f"⚠️ 签到响应异常，响应长度: {len(response_text)}")

        except Exception as e:
            self.signin_success = False
            self.signin_message = f"签到请求失败: {type(e).__name__}"
            log.error(f"签到失败: {type(e).__name__}")

    def run(self) -> Dict:
        """执行完整流程，返回执行结果"""
        result = {
            'success': False,
            'message': '',
            'domain_changed': False
        }

        if not self.cookie:
            result['message'] = "Cookie信息不完整"
            log.warning("❌ Cookie信息不完整，跳过")
            return result

        # 第一次尝试：使用当前域名
        if self.get_sign_page():
            sleep_random(2, 4)
            self.do_checkin()

        # 如果第一次失败，尝试更新域名后重试
        if not self.signin_success:
            log.warning("⚠️ 签到失败，尝试获取最新域名后重试")
            new_domain = refresh_domain_after_failure(self.domain)

            if new_domain and new_domain != self.domain:
                previous_message = self.signin_message
                self.update_domain(new_domain)
                log.info("🔄 使用新域名重试签到")

                # 重置状态
                self.formhash = ""
                self.math_verify = ""

                # 第二次尝试
                if self.get_sign_page():
                    sleep_random(2, 4)
                    self.do_checkin()
                if not self.signin_success and not self.signin_message:
                    self.signin_message = previous_message or "使用新域名重试失败"
            elif new_domain == self.domain:
                if not self.signin_message:
                    self.signin_message = f"发布页返回的域名仍是当前域名 {self.domain}"
                log.warning(f"发布页返回的域名仍是当前域名 {self.domain}，不重复同域名重试")
            else:
                if not self.signin_message:
                    self.signin_message = "未能获取可用于重试的新域名"
                log.error("未能获取可用于重试的新域名")

        result['success'] = self.signin_success
        result['message'] = self.signin_message
        result['domain_changed'] = self.domain_changed

        return result


# ==================== 主函数 ====================
def main():
    log.info("=" * 60)
    log.info("🚀 尚香书苑自动签到脚本启动 (优化版)")
    log.info(f"⏰ 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 60)

    # 默认域名来自已持久化的缓存（昨天成功的新域名），无缓存才用内置默认。
    working_domain = get_working_domain()
    log.info(f"🌐 当前使用域名: {working_domain}")

    # 获取账号配置
    accounts = Config.get_accounts()

    if not accounts:
        log.error("❌ 未配置任何账号！")
        sys.exit(1)

    log.info(f"检测到 {len(accounts)} 个账号\n")

    # 执行签到
    success_count = 0
    fail_count = 0

    for i, account_config in enumerate(accounts, 1):
        log.info(f"\n{'='*60}")
        log.info(f"📱 账号 {i}/{len(accounts)} 开始执行")
        log.info(f"{'='*60}")

        try:
            sxsy = SXSYCheckin(domain=working_domain, **account_config)
            result = sxsy.run()

            if result.get('domain_changed'):
                working_domain = sxsy.domain
                log.info(f"🔄 后续账号将使用新域名: {working_domain}")
                # 仅当切换到的新域名签到成功时，才持久化为新的默认域名（次日生效）
                if result['success']:
                    save_domain_cache(working_domain, source="verified")

            if result['success']:
                success_count += 1
                log.info(f"✅ 账号 {i} 签到成功")
            else:
                fail_count += 1
                log.error(f"❌ 账号 {i} 签到失败: {result['message']}")

            # 账号间延迟
            if i < len(accounts):
                sleep_random(5, 10)

        except Exception as e:
            fail_count += 1
            log.error(f"❌ 账号 {i} 执行异常: {e}", exc_info=True)

    # 总结
    log.info(f"\n{'='*60}")
    log.info(f"📊 执行完毕")
    log.info(f"   - 成功: {success_count} 个账号")
    log.info(f"   - 失败: {fail_count} 个账号")
    log.info(f"   - 当前域名: {working_domain}")
    log.info(f"{'='*60}")

    all_success = (fail_count == 0 and success_count > 0)

    # 退出码
    sys.exit(0 if all_success else 1)


if __name__ == '__main__':
    main()
