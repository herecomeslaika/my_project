# Django 项目服务器部署文档

## 服务器信息

| 项目 | 值 |
|------|-----|
| 操作系统 | Ubuntu 22.04 |
| 公网 IP | 8.149.137.130 |
| 开放端口 | 80, 22 |
| root 密码 | <见私有记录> |
| 普通用户 | yyy（密码同 root） |
| Python 版本 | 3.10.12（3.9 不可用，已适配） |
| Nginx 版本 | 1.18.0 |
| Django 版本 | 5.2.8 |
| Gunicorn 版本 | 26.0.0 |
| GitHub 仓库 | https://github.com/herecomeslaika/my_project |

## 架构概览

```
客户端 → Nginx (80) → Unix Socket → Gunicorn → Django WSGI
                ↓
           /static → 文件系统直接伺服
```

- **Nginx**：监听 80 端口，静态文件直接由 alias 伺服，动态请求通过 Unix 套接字转发给 Gunicorn
- **Gunicorn**：通过 Systemd 守护，绑定 Unix 套接字 `/tmp/8.149.137.130.socket`，运行 Django WSGI 应用
- **Systemd**：管理 Gunicorn 进程，开机自启，崩溃自动重启

## 目录结构

```
/home/yyy/sites/8.149.137.130/
├── database/          # SQLite 数据库
│   └── db.sqlite3
├── source/            # 项目源码（git clone）
│   ├── mywebsite/     # Django 主项目
│   │   ├── mywebsite/ # 项目配置
│   │   │   ├── settings.py
│   │   │   ├── urls.py
│   │   │   └── wsgi.py
│   │   ├── lists/     # lists 应用
│   │   └── manage.py
│   ├── testproject/   # 测试项目
│   └── static/        # collectstatic 输出
├── static/            # Nginx 提供的静态文件
├── virtualenv/        # Python 虚拟环境
└── .secret_key        # 生产环境 SECRET_KEY
```

## 手动部署步骤

### 1. 服务器系统环境初始化

```bash
ssh root@8.149.137.130

useradd -m -d /home/yyy -s /bin/bash yyy
echo 'yyy:<见私有记录>' | chpasswd
usermod -aG sudo yyy

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y nginx
systemctl start nginx && systemctl enable nginx

DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv python3-dev git
```

### 2. 本地 Django 项目配置调整

**settings.py 关键修改：**

```python
ALLOWED_HOSTS = ['8.149.137.130']

INSTALLED_APPS = [
    # 'django.contrib.admin',
    'django.contrib.auth',
    ...
]

STATIC_ROOT = os.path.join(BASE_DIR, '../static/')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, '../database/db.sqlite3'),
    }
}
```

**requirements.txt：**

```
django==5.2.8
gunicorn
```

### 3. 服务器目录构建与代码拉取

```bash
ssh yyy@8.149.137.130
mkdir -p ~/sites/8.149.137.130/{database,source,static,virtualenv}
git clone https://github.com/herecomeslaika/my_project.git ~/sites/8.149.137.130/source
```

### 4. 虚拟环境与服务端数据库

```bash
python3 -m venv ~/sites/8.149.137.130/virtualenv
~/sites/8.149.137.130/virtualenv/bin/pip install -r ~/sites/8.149.137.130/source/mywebsite/requirements.txt

# 服务器端路径调整（多了一层 source/ 目录）
sed -i "s|os.path.join(BASE_DIR, '../database/db.sqlite3')|os.path.join(BASE_DIR, '../../database/db.sqlite3')|g" \
    ~/sites/8.149.137.130/source/mywebsite/mywebsite/settings.py
sed -i "s|os.path.join(BASE_DIR, '../static/')|os.path.join(BASE_DIR, '../../static/')|g" \
    ~/sites/8.149.137.130/source/mywebsite/mywebsite/settings.py

# 生产环境配置
sed -i 's/DEBUG = True/DEBUG = False/' ~/sites/8.149.137.130/source/mywebsite/mywebsite/settings.py

cd ~/sites/8.149.137.130/source/mywebsite
../../virtualenv/bin/python manage.py migrate --noinput
../../virtualenv/bin/python manage.py collectstatic --noinput
```

### 5. Nginx 配置（静态文件 + Unix 套接字代理）

```bash
sudo tee /etc/nginx/sites-available/8.149.137.130 << 'EOF'
server {
    listen 80;
    server_name 8.149.137.130;

    location /static {
        alias /home/yyy/sites/8.149.137.130/static;
    }

    location / {
        proxy_pass http://unix:/tmp/8.149.137.130.socket;
        proxy_set_header Host $host;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/8.149.137.130 /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

### 6. Systemd Gunicorn 服务

```bash
sudo tee /etc/systemd/system/gunicorn-8.149.137.130.service << 'EOF'
[Unit]
Description=Gunicorn server for 8.149.137.130

[Service]
Restart=on-failure
User=yyy
WorkingDirectory=/home/yyy/sites/8.149.137.130/source/mywebsite
ExecStart=/home/yyy/sites/8.149.137.130/virtualenv/bin/gunicorn \
    --bind unix:/tmp/8.149.137.130.socket \
    mywebsite.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable gunicorn-8.149.137.130
