# ✨ Actions-Checkin

<div align="center">

[![GitHub Actions](https://img.shields.io/badge/GitHub-Actions-2088FF?style=flat-square&logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

**基于 GitHub Actions 的多平台自动签到工具**

支持平台：花夏数娱 | 龙空论坛 | 星城小程序 | 看雪论坛 | 雨晨iOS资源

</div>

---

## 🎯 支持平台

| 平台 | 状态 | 认证方式 | 执行时间 |
|------|------|----------|---------|
| 🌸 花夏数娱 | ✅ | 账号密码 | 每天 03:00 |
| 🐉 龙空论坛 | ✅ | Cookie | 每天 04:00 |
| 🏙️ 星城小程序 | ✅ | Token + AppID | 每天 01:10 |
| ❄️ 看雪论坛 | ✅ | Cookie | 每天 01:30 |
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
| `KANXUE_COOKIE` | 网站Cookie | F12 → Network → Cookie字段 |



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
