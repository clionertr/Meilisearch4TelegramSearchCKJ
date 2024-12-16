# 使用官方 Python 3.12 镜像作为基础
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 将当前目录下的所有文件复制到容器的 /app 目录
COPY . /app

# 安装可编辑模式的包，注意这里可能需要先安装 setuptools
RUN pip install setuptools
RUN pip install -e .

# 安装项目依赖
RUN pip install -r requirements.txt

# 切换到工作目录
WORKDIR /app/Meilisearch4TelegramSearchCKJ/src


# 运行你的 main.py 脚本
CMD ["python", "main.py"]