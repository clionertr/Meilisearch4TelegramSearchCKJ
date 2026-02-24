"""
端到端 API 集成测试（强保证版）

按逻辑顺序测试所有 API 端点：
  Phase 1: 基础连通性
  Phase 2: 配置管理
  Phase 3: 下载与入索引链路
  Phase 4: 搜索结果质量
  Phase 5: 客户端控制
  Phase 6: 错误处理

关键目标：
- 不依赖历史数据，不允许“空跑通过”
- 使用本次运行注入的 probe marker/keyword 做强校验
- 输出审查式日志（如：搜索结果格式审核✅️）
"""

import json
import time
from typing import Any

import httpx
import pytest

from tests.integration.config import DOWNLOAD_WAIT_TIMEOUT
from tests.integration.conftest import switchable

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

POLL_INTERVAL_SECONDS = 2


def _log(method: str, path: str, status: int, body: dict | None = None) -> None:
    """统一的测试日志输出"""
    print(f"\n  [{method} {path}] -> {status}")
    if body:
        print(f"  Response: {json.dumps(body, indent=2, ensure_ascii=False)[:500]}")


def _audit_ok(title: str, detail: str | None = None) -> None:
    """输出审查通过日志"""
    if detail:
        print(f"  {title}✅️ ({detail})")
    else:
        print(f"  {title}✅️")


def _assert_audit(condition: bool, title: str, detail: str) -> None:
    """断言并输出审查日志"""
    if condition:
        _audit_ok(title, detail)
        return
    print(f"  {title}❌ ({detail})")
    raise AssertionError(f"{title}: {detail}")


def _load_probe_context(test_group_info: dict | None) -> dict[str, Any]:
    """读取并校验本次运行探针上下文"""
    _assert_audit(test_group_info is not None, "测试群组上下文校验", "已加载 .test_groups.json")

    assert test_group_info is not None  # for type checker
    required = ("group_id", "group_title", "probe_marker", "probe_keyword", "probe_message_count")
    for key in required:
        _assert_audit(key in test_group_info, "测试上下文字段审核", f"字段存在: {key}")

    probe_count = int(test_group_info["probe_message_count"])
    _assert_audit(probe_count > 0, "探针消息数量审核", f"probe_message_count={probe_count}")
    return {
        "group_id": int(test_group_info["group_id"]),
        "group_title": str(test_group_info["group_title"]),
        "probe_marker": str(test_group_info["probe_marker"]),
        "probe_keyword": str(test_group_info["probe_keyword"]),
        "probe_message_count": probe_count,
    }


