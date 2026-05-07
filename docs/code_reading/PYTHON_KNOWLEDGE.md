# Python 知识点整理（来自代码阅读中的疑问）

> 本文档记录在阅读 hz_bank_rag 项目代码时遇到的 Python 语法和概念问题。

---

## 1. getattr() —— 安全地获取对象属性

**出处**：`api/main.py` 第 80 行

```python
getattr(vector_store, "available", False)
```

**语法**：

```python
getattr(对象, "属性名", 默认值)
```

**含义**：从对象上取属性，如果属性不存在就返回默认值，不会报错。

**等价写法**：

```python
try:
    对象.available
except AttributeError:
    False
```

**本项目用途**：`vector_store` 可能是 `MilvusVectorStore`（有 `available` 属性）或 `InMemoryVectorStore`（没有这个属性），用 `getattr` 避免报错。

**类似函数**：

| 函数 | 作用 | 例子 |
|------|------|------|
| `getattr(obj, "name", default)` | 取属性 | `getattr(obj, "age", 0)` |
| `hasattr(obj, "name")` | 判断属性是否存在 | `hasattr(obj, "age")` → `True/False` |
| `setattr(obj, "name", value)` | 设置属性 | `setattr(obj, "age", 25)` |

---

## 2. 类型注解（Type Hints）—— `req: IngestRequest` 是什么

**出处**：`api/main.py` 第 100 行

```python
def ingest_document(kb_id: str, req: IngestRequest) -> dict:
```

**含义**：这是 Python 3.5+ 引入的**类型注解**，告诉开发者（和工具）参数应该是什么类型。

- `kb_id: str` — 参数应该是字符串
- `req: IngestRequest` — 参数应该是 IngestRequest 对象
- `-> dict` — 返回值应该是字典

**重要**：Python 本身**不强制执行**类型注解，传错类型不会报错。但 FastAPI 会利用它：
1. 自动把 JSON 请求体解析成 `IngestRequest` 对象
2. 自动校验字段类型
3. 自动生成 API 文档（`/docs` 页面）

**更多例子**：

```python
def greet(name: str, age: int = 18) -> str:
    return f"Hello, {name}! You are {age}."

# 类型注解不影响运行
greet(123, "wrong")  # Python 不报错，但类型检查工具会警告
```

---

## 3. URL 路径参数 —— `{kb_id}` 怎么传进来的

**出处**：`api/main.py` 第 99 行

```python
@app.post("/knowledge-bases/{kb_id}/documents")
def ingest_document(kb_id: str, req: IngestRequest) -> dict:
```

**含义**：`{kb_id}` 是 URL 路径的一部分，FastAPI 自动提取。

**用户调用时**：

```
POST /knowledge-bases/hz-bank-demo/documents
                ↑
            这就是 kb_id 的值 = "hz-bank-demo"
```

**FastAPI 区分参数来源的规则**：

| 参数特征 | 来源 | 例子 |
|----------|------|------|
| 参数名和 URL 路径中的 `{xxx}` 匹配 | 路径参数 | `kb_id` 从 URL 取 |
| 参数类型是 Pydantic BaseModel | 请求体（body） | `req: IngestRequest` 从 JSON body 取 |
| 用 `Query()` 标记 | 查询参数 | `?limit=20` 从 URL 查询字符串取 |
| 用 `Header()` 标记 | 请求头 | `Authorization: Bearer xxx` |

---

## 4. raise + HTTPException —— 抛出 HTTP 错误

**出处**：`api/main.py` 第 110~114 行

```python
raise HTTPException(status_code=400, detail=str(exc)) from exc
```

**拆解**：

| 部分 | 含义 |
|------|------|
| `raise` | 抛出异常，中断当前流程 |
| `HTTPException` | FastAPI 专用异常类 |
| `status_code=400` | HTTP 状态码（400 = 请求有误） |
| `detail=str(exc)` | 错误详情，返回给前端 |
| `from exc` | 保留原始异常链，方便调试 |

**常见 HTTP 状态码**：

| 状态码 | 含义 | 本项目用途 |
|--------|------|-----------|
| 200 | 成功 | 正常返回 |
| 400 | 请求有误 | 运行时错误 |
| 404 | 未找到 | 文件不存在 |
| 409 | 冲突 | 文档重复 |
| 500 | 服务器内部错误 | 未捕获的异常 |

**效果**：前端收到 JSON 响应：

```json
{"detail": "File not found: /path/to/file.pdf"}
```

---

## 5. yield + 生成器 —— 流式输出的原理

