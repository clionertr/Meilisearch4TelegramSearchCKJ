# 使用官方 Python 3.12 镜像作为基础
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 将当前目录下的所有文件复制到容器的 /app 目录
COPY . /app

# 安装项目（使用 pyproject.toml）
RUN pip install --no-cache-dir .

# 使用模块方式运行（支持 python -m tg_search）
CMD ["python", "-m", "tg_search"]
