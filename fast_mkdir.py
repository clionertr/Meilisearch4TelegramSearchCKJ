import pathlib


def create_project_structure(project_name):
    # 创建主目录
    base_path = pathlib.Path(project_name)

    # 创建目录结构
    directories = [
        'docs',
        'src',
        'src/config',
        'src/utils',
        'src/models',
        'src/api',
        'tests'
    ]

    # 创建需要的空文件
    files = [
        'src/__init__.py',
        'src/main.py',
        'requirements.txt',
        'setup.py',
        'README.md',
        'LICENSE'
    ]

    # 创建目录
    for dir_path in directories:
        path = base_path / dir_path
        path.mkdir(parents=True, exist_ok=True)
        # 在每个Python包目录下创建__init__.py
        if dir_path.startswith('src'):
            (path / '__init__.py').touch()

    # 创建文件
    for file_path in files:
        path = base_path / file_path
        path.touch()

    print(f"Project structure created for {project_name}")


# 使用示例
if __name__ == "__main__":
    create_project_structure("Meilisearch4TelegramSearchCKJ")