**出处**：`api/main.py` 第 177~183 行

```python
def event_generator():
    yield f"data: {json.dumps({'type': 'meta', 'payload': meta_info})}\n\n"
    for token in token_iter:
        yield f"data: {json.dumps({'type': 'token', 'payload': token})}\n\n"
    yield "data: {\"type\":\"done\"}\n\n"
```

**`yield` 是什么？**

`yield` 是 Python 的**生成器语法**。普通函数用 `return` 返回一个值就结束了，生成器用 `yield` 可以产出多个值，每次产出后暂停，下次调用时继续。

**对比**：

```python
# 普通函数
def get_numbers():
    return [1, 2, 3]  # 一次性返回所有

# 生成器
def get_numbers():
    yield 1    # 产出 1，暂停
    yield 2    # 产出 2，暂停
    yield 3    # 产出 3，结束
```

**使用方式**：

```python
for num in get_numbers():  # 每次循环取一个值
    print(num)
```

**本项目用途**：SSE（Server-Sent Events）流式输出。AI 每生成一个 token（字/词），就 `yield` 一条消息，前端逐字显示，体验像 ChatGPT 一样。

**SSE 协议格式**：

```
data: {"type": "meta", "payload": {...}}\n\n
data: {"type": "token", "payload": "你"}\n\n
data: {"type": "token", "payload": "好"}\n\n
data: {"type": "done"}\n\n
```

---

## 6. copy.deepcopy() —— 深拷贝 vs 浅拷贝

**出处**：`qa_service.py` 第 83 行

```python
result = copy.deepcopy(cached)
```

**问题**：Python 中字典是引用类型：

```python
a = {"name": "test"}
b = a           # b 和 a 指向同一个对象！
b["name"] = "changed"
print(a["name"])  # "changed" ← a 也被改了！
```

**深拷贝**：完全复制一份新的，和原来的互不影响。

```python
import copy

a = {"name": "test"}
b = copy.deepcopy(a)  # 完全独立的副本
b["name"] = "changed"
print(a["name"])  # "test" ← a 不受影响
```

**本项目用途**：从缓存取出结果后，修改 `result["cache_hit"] = True`，如果不深拷贝，缓存里的原始数据也会被改掉。

**浅拷贝 vs 深拷贝**：

| 方式 | 方法 | 嵌套对象 |
|------|------|----------|
| 浅拷贝 | `copy.copy(obj)` 或 `obj.copy()` | 嵌套对象仍是引用 |
| 深拷贝 | `copy.deepcopy(obj)` | 完全独立，包括嵌套对象 |

---

## 7. 三元表达式 —— `A if 条件 else B`

**出处**：`api/main.py` 第 44~55 行

```python
vector_store = (
    MilvusVectorStore(...)
    if settings.use_milvus
    else InMemoryVectorStore(settings.vector_dim)
)
```

**语法**：

```python
值A if 条件 else 值B
```

**等价于**：

```python
if 条件:
    result = 值A
else:
    result = 值B
```

**更多例子**：

```python
status = "成年" if age >= 18 else "未成年"
max_val = a if a > b else b
```

---

## 8. @staticmethod —— 静态方法

**出处**：`qa_service.py` 第 301 行、第 357 行等

```python
@staticmethod
def _citation_from_hit(hit) -> dict:
    ...
```

**含义**：静态方法是属于类但**不需要实例化**就能调用的方法，也不需要 `self` 参数。

**对比**：

```python
class MyClass:
    def instance_method(self):      # 实例方法，需要 self
        return "需要创建对象才能调用"

    @staticmethod
    def static_method():            # 静态方法，不需要 self
        return "直接用类名就能调用"

# 使用
obj = MyClass()
obj.instance_method()               # 通过对象调用
MyClass.static_method()             # 通过类名直接调用
```

**本项目用途**：`_citation_from_hit`、`_extract_strong_keywords` 等函数不依赖实例状态（不需要访问 `self.repo`、`self.cache` 等），所以声明为静态方法，语义更清晰。

---

## 9. list[tuple[str, float]] 等复杂类型注解

**出处**：`hybrid_retriever.py` 第 95 行

```python
def _normalize_scores(hits: list[tuple[str, float]]) -> dict[str, float]:
```

**含义**：

| 注解 | 含义 |
|------|------|
| `list[tuple[str, float]]` | 一个列表，每个元素是 `(字符串, 浮点数)` 元组 |
| `dict[str, float]` | 一个字典，key 是字符串，value 是浮点数 |
| `list[dict]` | 一个列表，每个元素是字典 |
| `str \| None` | 字符串或 None（Python 3.10+ 语法） |

