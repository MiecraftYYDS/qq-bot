# 📤 Git 上传到 GitHub 详细指南

本文档详细介绍如何将机器人项目上传到 GitHub。

## 📋 目录

1. [准备工作](#1-准备工作)
2. [安装 Git](#2-安装-git)
3. [配置 Git](#3-配置-git)
4. [创建 GitHub 仓库](#4-创建-github-仓库)
5. [初始化本地仓库](#5-初始化本地仓库)
6. [创建 .gitignore](#6-创建-gitignore)
7. [提交代码](#7-提交代码)
8. [推送到 GitHub](#8-推送到-github)
9. [后续维护](#9-后续维护)
10. [常见问题](#10-常见问题)

---

## 1. 准备工作

### 需要准备的东西

- [ ] GitHub 账号 (没有的话去 https://github.com 注册)
- [ ] Git 软件
- [ ] 项目文件

### 敏感信息处理

**⚠️ 重要：上传前必须处理敏感信息！**

需要隐藏的信息：
- `config.yml` 中的 `zhipu.api_key`（AI API 密钥）
- `config.yml` 中的 `onebot.token`（OneBot 鉴权 Token）
- `config.yml` 中的 `auth.secret_key`（JWT 密钥）
- `bot.qq_id` 和 `admin_qq`（可选，看你是否介意公开）

---

## 2. 安装 Git

### Windows

1. 下载 Git: https://git-scm.com/download/win
2. 运行安装程序
3. 一直点 Next，使用默认设置即可
4. 安装完成后，在任意文件夹右键应该能看到 "Git Bash Here"

### 验证安装

打开命令行（CMD 或 PowerShell）：

```bash
git --version
```

应该显示类似 `git version 2.43.0.windows.1`

---

## 3. 配置 Git

首次使用需要配置用户名和邮箱：

```bash
# 设置用户名（你的 GitHub 用户名）
git config --global user.name "你的用户名"

# 设置邮箱（你的 GitHub 注册邮箱）
git config --global user.email "你的邮箱@example.com"
```

### 配置 SSH 密钥（推荐）

SSH 密钥可以免去每次推送输密码的麻烦。

1. **生成 SSH 密钥**

```bash
ssh-keygen -t ed25519 -C "你的邮箱@example.com"
```

一直按 Enter 使用默认设置。

2. **复制公钥**

```bash
# Windows PowerShell
Get-Content ~/.ssh/id_ed25519.pub | Set-Clipboard

# 或者手动打开文件
notepad ~/.ssh/id_ed25519.pub
```

3. **添加到 GitHub**

- 打开 GitHub → Settings → SSH and GPG keys
- 点击 "New SSH key"
- Title 填 "我的电脑"（随便填）
- Key 粘贴刚才复制的公钥
- 点击 "Add SSH key"

4. **测试连接**

```bash
ssh -T git@github.com
```

首次连接会提示确认，输入 `yes`。成功后显示：
`Hi 用户名! You've successfully authenticated...`

---

## 4. 创建 GitHub 仓库

1. 登录 GitHub
2. 点击右上角 "+" → "New repository"
3. 填写信息：
   - **Repository name**: `qq-bot`（或你喜欢的名字）
   - **Description**: `基于 FastAPI 的 QQ 群聊机器人`
   - **Public/Private**: 选择公开或私有
   - **⚠️ 不要勾选** "Add a README file"（我们已经有了）
   - **⚠️ 不要勾选** "Add .gitignore"（我们自己创建）
4. 点击 "Create repository"

创建后会显示一个页面，记住你的仓库地址：
- SSH 格式：`git@github.com:你的用户名/qq-bot.git`
- HTTPS 格式：`https://github.com/你的用户名/qq-bot.git`

---

## 5. 初始化本地仓库

打开命令行，进入项目目录：

```bash
cd D:\桌面\bot
```

初始化 Git 仓库：

```bash
git init
```

这会创建一个 `.git` 隐藏文件夹。

---

## 6. 创建 .gitignore

创建 `.gitignore` 文件，告诉 Git 忽略哪些文件：

```bash
# 在项目根目录创建 .gitignore 文件
```

`.gitignore` 内容：

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
*.egg-info/
dist/
build/

# 数据库文件（包含用户数据，不应上传）
sqline/*.db
*.db
*.db-shm
*.db-wal

# 敏感配置（包含密钥，绝对不能上传）
config.yml

# 生成的文件
qtp/
qtppng/

# IDE
.idea/
.vscode/
*.swp
*.swo

# 系统文件
.DS_Store
Thumbs.db

# 日志
*.log
logs/

# 测试文件
test_*.png
```

---

## 7. 提交代码

### 7.1 创建配置文件模板

由于 `config.yml` 被忽略，需要创建一个模板文件：

```bash
# 复制 config.yml 为 config.yml.example
copy config.yml config.yml.example
```

然后编辑 `config.yml.example`，把敏感信息替换：

```yaml
zhipu:
  api_key: "your_api_key_here"  # 替换为你的 API Key

onebot:
  token: "your_token_here"      # 替换为你的 Token

auth:
  secret_key: "change_this_in_production"
```

### 7.2 添加文件到暂存区

```bash
# 查看状态
git status

# 添加所有文件
git add .

# 或者逐个添加
git add README.md
git add start.py
git add requirements.txt
git add config.yml.example
git add py/
git add html/
git add resource/
git add md/
git add text/
```

### 7.3 检查将要提交的文件

```bash
git status
```

确保没有敏感文件（config.yml、*.db 等）。

### 7.4 提交

```bash
git commit -m "Initial commit: FastAPI QQ Bot"
```

---

## 8. 推送到 GitHub

### 8.1 添加远程仓库

```bash
# 使用 SSH（推荐）
git remote add origin git@github.com:你的用户名/qq-bot.git

# 或使用 HTTPS
git remote add origin https://github.com/你的用户名/qq-bot.git
```

### 8.2 推送代码

```bash
# 首次推送，设置上游分支
git push -u origin main
```

如果报错说分支名是 `master` 而不是 `main`：

```bash
# 重命名分支
git branch -M main

# 再次推送
git push -u origin main
```

### 8.3 验证

打开 GitHub 仓库页面，刷新应该能看到你的代码了！

---

## 9. 后续维护

### 日常更新流程

```bash
# 1. 查看修改了什么
git status

# 2. 查看具体改动
git diff

# 3. 添加修改的文件
git add .

# 4. 提交
git commit -m "描述这次改动"

# 5. 推送
git push
```

### 提交信息规范

建议使用规范的提交信息：

```bash
# 新功能
git commit -m "feat: 添加签到功能"

# 修复 bug
git commit -m "fix: 修复复读概率计算错误"

# 文档更新
git commit -m "docs: 更新 README"

# 重构
git commit -m "refactor: 重构插件加载逻辑"

# 配置变更
git commit -m "chore: 更新依赖版本"
```

### 分支管理

```bash
# 创建新分支（开发新功能时）
git checkout -b feature/new-plugin

# 切换分支
git checkout main

# 合并分支
git merge feature/new-plugin

# 删除分支
git branch -d feature/new-plugin
```

### 拉取远程更新

```bash
# 拉取远程更新
git pull
```

---

## 10. 常见问题

### Q1: 推送时提示需要用户名密码

如果配置了 SSH 还要密码，可能用了 HTTPS 地址：

```bash
# 查看当前远程地址
git remote -v

# 修改为 SSH 地址
git remote set-url origin git@github.com:你的用户名/qq-bot.git
```

### Q2: 不小心提交了敏感文件

**方法1：从历史中完全删除（推荐）**

```bash
# 安装 git-filter-repo（只需一次）
pip install git-filter-repo

# 从所有历史中删除文件
git filter-repo --invert-paths --path config.yml

# 强制推送
git push --force
```

**方法2：简单删除（文件还在历史中）**

```bash
git rm --cached config.yml
git commit -m "Remove sensitive file"
git push
```

⚠️ 如果密钥已泄露，必须立即更换密钥！

### Q3: 推送被拒绝

```bash
# 先拉取远程更新
git pull --rebase

# 再推送
git push
```

### Q4: 想撤销上一次提交

```bash
# 撤销提交但保留修改
git reset --soft HEAD~1

# 撤销提交和修改
git reset --hard HEAD~1
```

### Q5: 想查看提交历史

```bash
# 简洁模式
git log --oneline

# 详细模式
git log

# 图形化
git log --oneline --graph
```

---

## 📝 完整操作示例

从零开始的完整流程：

```bash
# 1. 进入项目目录
cd D:\桌面\bot

# 2. 初始化仓库
git init

# 3. 创建 .gitignore（手动创建或使用命令）
# 确保包含 config.yml、*.db 等

# 4. 创建配置模板
copy config.yml config.yml.example
# 编辑 config.yml.example，删除敏感信息

# 5. 添加所有文件
git add .

# 6. 检查状态，确保没有敏感文件
git status

# 7. 首次提交
git commit -m "Initial commit: FastAPI QQ Bot"

# 8. 添加远程仓库
git remote add origin git@github.com:你的用户名/qq-bot.git

# 9. 推送
git branch -M main
git push -u origin main
```

恭喜！你的项目已经上传到 GitHub 了！🎉
