[根目录](../CLAUDE.md) > **tests**

# Tests 模块

> 单元测试与集成测试模块，确保代码质量和功能正确性

---

## 模块职责

提供全面的测试覆盖，包括：
- **单元测试**: MeiliSearch 客户端、工具函数、权限检查
- **API 测试**: FastAPI 端点测试（使用 TestClient）
- **Mock 测试**: Telegram 客户端、异步操作
- **异常测试**: 网络错误、超时、API 错误
- **重试机制测试**: tenacity 重试验证

---

## 文件清单

### 测试文件

| 文件 | 职责 | 测试类 |
|------|------|--------|
| `conftest.py` | pytest 配置和公共 fixtures | - |
| `test_api.py` | FastAPI 端点测试 | 7 个测试类 (20+ 测试) |
| `test_api_integration.py` | API 集成测试 | - |
| `test_meilisearch_handler.py` | MeiliSearch 客户端测试 | 4 个测试类 |
| `test_utils.py` | 工具函数测试 | 3 个测试类 |
| `test_logger.py` | 日志配置测试 | - |
| `test_tg_client.py` | Telegram 客户端测试 (集成) | - |
| `test_configparser.py` | 配置解析测试 | - |
| `test_meilisearch.py` | MeiliSearch 集成测试 | - |

### 工具脚本

| 文件 | 用途 |
|------|------|
| `get_session_file.py` | 获取 Telethon 会话文件 |
| `get_str_session.py` | 获取 Telethon 会话字符串 |
| `delete_all_contain_keyword.py` | 删除包含关键词的文档 |

---

## 测试覆盖

### conftest.py - Fixtures

```python
@pytest.fixture
def mock_meilisearch_client():
    """Mock MeiliSearch Client"""

@pytest.fixture
def mock_index():
    """Mock MeiliSearch Index"""

@pytest.fixture
def sample_documents():
    """示例文档数据（用于测试）"""

@pytest.fixture
def mock_logger():
    """Mock Logger"""

@pytest.fixture
def mock_telegram_client():
    """Mock Telegram Client"""

@pytest.fixture
def mock_app_state():
    """Mock AppState（API 测试用）"""

@pytest.fixture
def test_client():
    """FastAPI TestClient（带 Mock 状态）"""
```

### test_api.py

#### TestHealthCheck
- [x] 测试健康检查端点
- [x] 测试根端点

#### TestSearchAPI
- [x] 测试消息搜索
- [x] 测试带过滤条件的搜索
- [x] 测试搜索统计

#### TestConfigAPI
- [x] 测试获取配置
- [x] 测试添加白名单
- [x] 测试添加黑名单

#### TestStatusAPI
- [x] 测试获取系统状态
- [x] 测试获取对话列表
- [x] 测试获取下载进度

#### TestControlAPI
- [x] 测试获取客户端状态
- [x] 测试停止未运行的客户端

#### TestModels
- [x] 测试 ApiResponse 模型
- [x] 测试 ErrorResponse 模型
- [x] 测试 SearchRequest 验证
- [x] 测试 MessageModel

#### TestProgressRegistry
- [x] 测试更新进度
- [x] 测试订阅和发布
- [x] 测试完成进度

### test_meilisearch_handler.py

#### TestMeiliSearchClientInit
- [x] 测试成功初始化
- [x] 测试连接错误
- [x] 测试超时错误

#### TestMeiliSearchClientCRUD
- [x] 测试创建索引
- [x] 测试索引已存在情况
- [x] 测试添加文档
- [x] 测试添加空文档列表
- [x] 测试搜索
- [x] 测试空查询
- [x] 测试删除索引
- [x] 测试获取索引统计
- [x] 测试更新文档
- [x] 测试删除文档

#### TestMeiliSearchExceptionHandling
- [x] 测试添加文档时连接错误
- [x] 测试添加文档时超时错误
- [x] 测试添加文档时 API 错误
- [x] 测试搜索时连接错误

#### TestMeiliSearchAPIErrorDetails
- [x] 测试 API 错误包含状态码
- [x] 测试 API 错误不含状态码

### test_utils.py