**例子**：

```python
hits = [("chunk_001", 0.85), ("chunk_002", 0.72)]
# 类型是 list[tuple[str, float]]
```

---

## 10. defaultdict —— 带默认值的字典

**出处**：`hybrid_retriever.py` 第 48 行

```python
from collections import defaultdict
rank_map: dict[str, dict[str, float]] = defaultdict(dict)
```

**普通字典的问题**：

```python
d = {}
d["key"]["sub_key"] = 1.0  # KeyError! 因为 d["key"] 不存在
```

**defaultdict 自动创建默认值**：

```python
d = defaultdict(dict)  # 访问不存在的 key 时，自动创建一个空 dict
d["key"]["sub_key"] = 1.0  # 正常工作！
```

**常用形式**：

```python
from collections import defaultdict

d1 = defaultdict(int)      # 默认值是 0
d2 = defaultdict(list)     # 默认值是 []
d3 = defaultdict(dict)     # 默认值是 {}
d4 = defaultdict(lambda: "未知")  # 自定义默认值
```

---

## 11. ThreadPoolExecutor —— 多线程并行执行

**出处**：`hybrid_retriever.py` 第 36~43 行

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=2) as pool:
    sparse_future = pool.submit(self.bm25_store.search, ...)
    dense_future = pool.submit(self.vector_store.search, ...)
    sparse_hits = sparse_future.result()  # 等待结果
    dense_hits = dense_future.result()    # 等待结果
```

**含义**：同时执行两个任务（BM25 检索和向量检索），而不是一个做完再做另一个。

**对比**：

```python
# 串行（慢）
result1 = bm25.search(...)    # 花 100ms
result2 = vector.search(...)  # 花 100ms
# 总共 200ms

# 并行（快）
# 两个同时执行
# 总共约 100ms
```

**本项目用途**：BM25 检索和向量检索互不依赖，可以并行执行，减少用户等待时间。

---

## 12. @app.get / @app.post —— FastAPI 路由装饰器

**出处**：`api/main.py` 贯穿全文

```python
@app.get("/health")
def health() -> dict:
    ...

@app.post("/query")
def query(req: QueryRequest) -> dict:
    ...
```

**装饰器是什么？**

装饰器是一个函数，它接收一个函数作为参数，返回一个新函数。用 `@` 语法放在函数定义前面。

**等价写法**：

```python
def health() -> dict:
    ...

health = app.get("/health")(health)  # 装饰器的本质
```

**GET vs POST**：

| 方法 | 用途 | 参数位置 |
|------|------|----------|
| GET | 查询/获取数据 | 参数在 URL 里（`?key=value`） |
| POST | 提交/创建数据 | 参数在请求体（body）里 |
| PUT | 更新数据 | 参数在请求体里 |
| DELETE | 删除数据 | 参数在 URL 里 |

---

## 13. Pydantic BaseModel —— 数据校验模型

**出处**：`api/schemas.py`

```python
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    kb_id: str
    query: str
    top_k: int = 5
    fast_mode: bool = True
```

**作用**：

1. **自动类型校验**：传入 `top_k: "abc"` 会自动报错
2. **自动类型转换**：传入 `top_k: "5"` 会自动转成整数 5
3. **默认值**：不传 `fast_mode` 时默认为 `True`
4. **自动生成文档**：FastAPI 用它生成 `/docs` 页面的参数说明

**Field 的作用**：

```python
file_path: str = Field(..., description="文档路径")
#                        ↑ 必填（... 是 Ellipsis，表示必填）
top_k: int = Field(default=5, description="返回结果数量")
#                       ↑ 可选，默认 5
```

---

## 14. from exc —— 异常链

**出处**：`api/main.py` 第 110 行

```python
raise HTTPException(status_code=400, detail=str(exc)) from exc
```

**`from exc` 的作用**：保留原始异常的堆栈信息。

**调试时的效果**：

```
Traceback (most recent call last):
  ...
hz_bank_rag.storage.rag_repository.DuplicateDocumentError: 文档已存在

The above exception was the direct cause of the following exception:

  ...
