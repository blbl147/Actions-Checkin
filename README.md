# ✨ Actions-Checkin

<div align="center">

[![GitHub Actions](https://img.shields.io/badge/GitHub-Actions-2088FF?style=flat-square&logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

**自动签到**

支持平台：花夏数娱 | 龙空论坛 | 星城小程序 | 看雪论坛(GitHub中会被检测，失效了) | 雨晨iOS资源

</div>

---

## 🎯 支持平台

| 平台 | 状态 | 认证方式 | 执行时间 |
|------|------|----------|---------|
| 🌸 花夏数娱 | ✅ | 账号密码 | 每天 03:00 |
| 🐉 龙空论坛 | ✅ | Cookie | 每天 04:00 |
| 🏙️ 星城小程序 | ✅ | Token + AppID | 每天 01:10 |
| ❄️ 看雪论坛 | ❌ | Cookie | 每天 01:30 |
| 🌧️ 雨晨iOS | ✅ | 账号密码 | 每天 03:00 |

---

## 🚀 快速开始

### 1. Fork 本仓库

点击右上角 **Fork** 按钮

### 2. 配置 Secrets

#### 🌸 花夏数娱

| Secret名称 | 说明 | 示例 |
|-----------|------|------|
| `HXSY_USERNAME` | 登录账号 | `user@example.com` |
| `HXSY_PASSWORD` | 登录密码 | `your_password` |

#### 🐉 龙空论坛

| Secret名称 | 说明 | 获取方法 |
|-----------|------|---------|
| `LKONG_COOKIE` | 网站Cookie | F12 → Network → Cookie字段 |


#### 🏙️ 星城小程序

| Secret名称 | 说明 | 获取方法 |
|-----------|------|---------|
| `CHECKIN_TOKEN` | 认证Token | 抓包获取 |
| `APP_ID` | 小程序AppID | 抓包获取 |


#### ❄️ 看雪论坛

| Secret名称 | 说明 | 获取方法 |
|-----------|------|---------|
| `KANXUE_COOKIE` | 网站Cookie | 抓签到user-signin.htm或者signin |



#### 🌧️ 雨晨iOS资源

**方式1：单账号**

| Secret名称 | 说明 | 示例 |
|-----------|------|------|
| `YUCHEN_USERNAME` | 登录账号 | `user@example.com` |
| `YUCHEN_PASSWORD` | 登录密码 | `your_password` |

**方式2：多账号**

| Secret名称 | 说明 | 格式 |
|-----------|------|------|
| `YUCHEN_ACCOUNTS` | 多账号JSON | 见下方示例 |

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
## ⚠️ 免责声明

本项目仅供学习交流使用，请勿用于商业用途
使用本项目所产生的一切后果由使用者自行承担
请遵守相关网站的服务条款和使用规则
频繁请求可能导致账号被封禁，请合理设置签到频率
开发者不对账号安全负责，请妥善保管账号信息