#### TestIsAllowed
- [x] 空列表允许所有
- [x] 白名单模式只允许列表中的 ID
- [x] 黑名单模式阻止列表中的 ID
- [x] 白名单和黑名单都会被检查
- [x] None 白名单视为空
- [x] None 黑名单视为空
- [x] 负数 chat_id（群组 ID）
- [x] 单元素列表

#### TestSizeofFmt
- [x] 测试字节单位
- [x] 测试 KiB 单位
- [x] 测试 MiB 单位
- [x] 测试 GiB 单位
- [x] 测试 TiB 单位
- [x] 测试超大值（YiB）
- [x] 测试自定义后缀
- [x] 测试负数值
- [x] 测试浮点数输入
- [x] 测试精度

#### TestConfigValidation
- [x] 测试跳过验证的环境变量
- [x] 测试 ConfigurationError 异常类

---

## 运行测试

### 基本用法

```bash
# 运行所有测试
pytest tests/

# 运行特定文件
pytest tests/test_meilisearch_handler.py

# 运行 API 测试
pytest tests/test_api.py

# 运行特定测试类
pytest tests/test_utils.py::TestIsAllowed

# 运行特定测试方法
pytest tests/test_utils.py::TestIsAllowed::test_empty_lists_allows_all

# 显示详细输出
pytest tests/ -v

# 显示标准输出
pytest tests/ -s
```

### 覆盖率报告

```bash
# 生成覆盖率报告
pytest --cov=src/tg_search --cov-report=html tests/

# 查看覆盖率报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# 生成终端覆盖率报告
pytest --cov=src/tg_search --cov-report=term-missing tests/
```

### 并行运行

```bash
# 安装 pytest-xdist
uv add --dev pytest-xdist

# 并行运行测试（使用所有 CPU 核心）
pytest tests/ -n auto
```

---

## Mock 策略

### MeiliSearch Mock

```python
# conftest.py 中的 mock_meilisearch_client
with patch("meilisearch.Client") as mock_client_class:
    mock_client = MagicMock()
    mock_client.index.return_value = mock_index
    mock_client.create_index.return_value = MagicMock(task_uid=1)
    ...
```

### Telegram Mock

```python
# conftest.py 中的 mock_telegram_client
mock = AsyncMock()
mock.start = AsyncMock()
mock.disconnect = AsyncMock()
mock.iter_messages = AsyncMock(return_value=iter([]))
```

### API Mock

```python
# test_api.py 中的 test_client fixture
@pytest.fixture
def test_client(mock_app_state, mock_meili_client):
    with patch("tg_search.api.app.MeiliSearchClient", return_value=mock_meili_client):
        from tg_search.api.app import build_app
        app = build_app()
        with TestClient(app) as client:
            app.state.app_state.meili_client = mock_meili_client
            yield client
```

### 环境变量 Mock

```python
# conftest.py 顶部（在导入前设置）
os.environ["SKIP_CONFIG_VALIDATION"] = "true"
os.environ["ENABLE_TRACEMALLOC"] = "false"
os.environ.setdefault("APP_ID", "12345678")
os.environ.setdefault("APP_HASH", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6")
...
```

---

## 示例测试代码

### 测试 MeiliSearch 添加文档

```python
def test_add_documents(self, meili_client, sample_documents, mock_meilisearch_client):
    """测试添加文档"""
    meili_client.add_documents(sample_documents)
    mock_meilisearch_client.index.return_value.add_documents.assert_called_once_with(
        sample_documents
    )
```

### 测试异常处理

```python
def test_add_documents_connection_error(self, meili_client, sample_documents, mock_meilisearch_client):
    """测试添加文档时连接错误"""
    mock_meilisearch_client.index.return_value.add_documents.side_effect = ConnectionError("Connection lost")
    with pytest.raises(MeiliSearchConnectionError):
        meili_client.add_documents(sample_documents)
```

### 测试重试机制

```python
def test_add_documents_timeout_error(self, meili_client, sample_documents, mock_meilisearch_client):
    """测试添加文档时超时错误（tenacity 会重试 3 次后抛出）"""
    mock_meilisearch_client.index.return_value.add_documents.side_effect = requests.exceptions.Timeout("Timeout")
    with pytest.raises(MeiliSearchTimeoutError):
        meili_client.add_documents(sample_documents)
    # 验证重试次数
    assert mock_meilisearch_client.index.return_value.add_documents.call_count == 3
```

### 测试 API 端点

