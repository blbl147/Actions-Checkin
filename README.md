# ✨ Actions-Checkin

[![GitHub Actions](https://img.shields.io/badge/GitHub-Actions-2088FF?style=flat-square&logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](https://chatgpt.com/c/LICENSE)

自动化签到合集，基于 GitHub Actions 定时执行。

------

## 🎯 支持平台

| 平台          | 状态                       | 认证方式      |
| ------------- | -------------------------- | ------------- |
| 星城小程序    | ✅ 正常                     | Token + AppID |
| 雨晨 iOS 资源 | ✅ 正常                     | 账号密码      |
| 禁漫天堂      | ✅ 正常                     | 账号密码      |
| 龙空论坛      | ✅ 正常                     | Cookie        |
| 花夏数娱      | ⚠️ 网站关闭，无法签到       | 账号密码      |
| 尚香书苑      | ❌ GitHub Actions IP 被拦截 | Cookie        |
| 看雪论坛      | ❌ GitHub Actions IP 被拦截 | Cookie        |

------

## 🚀 快速开始

### 1. Fork 本仓库

点击页面右上角的 **Fork**，将仓库复制到自己的 GitHub 账户。

### 2. 配置 GitHub Secrets

进入 Fork 后的仓库：

`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

按需添加下方平台对应的 Secret。

> 注意：Secret 名称必须完全一致，内容中不要包含多余空格或换行。

------

## 🔐 Secret 配置说明

### 星城小程序

| Secret 名称     | 说明           | 示例       |
| --------------- | -------------- | ---------- |
| `CHECKIN_TOKEN` | 登录认证 Token | `抓包获取` |
| `APP_ID`        | 小程序 AppID   | `抓包获取` |

### 雨晨 iOS 资源

#### 单账号配置

| Secret 名称       | 说明     | 示例               |
| ----------------- | -------- | ------------------ |
| `YUCHEN_USERNAME` | 登录账号 | `user@example.com` |
| `YUCHEN_PASSWORD` | 登录密码 | `your_password`    |

#### 多账号配置

| Secret 名称       | 说明             | 格式       |
| ----------------- | ---------------- | ---------- |
| `YUCHEN_ACCOUNTS` | 多账号 JSON 配置 | 见下方示例 |

```json
[
  {
    "username": "account1@example.com",
    "password": "password1"
  },
  {
    "username": "account2@example.com",
    "password": "password2"
  }
]
```

### 禁漫天堂

| Secret 名称   | 说明     | 示例            |
| ------------- | -------- | --------------- |
| `JM_ACCOUNT`  | 登录账号 | `username`      |
| `JM_PASSWORD` | 登录密码 | `your_password` |

### 龙空论坛

| Secret 名称    | 说明        | 获取方式                                               |
| -------------- | ----------- | ------------------------------------------------------ |
| `LKONG_COOKIE` | 网站 Cookie | 浏览器按 `F12` → `Network`，从请求头中获取 Cookie 字段 |

### 花夏数娱

| Secret 名称     | 说明     | 示例               |
| --------------- | -------- | ------------------ |
| `HXSY_USERNAME` | 登录账号 | `user@example.com` |
| `HXSY_PASSWORD` | 登录密码 | `your_password`    |

### 尚香书苑

#### 单账号配置

| Secret 名称   | 说明        | 获取方式                                               |
| ------------- | ----------- | ------------------------------------------------------ |
| `SXSY_COOKIE` | 网站 Cookie | 浏览器按 `F12` → `Network`，从请求头中获取 Cookie 字段 |

#### 多账号配置

| Secret 名称     | 说明             | 格式       |
| --------------- | ---------------- | ---------- |
| `SXSY_ACCOUNTS` | 多账号 JSON 配置 | 见下方示例 |

```json
[
  {
    "cookie": "账号1的完整 Cookie",
    "user_agent": "Mozilla/5.0 ..."
  },
  {
    "cookie": "账号2的完整 Cookie",
    "user_agent": "Mozilla/5.0 ..."
  }
]
```

### 看雪论坛

| Secret 名称     | 说明        | 获取方式                                           |
| --------------- | ----------- | -------------------------------------------------- |
| `KANXUE_COOKIE` | 网站 Cookie | 抓取 `user-signin.htm` 或 `signin` 请求中的 Cookie |

------

## 📅 执行时间

工作流默认按照仓库内配置的 `cron` 表达式自动运行。

需要调整签到时间时，修改对应 GitHub Actions 工作流文件中的：

```yaml
schedule:
  - cron: "0 0 * * *"
```

------

## ⚠️ 免责声明

- 本项目仅供学习与交流使用，不得用于商业用途。
- 使用本项目产生的一切后果由使用者自行承担。
- 请遵守相关网站的服务条款、使用规则及当地法律法规。
- 高频请求可能导致账号异常或封禁，请合理设置执行频率。
- 请妥善保管账号、密码、Cookie 与 Token 等敏感信息。
- 开发者不对使用过程中产生的账号安全问题承担责任。

------

## 📄 License

本项目基于 [MIT License](https://chatgpt.com/c/LICENSE) 开源。