def _search_marker_hits(
    api_client: httpx.Client,
    marker: str,
    group_id: int,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """按 marker + chat_id 搜索命中"""
    try:
        r = api_client.get(
            "/api/v1/search",
            params={
                "q": marker,
                "chat_id": group_id,
                "limit": limit,
                "offset": 0,
            },
            timeout=8.0,
        )
    except (httpx.ReadTimeout, httpx.ConnectError) as exc:
        raise AssertionError(f"探针搜索超时或连接失败: {type(exc).__name__}: {exc}") from exc
    _log("GET", f"/api/v1/search?q={marker}&chat_id={group_id}", r.status_code, r.json())
    _assert_audit(r.status_code == 200, "探针搜索接口状态审核", f"status={r.status_code}")
    data = r.json()
    _assert_audit(data.get("success") is True, "探针搜索业务状态审核", "success=true")
    return data["data"]["hits"]


class TestPhase1Connectivity:
    """Phase 1: 基础连通性"""

    @switchable("health_check")
    def test_01_health_check(self, api_client: httpx.Client):
        """健康检查接口审核"""
        r = api_client.get("/health")
        _log("GET", "/health", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "健康检查状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("status") == "ok", "健康状态字段审核", "status=ok")
        _assert_audit("timestamp" in data, "健康检查时间戳审核", "包含 timestamp")

    @switchable("root_endpoint")
    def test_02_root_endpoint(self, api_client: httpx.Client):
        """根端点元信息审核"""
        r = api_client.get("/")
        _log("GET", "/", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "根端点状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("name") == "Telegram Search API", "服务名称审核", "name=Telegram Search API")
        _assert_audit("version" in data, "版本字段审核", "包含 version")

    @switchable("system_status")
    def test_03_system_status(self, api_client: httpx.Client):
        """系统状态接口审核"""
        r = api_client.get("/api/v1/status")
        _log("GET", "/api/v1/status", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "系统状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("success") is True, "系统状态成功标记审核", "success=true")
        status = data["data"]
        _assert_audit("uptime_seconds" in status, "系统运行时长字段审核", "包含 uptime_seconds")
        _assert_audit("meili_connected" in status, "Meili 连接字段审核", "包含 meili_connected")
        _assert_audit("version" in status, "系统版本字段审核", "包含 version")


class TestPhase2Config:
    """Phase 2: 配置管理"""

    @switchable("get_config")
    def test_04_get_config(self, api_client: httpx.Client):
        """配置读取接口审核"""
        r = api_client.get("/api/v1/config")
        _log("GET", "/api/v1/config", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "配置读取状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("success") is True, "配置读取成功标记审核", "success=true")

        config = data["data"]
        expected = (
            "white_list",
            "black_list",
            "owner_ids",
            "batch_msg_num",
            "results_per_page",
            "max_page",
            "search_cache",
            "cache_expire_seconds",
        )
        for key in expected:
            _assert_audit(key in config, "配置字段完整性审核", f"字段存在: {key}")

    @switchable("config_whitelist")
    def test_05_set_whitelist(self, api_client: httpx.Client, test_group_info: dict | None):
        """白名单更新接口审核"""
        ctx = _load_probe_context(test_group_info)
        test_ids = [ctx["group_id"]]

        r = api_client.post("/api/v1/config/whitelist", json={"ids": test_ids})
        _log("POST", "/api/v1/config/whitelist", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "白名单写入状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("success") is True, "白名单写入成功标记审核", "success=true")
        updated_list = data["data"]["updated_list"]
        _assert_audit(ctx["group_id"] in updated_list, "白名单目标群组审核", f"group_id={ctx['group_id']}")

    @switchable("config_whitelist")
    def test_06_verify_whitelist(self, api_client: httpx.Client, test_group_info: dict | None):
        """白名单持久状态读取审核"""
        ctx = _load_probe_context(test_group_info)
        r = api_client.get("/api/v1/config")
        _log("GET", "/api/v1/config", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "白名单读取状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("success") is True, "白名单读取成功标记审核", "success=true")
        white_list = data["data"]["white_list"]
        _assert_audit(ctx["group_id"] in white_list, "白名单生效审核", f"group_id={ctx['group_id']}")

    @switchable("config_blacklist")
    def test_07_set_blacklist(self, api_client: httpx.Client):
        """黑名单更新接口审核"""
        blacklist_id = 8888888
        r = api_client.post("/api/v1/config/blacklist", json={"ids": [blacklist_id]})
        _log("POST", "/api/v1/config/blacklist", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "黑名单写入状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("success") is True, "黑名单写入成功标记审核", "success=true")
        _assert_audit(blacklist_id in data["data"]["updated_list"], "黑名单目标 ID 审核", f"id={blacklist_id}")


class TestPhase3Download:
    """Phase 3: 下载与入索引链路"""

    @switchable("download_history")
    def test_08_start_download(self, api_client: httpx.Client):
        """下载任务启动审核"""
        r = api_client.post("/api/v1/client/start")
        _log("POST", "/api/v1/client/start", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "下载启动状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("success") is True, "下载启动成功标记审核", "success=true")
        _assert_audit(
            data["data"]["status"] in ("started", "already_running"),
            "下载任务状态审核",
            f"status={data['data']['status']}",
        )

    @switchable("download_history")
    def test_09_wait_for_probe_indexed(self, api_client: httpx.Client, test_group_info: dict | None):
        """探针消息入索引链路审核"""
        ctx = _load_probe_context(test_group_info)
        marker = ctx["probe_marker"]
        group_id = ctx["group_id"]

        deadline = time.time() + DOWNLOAD_WAIT_TIMEOUT
        matched_hits: list[dict[str, Any]] = []

        print(f"  Waiting probe indexing: marker={marker}, timeout={DOWNLOAD_WAIT_TIMEOUT}s")
        while time.time() < deadline:
            hits = _search_marker_hits(api_client, marker, group_id, limit=100)
            matched_hits = [h for h in hits if marker in (h.get("text") or "")]
            if matched_hits:
                break
            time.sleep(POLL_INTERVAL_SECONDS)

        _assert_audit(bool(matched_hits), "探针消息入索引审核", f"marker={marker}, hits={len(matched_hits)}")

        for hit in matched_hits:
            chat = hit.get("chat") or {}
            _assert_audit(chat.get("id") == group_id, "按 chat_id 过滤审核", f"chat.id={chat.get('id')}")

        _audit_ok("下载链路触发审核")

    @switchable("download_history")
    def test_10_verify_probe_count(self, api_client: httpx.Client, test_group_info: dict | None):
        """探针消息数量与索引统计审核"""
        ctx = _load_probe_context(test_group_info)
        marker = ctx["probe_marker"]
        group_id = ctx["group_id"]
        expected_count = ctx["probe_message_count"]

        hits = _search_marker_hits(api_client, marker, group_id, limit=100)
        marker_hits = [h for h in hits if marker in (h.get("text") or "")]
        _assert_audit(
            len(marker_hits) >= expected_count,
            "探针消息数量审核",
            f"expected>={expected_count}, actual={len(marker_hits)}",
        )

        r = api_client.get("/api/v1/search/stats")
        _log("GET", "/api/v1/search/stats", r.status_code, r.json())
        _assert_audit(r.status_code == 200, "索引统计状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("success") is True, "索引统计成功标记审核", "success=true")
        total = int(data["data"]["total_documents"])
        _assert_audit(total >= expected_count, "索引文档总量审核", f"total_documents={total}")


class TestPhase4Search:
    """Phase 4: 搜索结果质量"""

    @switchable("search_stats")
    def test_11_search_stats(self, api_client: httpx.Client, test_group_info: dict | None):
        """搜索统计结果审核"""
        ctx = _load_probe_context(test_group_info)
        expected_min = ctx["probe_message_count"]

        r = api_client.get("/api/v1/search/stats")
        _log("GET", "/api/v1/search/stats", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "搜索统计状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("success") is True, "搜索统计成功标记审核", "success=true")
        total_documents = int(data["data"]["total_documents"])
        _assert_audit(
            total_documents >= expected_min,
            "搜索统计文档量审核",
            f"expected>={expected_min}, actual={total_documents}",
        )
        _assert_audit("is_indexing" in data["data"], "搜索统计索引状态字段审核", "包含 is_indexing")

    @switchable("search_basic")
    def test_12_search_basic(self, api_client: httpx.Client, test_group_info: dict | None):
        """搜索结果格式审核"""
        ctx = _load_probe_context(test_group_info)

        r = api_client.get(
            "/api/v1/search",
            params={"q": ctx["probe_marker"], "chat_id": ctx["group_id"], "limit": 20},
        )
        _log("GET", f"/api/v1/search?q={ctx['probe_marker']}", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "基础搜索状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("success") is True, "基础搜索成功标记审核", "success=true")
        result = data["data"]
        hits = result["hits"]
        _assert_audit(len(hits) > 0, "基础搜索命中审核", f"hits={len(hits)}")

        required_keys = {
            "id",
            "chat",
            "date",
            "text",
            "from_user",
            "reactions",
            "reactions_scores",
            "text_len",
            "formatted",
            "formatted_text",
        }
        first = hits[0]
        _assert_audit(required_keys.issubset(set(first.keys())), "搜索结果字段完整性审核", "命中字段齐全")
        _assert_audit(result["query"] == ctx["probe_marker"], "搜索 query 回显审核", "query 与输入一致")
        _assert_audit("total_hits" in result, "搜索 total_hits 字段审核", "包含 total_hits")
        _assert_audit("processing_time_ms" in result, "搜索耗时字段审核", "包含 processing_time_ms")
        _audit_ok("搜索结果格式审核")

    @switchable("search_chinese")
    def test_13_search_chinese(self, api_client: httpx.Client, test_group_info: dict | None):
        """中文检索命中审核"""
        ctx = _load_probe_context(test_group_info)
        query = "中文探针"
        r = api_client.get("/api/v1/search", params={"q": query, "chat_id": ctx["group_id"], "limit": 20})
        _log("GET", f"/api/v1/search?q={query}", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "中文搜索状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("success") is True, "中文搜索成功标记审核", "success=true")
        hits = data["data"]["hits"]
        _assert_audit(len(hits) > 0, "中文搜索命中审核", f"hits={len(hits)}")
        _assert_audit(
            any("中文探针" in (h.get("text") or "") for h in hits),
            "中文文本匹配审核",
            "至少 1 条命中包含 '中文探针'",
        )

    @switchable("search_with_filters")
    def test_14_search_with_filters(self, api_client: httpx.Client, test_group_info: dict | None):
        """搜索过滤条件审核"""
        ctx = _load_probe_context(test_group_info)
        params = {
            "q": ctx["probe_marker"],
            "limit": 5,
            "offset": 0,
            "chat_type": "group",
            "chat_id": ctx["group_id"],
        }
        r = api_client.get("/api/v1/search", params=params)
        _log("GET", "/api/v1/search (filtered)", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "过滤搜索状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("success") is True, "过滤搜索成功标记审核", "success=true")
        result = data["data"]
        _assert_audit(result["limit"] == 5, "过滤搜索 limit 审核", "limit=5")
        _assert_audit(result["offset"] == 0, "过滤搜索 offset 审核", "offset=0")
        hits = result["hits"]
        _assert_audit(len(hits) > 0, "过滤搜索命中审核", f"hits={len(hits)}")
        _assert_audit(
            all((h.get("chat") or {}).get("id") == ctx["group_id"] for h in hits),
            "chat_id 过滤精确性审核",
            f"all chat.id == {ctx['group_id']}",
        )
        _assert_audit(
            all((h.get("chat") or {}).get("type") == "group" for h in hits),
            "chat_type 过滤精确性审核",
            "all chat.type == group",
        )

    @switchable("search_with_filters")
    def test_15_search_with_chat_id(self, api_client: httpx.Client, test_group_info: dict | None):
        """按 chat_id 过滤结果一致性审核"""
        ctx = _load_probe_context(test_group_info)
        params = {"q": ctx["probe_marker"], "chat_id": ctx["group_id"], "limit": 20}
        r = api_client.get("/api/v1/search", params=params)
        _log("GET", "/api/v1/search (chat_id)", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "chat_id 过滤搜索状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("success") is True, "chat_id 过滤搜索成功标记审核", "success=true")
        hits = data["data"]["hits"]
        _assert_audit(len(hits) > 0, "chat_id 过滤搜索命中审核", f"hits={len(hits)}")
        for hit in hits:
            chat = hit.get("chat") or {}
            _assert_audit(chat.get("id") == ctx["group_id"], "chat_id 结果一致性审核", f"chat.id={chat.get('id')}")

    @switchable("search_pagination")
    def test_16_search_pagination(self, api_client: httpx.Client, test_group_info: dict | None):
        """搜索分页正确性审核"""
        ctx = _load_probe_context(test_group_info)
        query = ctx["probe_marker"]

        r1 = api_client.get("/api/v1/search", params={"q": query, "chat_id": ctx["group_id"], "limit": 1, "offset": 0})
        _assert_audit(r1.status_code == 200, "分页第一页状态码审核", "HTTP 200")
        page1 = r1.json()["data"]
        _log("GET", "/api/v1/search (page 1)", r1.status_code, r1.json())

        r2 = api_client.get("/api/v1/search", params={"q": query, "chat_id": ctx["group_id"], "limit": 1, "offset": 1})
        _assert_audit(r2.status_code == 200, "分页第二页状态码审核", "HTTP 200")
        page2 = r2.json()["data"]
        _log("GET", "/api/v1/search (page 2)", r2.status_code, r2.json())

        _assert_audit(len(page1["hits"]) == 1, "分页第一页结果数审核", "hits=1")
        _assert_audit(len(page2["hits"]) == 1, "分页第二页结果数审核", "hits=1")

        id1 = page1["hits"][0]["id"]
        id2 = page2["hits"][0]["id"]
        _assert_audit(id1 != id2, "分页去重审核", f"id1={id1}, id2={id2}")

    @switchable("search_highlight")
    def test_17_search_highlight(self, api_client: httpx.Client, test_group_info: dict | None):
        """高亮字段输出审核"""
        ctx = _load_probe_context(test_group_info)
        query = ctx["probe_keyword"]
        r = api_client.get(
            "/api/v1/search",
            params={"q": query, "chat_id": ctx["group_id"], "limit": 20},
        )
        _log("GET", f"/api/v1/search?q={query}", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "高亮搜索状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("success") is True, "高亮搜索成功标记审核", "success=true")
        hits = data["data"]["hits"]
        _assert_audit(len(hits) > 0, "高亮搜索命中审核", f"hits={len(hits)}")

        highlight_hits = [h for h in hits if "<mark>" in (h.get("formatted_text") or "")]
        _assert_audit(
            len(highlight_hits) > 0,
            "高亮标签渲染审核",
            f"formatted_text with <mark>: {len(highlight_hits)}",
        )
        _audit_ok("搜索高亮格式审核")


class TestPhase5ClientControl:
    """Phase 5: 客户端控制"""

    @switchable("client_status")
    def test_18_client_status(self, api_client: httpx.Client):
        """客户端状态接口审核"""
        r = api_client.get("/api/v1/client/status")
        _log("GET", "/api/v1/client/status", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "客户端状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("success") is True, "客户端状态成功标记审核", "success=true")
        status = data["data"]
        _assert_audit(isinstance(status.get("is_running"), bool), "is_running 类型审核", "bool")
        _assert_audit(isinstance(status.get("api_only_mode"), bool), "api_only_mode 类型审核", "bool")

    @switchable("client_control")
    def test_19_stop_client(self, api_client: httpx.Client):
        """客户端停止接口审核"""
        r = api_client.post("/api/v1/client/stop")
        _log("POST", "/api/v1/client/stop", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "客户端停止状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("success") is True, "客户端停止成功标记审核", "success=true")
        _assert_audit(
            data["data"]["status"] in ("stopped", "already_stopped"),
            "客户端停止状态值审核",
            f"status={data['data']['status']}",
        )

    @switchable("client_control")
    def test_20_get_dialogs(self, api_client: httpx.Client, test_group_info: dict | None):
        """对话列表返回审核"""
        ctx = _load_probe_context(test_group_info)
        r = api_client.get("/api/v1/status/dialogs")
        _log("GET", "/api/v1/status/dialogs", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "对话列表状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("success") is True, "对话列表成功标记审核", "success=true")
        dialogs = data["data"]["dialogs"]
        _assert_audit(isinstance(dialogs, list), "对话列表类型审核", "list")

        group_id = ctx["group_id"]
        id_candidates = {group_id, -group_id}
        _assert_audit(
            any((d.get("id") in id_candidates) for d in dialogs),
            "测试群组出现在对话列表审核",
            f"candidate_ids={id_candidates}",
        )

    @switchable("client_control")
    def test_21_get_progress(self, api_client: httpx.Client, test_group_info: dict | None):
        """下载进度返回审核"""
        ctx = _load_probe_context(test_group_info)
        r = api_client.get("/api/v1/status/progress")
        _log("GET", "/api/v1/status/progress", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "下载进度状态码审核", "HTTP 200")
        data = r.json()
        _assert_audit(data.get("success") is True, "下载进度成功标记审核", "success=true")
        progress = data["data"]["progress"]
        _assert_audit(isinstance(progress, dict), "下载进度数据结构审核", "dict")

        group_id = ctx["group_id"]
        key_candidates = {str(group_id), str(-group_id)}
        _assert_audit(
            any(k in progress for k in key_candidates),
            "测试群组进度记录审核",
            f"candidate_keys={key_candidates}",
        )


class TestPhase6ErrorHandling:
    """Phase 6: 错误处理"""

    @switchable("error_empty_query")
    def test_22_search_empty_query(self, api_client: httpx.Client):
        """空查询参数校验审核"""
        r = api_client.get("/api/v1/search", params={"q": ""})
        _log("GET", "/api/v1/search?q=", r.status_code, r.json())

        _assert_audit(r.status_code == 422, "空查询状态码审核", "HTTP 422")
        data = r.json()
        _assert_audit("detail" in data, "空查询错误详情审核", "包含 detail")

    @switchable("error_invalid_limit")
    def test_23_search_invalid_limit(self, api_client: httpx.Client):
        """limit 上限参数校验审核"""
        r = api_client.get("/api/v1/search", params={"q": "test", "limit": 200})
        _log("GET", "/api/v1/search?q=test&limit=200", r.status_code, r.json())

        _assert_audit(r.status_code == 422, "limit 超限状态码审核", "HTTP 422")
        data = r.json()
        _assert_audit("detail" in data, "limit 超限错误详情审核", "包含 detail")