```python
class TestSearchAPI:
    def test_search_messages(self, test_client):
        """测试消息搜索"""
        response = test_client.get("/api/v1/search?q=hello")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_search_with_filters(self, test_client):
        """测试带过滤条件的搜索"""
        response = test_client.get(
            "/api/v1/search",
            params={
                "q": "test",
                "chat_type": "group",
                "limit": 10,
            },
        )
        assert response.status_code == 200
```

### 测试 ProgressRegistry

```python
class TestProgressRegistry:
    @pytest.mark.asyncio
    async def test_update_progress(self):
        """测试更新进度"""
        from tg_search.api.state import ProgressRegistry

        registry = ProgressRegistry()
        await registry.update_progress(
            dialog_id=123,
            dialog_title="Test Dialog",
            current=50,
            total=100,
        )

        progress = registry.get_progress(123)
        assert progress is not None
        assert progress.current == 50
        assert progress.percentage == 50.0
```

---

## 测试数据

### sample_documents

```python
[
    {
        "id": "123-1",
        "chat": {"id": 123, "type": "channel", "title": "Test Channel"},
        "date": "2024-01-01T12:00:00+08:00",
        "text": "Hello World",
        "from_user": {"id": 456, "username": "testuser"},
        "reactions": None,
        "reactions_scores": None,
        "text_len": 11,
    },
    {
        "id": "123-2",
        "chat": {"id": 123, "type": "channel", "title": "Test Channel"},
        "date": "2024-01-01T12:01:00+08:00",
        "text": "你好世界",
        "from_user": {"id": 456, "username": "testuser"},
        "reactions": {"!": 5},
        "reactions_scores": 5.0,
        "text_len": 4,
    },
]
```

---

## 工具脚本使用

### get_session_file.py

用于生成 Telethon 会话文件（交互式）。

```bash
python tests/get_session_file.py
# 按提示输入 API ID、Hash 和手机号
# 生成 session/user_bot_session.session
```

### get_str_session.py

用于生成 Telethon 会话字符串（用于环境变量）。

```bash
python tests/get_str_session.py
# 按提示输入信息
# 输出 SESSION_STRING 的值
```

### delete_all_contain_keyword.py

删除 MeiliSearch 中包含关键词的所有文档（危险操作）。

```bash
python tests/delete_all_contain_keyword.py
# 按提示输入关键词和确认
```

---

## 常见问题 (FAQ)

### Q1: 如何跳过慢速测试？

**A:**
```python
# 标记慢速测试
@pytest.mark.slow
def test_large_download():
    ...

# 跳过慢速测试
pytest tests/ -m "not slow"
```

### Q2: 如何调试失败的测试？

**A:**
```bash
# 使用 -v 显示详细信息
pytest tests/ -v

# 使用 -s 显示 print 输出
pytest tests/ -s

# 在第一个失败处停止
pytest tests/ -x

# 使用 pdb 调试器
pytest tests/ --pdb
```

### Q3: 如何测试异步函数？

**A:** 使用 `pytest-asyncio`（已在 pyproject.toml 中配置）：
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result == expected
```

### Q4: 为什么测试需要设置环境变量？

**A:** 因为配置模块（`config/settings.py`）在导入时会读取环境变量。`conftest.py` 在导入前设置了测试用的假值，避免配置验证失败。

### Q5: 如何添加新的测试？

**A:**
1. 在 `tests/` 目录下创建 `test_*.py` 文件
2. 定义测试类（`class TestXXX`）或测试函数（`def test_xxx()`）
3. 使用 fixtures（在 `conftest.py` 中定义）
4. 运行 `pytest tests/` 验证

### Q6: 如何测试 API 端点？

**A:** 使用 `test_client` fixture：
```python
def test_my_endpoint(self, test_client):
    response = test_client.get("/api/v1/my-endpoint")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
```

---

## 变更记录 (Changelog)

### 2026-02-06
- 更新文档，添加 API 测试说明
- 新增 test_api.py 测试覆盖列表
- 新增 mock_app_state 和 test_client fixtures
- 添加 ProgressRegistry 测试说明

### 2026-02-05
- 创建测试模块文档
- 记录所有测试文件和覆盖范围
- 添加工具脚本使用说明
- 补充测试策略和 Mock 方法
