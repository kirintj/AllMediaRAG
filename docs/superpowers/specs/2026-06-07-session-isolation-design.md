# 会话隔离设计文档

**日期**: 2026-06-07
**状态**: 已批准

---

## 背景

当前 RAG 引擎在内存中维护全局共享的 `conversation_history` 列表，所有用户对话上下文互相污染。对话文件按扁平 `conv_id` 存储，无用户归属，任何已认证用户可读取/删除他人的对话。

## 方案

**前端持有上下文，后端无状态化（方案 D）**：让前端每次请求时携带最近 N 轮对话上下文，后端 RAG Engine 不再维护任何用户状态。对话持久化按用户子目录隔离。

---

## 1. API 契约变更

### `POST /api/chat` 请求体

```python
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    mode: Literal["rag", "direct"] = "rag"
    conversation_id: Optional[str] = Field(None, max_length=64, pattern=r"^[a-zA-Z0-9_-]*$")
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
```

- `history`: 前端传最近 N 轮上下文，上限 20 条消息（10 轮对话）
- 响应结构不变，SSE 流式输出保持原格式

### 对话管理端点

- `GET /conversations` — 仅返回当前用户的对话（路径限定为 `conversations/{username}/`）
- `GET /conversations/{conv_id}` — 归属校验，非本人对话返回 403
- `DELETE /conversations/{conv_id}` — 同上
- `save_conversation(conv_id, username, title, messages, mode)` — 新增 `username` 参数
- `DELETE /api/history` — 删除此端点（后端不再维护历史）

---

## 2. 后端引擎变更

### 删除

- `RAGEngine.conversation_history` 列表
- `RAGEngine.update_history()` 方法
- `RAGEngine.clear_history()` 方法

### 修改

- `build_prompt(query, contexts, history=None)` — 新增 `history` 参数，由调用方传入
- `chat.py` — 从 `body.history` 提取上下文透传给 `build_prompt`，不再调用 `update_history`
- `conversations.py` — 存储路径从 `conversations/{conv_id}.json` 改为 `conversations/{username}/{conv_id}.json`
- `_list_all()` → `_list_user(username)` — 只扫描当前用户目录
- `get_conversation()` / `delete_conversation()` — 路径必须落在 `conversations/{username}/` 下，否则 403

---

## 3. 前端变更

### `api/index.js`

- `chatStream` 签名新增 `history` 参数，序列化到请求体

### `stores/chat.js`

- 调用 `chatStream` 时从当前 `messages` 提取最近 10 轮作为 `history`
- 新增 `clearCurrentConversation()` — 纯前端清空，不调用后端

### UI

- 移除或替换依赖 `DELETE /api/history` 的按钮

---

## 4. 涉及文件

| 文件 | 变更类型 |
|------|---------|
| `backend/core/rag_engine.py` | 删除 history 相关属性和方法，修改 `build_prompt` 签名 |
| `backend/api/chat.py` | 适配新 ChatRequest，透传 history，移除 update_history 调用 |
| `backend/api/conversations.py` | 用户子目录存储，归属校验，移除 `_list_all` |
| `backend/main.py` | 移除 history 路由注册 |
| `frontend/src/api/index.js` | chatStream 增加 history 参数 |
| `frontend/src/stores/chat.js` | 提取 history 并传入，本地清空对话 |
| `tests/unit/test_full_pipeline.py` | 适配 build_prompt 新签名 |

---

## 5. 验收标准

1. 用户 A 的对话上下文不会出现在用户 B 的 RAG 检索结果中
2. `GET /conversations` 仅返回当前用户的对话
3. 用户 A 无法通过猜测 conv_id 访问用户 B 的对话（返回 403）
4. 现有 70 个单元测试全部通过
5. 新增 API 集成测试覆盖：跨用户隔离、history 透传、403 拒绝
