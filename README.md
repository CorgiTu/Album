<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/GUI-Flet-14B8A6?style=for-the-badge&logo=flutter&logoColor=white" alt="Flet">
  <img src="https://img.shields.io/badge/API-pyncm-EE672F?style=for-the-badge&logo=netease-cloud-music&logoColor=white" alt="pyncm">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License">
</p>

<h1 align="center"> CustomPlaylistGenerator</h1>

<p align="center">
  <b>轻量级 · 开箱即用 · 跨平台歌单自动化生成与同步工具</b>
</p>

<p align="center">
  一键搜索歌手热歌，自动匹配并创建网易云音乐歌单 — 让好音乐触手可及。
</p>

---

## 简介

**CustomPlaylistGenerator** 是一款使用 Python 构建的轻量级桌面工具，基于 **Flet** 跨平台 GUI 框架，通过 **网易云音乐 API** 实现歌单的自动化检索与创建。

告别手动一首首搜歌、加歌的繁琐流程 —— 你只需输入歌手名称，工具会自动抓取该歌手的头部热门歌曲，在网易云音乐中为每一首歌曲匹配资源，然后批量创建为一个完整的歌单。

> **核心理念**：简单、纯粹、不做重基建。无需安装浏览器驱动，无需复杂的配置，开箱即用。

---

## 核心功能

- **歌手热门搜索** — 输入歌手名，自动获取其热门歌曲列表（支持自定义数量）
- **智能匹配抓取** — 基于 `pyncm` 直接调用网易云 API，逐首精准匹配歌曲资源
- **GUI 进度可视化** — 实时进度条显示 + 滚动日志面板，每一步执行状态清晰可见
- **Cookie 自动持久化** — 登录凭据本地保存，下次启动无需重复粘贴

---

## 快速开始

### 前置要求

- Python 3.10 或更高版本
- 网易云音乐账号（用于获取 Cookie）

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/your-username/CustomPlaylistGenerator.git
cd CustomPlaylistGenerator

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动应用
python src/main.py
```

### 获取 Cookie（必看）

本工具需要你的网易云音乐 **`MUSIC_U` Cookie** 来执行歌单操作。请按照以下步骤获取：

1. 打开浏览器，访问 [网易云音乐官网](https://music.163.com) 并登录你的账号
2. 按键盘 **`F12`** 打开开发者工具（或在页面右键 → "检查"）
3. 点击顶部选项卡切换到 **「Application」**（Chrome/Edge）或 **「存储」**（Firefox）
   - 如果找不到 Application 选项卡，点击 `>>` 展开更多菜单
4. 在左侧导航栏中找到 **「Cookies」** → 点击 **`https://music.163.com`**
5. 在右侧的 Cookie 列表中找到名为 **`MUSIC_U`** 的行
6. **双击该行的「Value」列**，按 `Ctrl+C`（或 `Cmd+C`）复制完整的值
7. 将复制的内容粘贴到工具的 Cookie 输入框中

> **安全说明**：MUSIC_U 是网易云用于识别登录状态的临时票据。该值仅保存在你的本地 `config.json` 文件中，**不会被上传到任何云端服务器**，也不会被发送给第三方。如果你担心安全，使用完毕后可在设置中清除。

---

## 使用指南

1. 启动应用后，在「歌手名称」输入框中填写目标歌手（如 "周杰然"）
2. 设置「抓取数量」（建议 10-50 首）
3. 可选：自定义「歌单名称」，留空将自动生成
4. 将上一步获取的 `MUSIC_U` Cookie 粘贴到输入框
5. 点击 **「生成专属歌单」** 按钮，坐等完成

应用会自动执行：**抓取歌曲 → 逐首匹配 → 创建歌单 → 批量添加**，全部完成后会弹出结果摘要。

---

## 技术栈

| 层级 | 选型 |
|------|------|
| 编程语言 | Python 3.10+ |
| GUI 框架 | [Flet](https://flet.dev/)（基于 Flutter，跨平台原生渲染） |
| 网易云 API | [pyncm](https://github.com/git-bing/pyncm)（纯 Python 封装） |
| 加密支持 | pycryptodome（AES / RSA 鉴权） |
| 异步模型 | asyncio + `to_thread` 桥接 |
| 数据存储 | JSON 文件（`config.json`） |
| 打包方案 | PyInstaller（可选，构建单文件分发） |

---

## 项目结构

```
CustomPlaylistGenerator/
├── src/
│   ├── main.py          # Flet GUI 桌面主程序（入口）
│   ├── crawler.py       # 歌曲抓取与搜索核心逻辑
│   ├── netease.py       # 网易云音乐 API 交互封装
│   └── _e2e_test.py     # 端到端验证脚本
├── config.json          # 本地配置与 Cookie 持久化（不纳入 Git）
├── requirements.txt     # Python 依赖清单
└── README.md            # 项目文档
```

---

## 免责声明

1. **仅限技术研究与学习交流** — 本项目的开发初衷是学习和研究 Python 桌面应用开发、异步编程与第三方 API 交互，**不构成任何商业服务或产品**。
2. **不收集用户隐私数据** — 所有用户数据（包括 Cookie）仅存储在用户本地 `config.json` 文件中，**不会以任何形式上传至云端或第三方服务器**。
3. **版权责任由用户自行承担** — 用户生成的歌单内容来源于网易云音乐平台，其版权归属原始权利人。使用者应遵守相关平台的服务条款，因使用本工具产生的版权或其他法律问题，**项目开发者不承担任何责任**。
4. **无担保声明** — 本项目按「现状」提供，不提供任何明示或暗示的担保。使用者需自行承担使用风险。

---

## License

本项目基于 [MIT License](LICENSE) 开源。

---

<p align="center">
  Made with Python · 跨平台 · 开源 · 轻量
</p>