fastapi.exceptions.HTTPException: 400: 文档已存在
```

没有 `from exc` 的话，只会显示后面的异常，看不到原始错误是什么。

---

## 15. Ellipsis (...) —— 三个点的含义

**出处**：`api/schemas.py` 第 11 行

```python
file_path: str = Field(..., description="文档路径")
```

**`...` 是什么？**

`...` 是 Python 的 `Ellipsis` 对象，是一个特殊的常量。在 Pydantic 的 `Field` 中，它表示**必填字段**。

**等价写法**：

```python
file_path: str = Field(..., description="文档路径")      # 必填
file_path: str = Field(description="文档路径")            # 也是必填（不传 default）
file_path: str = Field(default="auto", description="...") # 可选，默认 "auto"
```

---

## 16. lambda —— 匿名函数

**出处**：常见于排序等场景

```python
hits.sort(key=lambda item: item.score, reverse=True)
```

**lambda 是什么？**

lambda 是一种简写的函数，没有名字，只能写一行表达式。

**等价写法**：

```python
def get_score(item):
    return item.score

hits.sort(key=get_score, reverse=True)
```

**更多例子**：

```python
square = lambda x: x ** 2          # lambda 参数: 返回值
add = lambda a, b: a + b

numbers = [1, 3, 2]
sorted_numbers = sorted(numbers, key=lambda x: -x)  # [3, 2, 1]
```

---

## 17. @property —— 属性装饰器（补充）

虽然本项目没有大量使用，但值得了解：

```python
class Person:
    def __init__(self, name):
        self._name = name

    @property
    def name(self):          # 像属性一样访问，不需要加 ()
        return self._name

p = Person("Alice")
print(p.name)    # "Alice"，不需要写 p.name()
```

---

## 18. dict.get() —— 安全取字典值

**出处**：贯穿全文

```python
metadata.get("file_path", "")
```

**对比**：

```python
d = {"name": "test"}

d["age"]          # KeyError! 键不存在时报错
d.get("age")      # None，不报错
d.get("age", 0)   # 0，返回默认值
```

**本项目用途**：从 metadata 字典取值时，很多字段可能不存在，用 `get` 避免报错。

---

## 19. enumerate() —— 带索引的遍历

**出处**：`qa_service.py` 第 465 行

```python
context = "\n\n".join([f"[{idx + 1}] {hit.text}" for idx, hit in enumerate(hits)])
```

**对比**：

```python
# 不用 enumerate
idx = 0
for hit in hits:
    print(idx, hit.text)
    idx += 1

# 用 enumerate
for idx, hit in enumerate(hits):
    print(idx, hit.text)          # idx 自动递增
```

**指定起始值**：

```python
for idx, hit in enumerate(hits, start=1):  # 从 1 开始
    print(idx, hit.text)
```

---

## 20. f-string —— 格式化字符串

**出处**：贯穿全文

```python
f"data: {json.dumps({'type': 'meta', 'payload': meta_info}, ensure_ascii=False)}\n\n"
```

**语法**：`f"文本 {表达式} 文本"`

**对比**：

```python
name = "Alice"
age = 25

# f-string（推荐）
print(f"我叫{name}，今年{age}岁")

# format 方法
print("我叫{}，今年{}岁".format(name, age))

# % 格式化（老式）
print("我叫%s，今年%d岁" % (name, age))
```

---

## 21. dict | dict —— 字典合并（Python 3.9+）

```python
# Python 3.9+
merged = dict1 | dict2

# 旧版本
merged = {**dict1, **dict2}
```

---

## 22. walrus operator := —— 赋值表达式（Python 3.8+）

```python
# 传统写法
result = expensive_call()
if result > 0:
    print(result)

# walrus operator
if (result := expensive_call()) > 0:
    print(result)
```

本项目未使用，但值得了解。

---

## 总结：本项目用到的核心 Python 特性

| 特性 | 用途 | 出现频率 |
|------|------|----------|
| 类型注解 | FastAPI 参数校验和文档生成 | 极高 |
| Pydantic BaseModel | 请求/响应模型定义 | 高 |
| 装饰器 `@app.get/post` | 路由注册 | 高 |
| `yield` 生成器 | 流式输出 | 中 |
| `deepcopy` | 缓存隔离 | 低 |
| `getattr` | 安全取属性 | 低 |
| `defaultdict` | 带默认值的字典 | 低 |
| `ThreadPoolExecutor` | 并行检索 | 低 |
| `@staticmethod` | 无状态工具方法 | 中 |
| `raise ... from` | 异常链 | 低 |
| f-string | 字符串格式化 | 极高 |
| `lambda` | 排序 key | 低 |
| `dict.get()` | 安全取字典值 | 极高 |
| `enumerate()` | 带索引遍历 | 中 |