sudo systemctl start gunicorn-8.149.137.130
```

## 自动化部署（Fabric）

### 部署工具文件结构

```
deploy_tools/
├── nginx.template.conf              # Nginx 配置模板（SITENAME 占位符）
├── gunicorn-systemd.template.service # Systemd 服务模板（SITENAME 占位符）
└── fabfile.py                       # Fabric 自动部署脚本
```

### 使用方法

```bash
# 安装 fabric3
pip install fabric3

# 完整部署（首次或更新）
cd deploy_tools
fab deploy

# 仅更新 Nginx 配置
fab nginx_config

# 仅更新 Gunicorn 服务配置
fab gunicorn_config
```

### fabfile.py 功能清单

| 函数 | 功能 |
|------|------|
| `deploy` | 完整部署流程 |
| `_create_directory_structure` | 创建 database/source/static/virtualenv 目录 |
| `_pull_source` | git clone 或 git fetch + reset --hard |
| `_update_settings` | 设置 DEBUG=False、ALLOWED_HOSTS、SECRET_KEY、路径修正 |
| `_update_virtualenv` | 创建虚拟环境并安装依赖 |
| `_collectstatic` | 收集静态文件 |
| `_migrate` | 执行数据库迁移 |
| `_restart_gunicorn` | 重启 Gunicorn 服务 |
| `nginx_config` | 从模板部署 Nginx 配置 |
| `gunicorn_config` | 从模板部署 Systemd 服务 |

### SECRET_KEY 管理

生产环境的 SECRET_KEY 存储在 `/home/yyy/sites/8.149.137.130/.secret_key` 文件中，首次部署时自动生成。settings.py 通过读取该文件获取密钥，避免将密钥提交到代码仓库。

## 部署经验与踩坑记录

### 1. SSH 密码含特殊字符
root 密码末尾包含逗号（`525jihaoyangZPU,`），在脚本中传递时容易遗漏。Windows 环境下无法直接用 `ssh` 传递密码，需使用 `paramiko` 库。

### 2. Python 3.9 不可用
Ubuntu 22.04 默认 Python 为 3.10，`apt-cache` 中无 python3.9 包。deadsnakes PPA 在阿里云镜像源下可能不可用。直接使用系统自带 Python 3.10 即可，Django 5.2.8 完全兼容。

### 3. Django 版本兼容性
原需求指定 `django==2.1.7`，但该版本不支持 Python 3.10。项目实际由 Django 5.2.8 生成，应使用 `django==5.2.8`。

### 4. 服务器端路径差异
本地项目结构与服务器不同：
- **本地**：`mywebsite/` 与 `database/`、`static/` 同级，`../database/` 正确
- **服务器**：代码在 `source/mywebsite/`，多了一层 `source/`，需改为 `../../database/`

这是部署中最容易出错的地方。fabfile.py 中的 `_update_settings` 函数已自动处理此问题。

### 5. Git 嵌套仓库问题
`mywebsite/` 和 `testproject/` 内部有各自的 `.git` 目录，直接 `git add` 会被识别为 submodule。需先删除嵌套的 `.git` 目录。

### 6. GitHub 私有仓库克隆
私有仓库在服务器上 `git clone` 需要认证。解决方案：
- 将仓库设为 public：`gh repo edit --visibility public --accept-visibility-change-consequences`
- 或使用 Personal Access Token：`git clone https://token@github.com/user/repo.git`

### 7. paramiko 超时问题
`pip install` 等长时间命令会导致 paramiko 连接超时。解决方法：
- 增大 `timeout` 参数（pip install 建议 300-600 秒）
- 调用 `stdout.channel.settimeout()` 设置通道超时
- 将大任务拆分为小步骤分别执行

### 8. Nginx alias 末尾斜杠
`location /static` 使用 `alias` 时，如果 location 路径末尾无斜杠，alias 路径末尾也不应有斜杠，否则路径拼接会出错。

### 9. Unix 套接字 vs TCP 端口
Unix 套接字比 TCP localhost 更高效（省去网络协议栈开销），但需注意：
- 套接字文件位于 `/tmp/`，系统重启后会被清理，Gunicorn 需通过 Systemd 自动重启重建
- Nginx 的 `proxy_pass` 写法为 `http://unix:/path/to/socket`

### 10. Systemd WorkingDirectory
`WorkingDirectory` 必须指向 `manage.py` 所在目录，否则 Django 找不到项目配置。

## 常用运维命令

```bash
# SSH 登录
ssh yyy@8.149.137.130

# Gunicorn 服务管理
sudo systemctl status gunicorn-8.149.137.130
sudo systemctl restart gunicorn-8.149.137.130
sudo systemctl stop gunicorn-8.149.137.130
sudo systemctl start gunicorn-8.149.137.130
journalctl -u gunicorn-8.149.137.130 -f   # 查看实时日志

# Nginx 管理
sudo systemctl status nginx
sudo systemctl reload nginx
sudo nginx -t                              # 测试配置
sudo tail -f /var/log/nginx/error.log      # 错误日志
sudo tail -f /var/log/nginx/access.log     # 访问日志

# 更新代码后手动重新部署
cd ~/sites/8.149.137.130/source && git pull
cd mywebsite
../../virtualenv/bin/pip install -r requirements.txt
../../virtualenv/bin/python manage.py migrate --noinput
../../virtualenv/bin/python manage.py collectstatic --noinput
sudo systemctl restart gunicorn-8.149.137.130

# 使用 Fabric 自动部署
cd deploy_tools && fab deploy
```
