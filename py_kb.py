#!/usr/bin/env python3
"""
================================================================================
  py_kb.py  —  项目全量 Python 知识点汇总（可执行示例）
================================================================================

  本文件将 hz_bank_rag 项目中出现的所有 Python 知识点，按"搭建一个迷你银行
  知识库问答系统"的主线串联起来，确保代码可直接运行（python py_kb.py）。

  学习路线图（按知识点层级递进）：
    Part 1 : 基础语法 — 类型标注、字符串、控制流、异常处理、内置函数
    Part 2 : 数据结构 — 列表/字典/集合/元组、推导式、排序、解包
    Part 3 : 函数进阶 — 闭包、lambda、装饰器、生成器、上下文管理器
    Part 4 : 面向对象 — 类、继承、抽象基类、静态方法、数据类
    Part 5 : 模块与库 — pathlib、json、re、hashlib、datetime、threading
    Part 6 : 设计模式 — 缓存（LRU/TTL）、单例、依赖注入、策略模式
    Part 7 : 综合实战 — 迷你 RAG 问答系统（串联所有知识点）

  使用说明：
    python py_kb.py              # 运行所有示例
    每个 Part 也可以独立阅读学习
================================================================================
"""

# --- 知识点 1.1: from __future__ import annotations ---
# 作用：让所有类型标注变成"惰性求值"（PEP 604/563），
#       允许用 | 做联合类型、用类名做前向引用而不必先定义类。
# 频次：41 个文件都在用
# 注意：必须放在文件最开头（docstring 之后、任何其他代码之前）！
from __future__ import annotations


# ================================================================================
# Part 1: 基础语法 — 类型标注、字符串、控制流、异常处理、内置函数
# ================================================================================
# 频次统计（来自项目 48 个 .py 文件）：
#   类型标注 (Type Hints)           — 41 次，几乎每个文件都在用
#   f-strings 格式化字符串          — 30 次
#   异常处理 (try/except)           — 26 次
#   len() 内置函数                  — 25 次
#   min() / max() 内置函数          — 18 次
#   isinstance() 类型检查           — 18 次
#   round() 内置函数                — 11 次
#   any() / all() 内置函数          — 11 次
#   range() 内置函数                — 10 次
#   enumerate() 内置函数            — 15 次
#   条件表达式 (三元运算符)          — 14 次
#   类型转换 int()/float()/str()/bool() — 13 次
# ================================================================================

print("=" * 70)
print("Part 1: 基础语法")
print("=" * 70)


# --- 知识点 1.2: 类型标注 (Type Hints) ---
# Python 是动态语言，但标注类型可以让 IDE 自动补全、让 mypy 做静态检查。
# 项目中使用 str | None、list[str]、dict[str, Any]、tuple[str, float] 等。
from typing import Any, Iterable, Iterator, Callable, Literal, Final

# 基础类型标注
user_name: str = "张三"                     # 字符串
user_age: int = 30                          # 整数
balance: float = 15280.55                   # 浮点数
is_vip: bool = True                         # 布尔值

# 容器类型标注（Python 3.10+ 可以用 list[X] 代替 List[X]）
question_list: list[str] = ["转账限额是多少？", "如何开通网银？"]
score_map: dict[str, float] = {"转账限额是多少？": 0.92, "如何开通网银？": 0.85}
embedding_tuple: tuple[str, float] = ("转账限额", 0.95)
# 可选类型：可以是 str 也可以是 None
maybe_answer: str | None = None

print("【类型标注示例】")
print(f"  用户名: {user_name}, 年龄: {user_age}, 余额: {balance}, VIP: {is_vip}")
print(f"  问题列表: {question_list}")
print(f"  得分映射: {score_map}")
print(f"  嵌入元组: {embedding_tuple}")
print(f"  可选答案: {maybe_answer}")


# --- 知识点 1.3: f-strings 格式化字符串 ---
# Python 3.6+ 引入，在项目中大量使用（30 次以上）
# 支持：内嵌表达式、格式说明符、调试模式 f"{var=}"
query: str = "转账限额"
top_k: int = 5
score: float = 0.8732

print("\n【f-strings 示例】")
print(f"  查询: {query}, 返回条数: {top_k}")
print(f"  得分保留两位小数: {score:.2f}")           # 格式说明符 :.2f
print(f"  调试模式: {query=}, {top_k=}")            # f"{var=}" 打印变量名和值


# --- 知识点 1.4: 条件表达式（三元运算符）---
# Python 中没有 ? : 三元运算符，用 x if condition else y
original_text: str | None = "  银行转账  "
# 如果 original_text 不为 None 就 strip，否则给默认文本
cleaned: str = original_text.strip() if original_text else "默认文本"
print(f"\n【条件表达式】清理后: '{cleaned}'")


# --- 知识点 1.5: 异常处理 (try/except) ---
# 项目中 26 个文件使用，是最常见的防御性编程手段。
# 还用了 try/finally（资源清理）和 from exc（异常链）
def safe_divide(a: float, b: float) -> float | None:
    """安全除法：捕获 ZeroDivisionError 和 TypeError"""
    try:
        result = a / b
    except ZeroDivisionError:
        print("    错误：除数不能为零！")
        return None
    except TypeError:
        print("    错误：传入的类型不正确！")
        return None
    else:
        print(f"    计算成功: {a} / {b} = {result}")
        return result
    finally:
        # finally 无论是否异常都会执行，常用于释放资源
        print("    [finally] 本次除法调用结束")

print("\n【异常处理示例】")
safe_divide(10, 2)
safe_divide(10, 0)

# 异常链：from exc 保留原始异常上下文
try:
    data = '{"name": "张三"'
    import json
    json.loads(data)
except json.JSONDecodeError as exc:
    # raise 新异常 from 旧异常，保留调试信息
    try:
        raise ValueError(f"配置文件格式错误: {exc}") from exc
    except ValueError as ve:
        print(f"    异常链示例: {ve}")


# --- 知识点 1.6: 内置函数总览 ---
# 项目中高频使用的内置函数
numbers: list[int] = [85, 92, 78, 96, 88, 73, 95]

print("\n【内置函数示例】")
print(f"  原始数据: {numbers}")
print(f"  len() 长度: {len(numbers)}")                          # 25 次
print(f"  min() 最小值: {min(numbers)}, max() 最大值: {max(numbers)}")  # 18 次
print(f"  round(3.14159, 2) 四舍五入: {round(3.14159, 2)}")    # 11 次
print(f"  any() 是否有 >=95 的: {any(n >= 95 for n in numbers)}")   # 11 次
print(f"  all() 是否全部 >=60: {all(n >= 60 for n in numbers)}")    # 11 次
print(f"  sum() 求和: {sum(numbers)}")
print(f"  sorted() 升序排序: {sorted(numbers)}")
print(f"  sorted() 降序排序: {sorted(numbers, reverse=True)}")
print(f"  range(5) 生成序列: {list(range(5))}")               # 10 次

# enumerate: 同时获取索引和值（项目中 15 次）
print(f"  enumerate() 带索引遍历:")
for idx, score_val in enumerate(numbers[:3]):
    print(f"    第 {idx} 条: {score_val}")

# isinstance: 运行时类型检查（项目中 18 次）
print(f"  isinstance(42, int): {isinstance(42, int)}")
print(f"  isinstance('hello', str): {isinstance('hello', str)}")
print(f"  isinstance(3.14, (int, float)): {isinstance(3.14, (int, float))}")

# int() / float() / str() / bool() 类型转换（项目中 13 次）
print(f"  int('42'): {int('42')}, float('3.14'): {float('3.14')}")
print(f"  str(100): '{str(100)}', bool(1): {bool(1)}, bool(0): {bool(0)}")


# --- 知识点 1.7: 字符串方法 ---
# 项目中 15 个文件使用字符串方法
raw_text: str = "  银行个人转账业务介绍 v2.0\n"
print("\n【字符串方法示例】")
print(f"  原始: {repr(raw_text)}")
print(f"  .strip(): {repr(raw_text.strip())}")         # 去首尾空白
print(f"  .lower(): {repr(raw_text.lower())}")         # 小写
print(f"  .upper(): {repr(raw_text.upper())}")         # 大写
print(f"  .replace('v2.0', 'v3.0'): {repr(raw_text.replace('v2.0', 'v3.0'))}")
print(f"  .split(): {raw_text.strip().split()}")       # 按空白分割
print(f"  .join(): {' | '.join(['A', 'B', 'C'])}")     # 连接
print(f"  .count('银行'): {raw_text.count('银行')}")    # 计数
print(f"  .find('银行'): {raw_text.find('银行')}")      # 查找位置
print(f"  .startswith('  '): {raw_text.startswith('  ')}")   # 判断前缀
print(f"  .endswith('\\n'): {raw_text.endswith(chr(10))}")    # 判断后缀
# 切片
text_sample: str = "银行个人转账业务介绍"
print(f"  .切片[:2]: '{text_sample[:2]}', [2:4]: '{text_sample[2:4]}'")
print(f"  .倒序: '{text_sample[::-1]}'")


# ================================================================================
# Part 2: 数据结构 — 列表/字典/集合/元组、推导式、排序、解包
# ================================================================================
# 频次统计：
#   列表推导式 (List Comprehension)   — 28 次，项目最常用的 Pythonic 写法
#   字典推导式 (Dict Comprehension)    — 10+ 次
#   sorted() with key=lambda          — 16 次
#   元组解包 (Tuple Unpacking)         — 5 次
#   集合操作 (Set Operations)          — 4 次
#   dict.get() 方法                    — 16 次
# ================================================================================

print("\n" + "=" * 70)
print("Part 2: 数据结构与推导式")
print("=" * 70)


# --- 知识点 2.1: 列表推导式 (List Comprehension) ---
# 项目中 28 个文件使用，是最常见的 Pythonic 写法。
# 一个简单的推导式替代 3-4 行 for 循环。
documents: list[dict[str, Any]] = [
    {"content": "个人转账限额为每日5万元", "score": 0.92},
    {"content": "企业网银转账限额为每日100万元", "score": 0.78},
    {"content": "跨境汇款需提供SWIFT代码", "score": 0.65},
    {"content": "定期存款利率为年化3.5%", "score": 0.45},
]

# 普通 for 循环写法（不推荐）
high_score_contents_old: list[str] = []
for doc in documents:
    if doc["score"] >= 0.7:
        high_score_contents_old.append(doc["content"])

# 列表推导式写法（推荐，项目中 28 次）
high_score_contents: list[str] = [
    doc["content"] for doc in documents if doc["score"] >= 0.7
]
print("【列表推导式示例 — 提取得分 >=0.7 的内容】")
for i, c in enumerate(high_score_contents):
    print(f"  [{i}] {c}")

# 带条件转换的推导式
score_labels: list[str] = [
    f"{doc['content'][:15]}... (得分:{doc['score']:.0%})"
    for doc in documents
]
print(f"\n  得分标签: {score_labels}")

# 嵌套推导式的使用场景：展平二维列表
nested: list[list[int]] = [[1, 2, 3], [4, 5], [6, 7, 8]]
flattened: list[int] = [x for row in nested for x in row]
print(f"  展平嵌套列表 {nested} → {flattened}")


# --- 知识点 2.2: 字典推导式 (Dict Comprehension) ---
# 快速构建映射表，项目中 10+ 次使用
content_score_map: dict[str, float] = {
    doc["content"]: doc["score"] for doc in documents
}
print(f"\n【字典推导式示例】")
print(f"  内容→得分映射: {content_score_map}")

# 反转映射（交换 key 和 value，注意重复键风险）
score_to_content: dict[float, str] = {
    v: k for k, v in content_score_map.items()
}
print(f"  得分→内容映射: {score_to_content}")


# --- 知识点 2.3: sorted() + lambda ---
# 项目中 16 次使用。lambda 是匿名函数，适合简短的回调。
docs_by_score: list[dict[str, Any]] = sorted(
    documents, key=lambda doc: doc["score"], reverse=True
)
print(f"\n【sorted() + lambda 示例 — 按得分降序排列】")
for doc in docs_by_score:
    print(f"  得分 {doc['score']:.2f}: {doc['content']}")

# 按字符串长度排序
words: list[str] = ["跨境汇款", "个人", "转账", "SWIFT代码", "网银"]
words_by_len: list[str] = sorted(words, key=lambda w: len(w), reverse=True)
print(f"  按长度排序: {words_by_len}")


# --- 知识点 2.4: 元组与解包 ---
# Python 中元组是不可变的，常用于多返回值、交换变量
# 项目中有 5 处元组解包

# 元组定义（逗号是关键，括号可省略）
doc_tuple: tuple[str, float] = ("转账限额文档", 0.92)
name, score_unpacked = doc_tuple   # 解包到两个变量
print(f"\n【元组解包示例】")
print(f"  文档名: {name}, 得分: {score_unpacked}")

# 变量交换（一行搞定，不需要临时变量）
a, b = 10, 20
a, b = b, a
print(f"  交换后: a={a}, b={b}")

# 星号解包（收集剩余部分）
first, *rest = [0.95, 0.88, 0.76, 0.65, 0.52]
print(f"  第一个: {first}, 剩余: {rest}")

# 多返回值（实际上是返回了一个元组）
def get_doc_stats() -> tuple[int, float, float]:
    """返回文档统计：(数量, 平均分, 最高分)"""
    scores = [doc["score"] for doc in documents]
    return len(scores), sum(scores) / len(scores), max(scores)

count, avg_score, top_score = get_doc_stats()
print(f"  文档统计: {count=}, {avg_score=:.2f}, {top_score=:.2f}")


# --- 知识点 2.5: 集合 (set) ---
# 无序、不重复、支持集合运算
doc_a_topics: set[str] = {"转账", "限额", "网银", "个人"}
doc_b_topics: set[str] = {"转账", "SWIFT", "跨境", "企业"}

print(f"\n【集合操作示例】")
print(f"  doc_a 主题: {doc_a_topics}")
print(f"  doc_b 主题: {doc_b_topics}")
print(f"  并集 (|):       {doc_a_topics | doc_b_topics}")
print(f"  交集 (&):       {doc_a_topics & doc_b_topics}")
print(f"  差集 (-):       {doc_a_topics - doc_b_topics}")
print(f"  对称差 (^):     {doc_a_topics ^ doc_b_topics}")
print(f"  '转账' 在 a 中: {'转账' in doc_a_topics}")

# 用集合去重（项目中常用模式）
raw_items: list[str] = ["转账", "限额", "转账", "网银", "限额", "转账"]
unique_items: list[str] = list(set(raw_items))
print(f"  去重: {raw_items} → {unique_items}")


# --- 知识点 2.6: dict 常用操作 ---
# .get() 在项目中使用 16 次，避免 KeyError
config_map: dict[str, str] = {"model": "deepseek-v3", "temperature": "0.7"}
print(f"\n【dict 操作示例】")
# .get() 第二个参数是找不到时的默认值
print(f"  config.get('model'): {config_map.get('model')}")
print(f"  config.get('unknown', 'N/A'): {config_map.get('unknown', 'N/A')}")
# .pop() 取出并删除
temp: str = config_map.pop("temperature", "0.5")
print(f"  pop 后: {config_map}, 取出的值: {temp}")
# .items() / .keys() / .values()
for key, value in config_map.items():
    print(f"  配置项: {key} = {value}")
# dict 合并 (Python 3.9+)
merged: dict[str, str] = config_map | {"max_tokens": "4096"}
print(f"  合并后: {merged}")


# ================================================================================
# Part 3: 函数进阶 — 闭包、lambda、装饰器、生成器、上下文管理器
# ================================================================================
# 频次统计：
#   嵌套函数/闭包 (Nested Function/Closure) — 12 次
#   generator (yield)                        — 6 次
#   @staticmethod 装饰器                      — 14 次（Part 4 讲）
#   @lru_cache 装饰器                         — 2 次
#   @abstractmethod 装饰器                    — 2 次（Part 4 讲）
#   with 上下文管理器                          — 14 次
#   contextlib.contextmanager                  — 1 次
# ================================================================================

print("\n" + "=" * 70)
print("Part 3: 函数进阶")
print("=" * 70)


# --- 知识点 3.1: lambda 表达式 ---
# 匿名函数，适合作为 sorted()/map()/filter() 的回调
# 项目中 10 次使用（主要是 sorted(key=lambda ...)）

# lambda 语法: lambda 参数: 返回值
multiply: Callable[[int, int], int] = lambda x, y: x * y
print(f"【lambda 示例】")
print(f"  lambda 乘法: multiply(3, 5) = {multiply(3, 5)}")

# 用于 filter 筛选
bank_products: list[str] = ["转账", "理财", "存款", "贷款", "汇款"]
# 选出长度 >= 2 的产品
long_products: list[str] = list(filter(lambda p: len(p) >= 2, bank_products))
print(f"  filter 长度>=2: {long_products}")

# 用于 map 映射
product_lengths: list[int] = list(map(lambda p: len(p), bank_products))
print(f"  map 求长度: {product_lengths}")


# --- 知识点 3.2: 嵌套函数与闭包 ---
# 项目中 12 处使用，常用于：封装逻辑、创建工厂函数、延迟执行
def create_score_filter(min_score: float):
    """
    闭包工厂：根据最低分阈值创建一个过滤函数。
    内层函数"记住"了外层函数的 min_score 值。
    """
    def filter_func(doc: dict[str, Any]) -> bool:
        # 内层函数访问外层变量 min_score → 这就是闭包
        return doc["score"] >= min_score
    return filter_func

# 创建不同的过滤器
high_pass = create_score_filter(0.85)   # 高分过滤器
low_pass = create_score_filter(0.50)    # 低分过滤器
print(f"\n【闭包示例】")
print(f"  高分过滤(>=0.85): {[d['content'][:12] for d in documents if high_pass(d)]}")
print(f"  低分过滤(>=0.50): {[d['content'][:12] for d in documents if low_pass(d)]}")

# 闭包的另一个经典用途：计数器
def make_counter() -> Callable[[], int]:
    count = 0
    def increment() -> int:
        nonlocal count    # nonlocal 声明使用外层变量（而非局部变量）
        count += 1
        return count
    return increment

counter = make_counter()
print(f"  计数器: {counter()}, {counter()}, {counter()}")


# --- 知识点 3.3: 装饰器 (Decorator) ---
# 项目中有：
#   @staticmethod (14 次)、@abstractmethod (2 次)、@lru_cache (2 次)
#   @app.get / @app.post (FastAPI 路由装饰器)
#   @contextmanager (1 次)
# 下面自己实现一个计时装饰器

import time

def timer_decorator(func: Callable):
    """计时装饰器：打印函数执行耗时"""
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"    [装饰器] {func.__name__} 执行耗时: {elapsed:.4f} 秒")
        return result
    return wrapper

@timer_decorator
def simulate_embedding(text: str) -> list[float]:
    """模拟生成文本嵌入向量（耗时计算）"""
    # 模拟耗时操作
    time.sleep(0.05)
    # 简单的伪嵌入：用字符 ASCII 码生成
    return [float(ord(c)) / 1000.0 for c in text[:10]]

print(f"\n【装饰器示例】")
vec = simulate_embedding("银行转账")
print(f"  嵌入向量(前5维): {vec[:5]}...")

# functools.lru_cache 装饰器（项目中出现 2 次）
# 作用：缓存函数结果，避免重复计算
from functools import lru_cache
call_count: int = 0

@lru_cache(maxsize=128)
def expensive_compute(x: int) -> int:
    """耗时计算（结果会被缓存）"""
    global call_count
    call_count += 1
    time.sleep(0.02)  # 模拟耗时
    return x * x

print(f"\n【lru_cache 装饰器示例】")
print(f"  第一次 expensive_compute(5): {expensive_compute(5)} (调用次数={call_count})")
print(f"  第二次 expensive_compute(5): {expensive_compute(5)} (调用次数={call_count}，命中缓存！)")


# --- 知识点 3.4: 生成器 (Generator) ---
# 用 yield 代替 return，实现惰性计算。项目中 6 处使用。
# 应用场景：流式输出(SSE)、大文件逐行读取、数据流管道

def generate_scores(count: int) -> Iterator[float]:
    """生成器函数：逐个产出得分，而非一次性返回列表"""
    import random
    random.seed(42)  # 固定随机种子保证结果可复现
    for i in range(count):
        yield round(random.uniform(0.5, 1.0), 3)

print(f"\n【生成器示例】")
gen = generate_scores(5)
print(f"  生成器对象: {gen}")
print(f"  next(gen): {next(gen)}")       # 手动获取下一个值
print(f"  用 for 遍历剩余值:")
for score_val in gen:
    print(f"    得分: {score_val}")

# 生成器表达式（类似列表推导式，但用圆括号）
# 内存友好：不会一次性创建整个列表
score_gen = (d["score"] for d in documents if d["score"] >= 0.6)
print(f"  生成器表达式: {list(score_gen)}")

# 生成器实现 SSE 流（项目中 QA 服务用此模式返回流式答案）
def sse_stream_answer(answer: str) -> Iterator[str]:
    """模拟 SSE 流：逐字返回答案"""
    for i, char in enumerate(answer):
        chunk = f'data: {{"index": {i}, "text": "{char}"}}\n\n'
        yield chunk
        time.sleep(0.01)  # 模拟流延迟
    yield "data: [DONE]\n\n"          # 流结束信号

print(f"\n  SSE 流式输出模拟:")
for event in sse_stream_answer("转账限额5万"):
    if "[DONE]" not in event:
        print(f"    {event.strip()}", end="\r")


# --- 知识点 3.5: 上下文管理器 (Context Manager) ---
# 项目中 14 处使用 with 语句
# 应用场景：
#   with ThreadPoolExecutor()...   (线程池)
#   with self._lock:               (线程锁)
#   with httpx.Client()...         (HTTP 客户端)
#   with open(...) as f:           (文件)
#   with tempfile.NamedTemporaryFile() (临时文件)
#   with torch.no_grad():          (PyTorch 推理)

# 方式一：使用 @contextmanager 装饰器（项目 metadata_store.py）
from contextlib import contextmanager

@contextmanager
def database_connection(db_path: str):
    """模拟数据库连接上下文管理器"""
    print(f"\n【上下文管理器示例】")
    print(f"  连接到数据库: {db_path}")
    # 获取资源（类似于 __enter__）
    conn = {"path": db_path, "connected": True, "data": {}}
    try:
        yield conn  # 将资源交给 with 块使用
        # with 块正常执行完毕后到这里
        print(f"  提交事务（commit）")
    except Exception as e:
        # with 块发生异常时到这里
        print(f"  回滚事务（rollback），原因: {e}")
        raise
    finally:
        # 无论是否异常都会执行
        print(f"  关闭连接")

# 使用自定义上下文管理器
with database_connection("knowledge.db") as conn:
    conn["data"]["key"] = "银行知识库"
    print(f"  执行操作: 写入 {conn['data']}")

# 方式二：定义 __enter__ / __exit__ 方法（面向对象方式，见 Part 4）


# ================================================================================
# Part 4: 面向对象 — 类、继承、抽象基类、静态方法、数据类
# ================================================================================
# 频次统计：
#   类定义 (OOP)                  — 30 次，项目核心组织形式
#   @dataclass                   — 15 次，广泛用于数据模型
#   @staticmethod                — 14 次
#   继承 (Inheritance)           — 6+ 次
#   @abstractmethod              — 2 次（vector_store.py 中的抽象基类）
#   super().__init__()           — 3 次
#   自定义异常类                   — 2 次
#   dataclass(frozen=True)       — 1 次
#   dataclass(field(...))        — 3 次
#   类属性 (Class Variables)      — 5+ 次
#   __dict__ 属性                 — 1 次
# ================================================================================

print("\n\n" + "=" * 70)
print("Part 4: 面向对象编程")
print("=" * 70)


# --- 知识点 4.1: 基本类定义 ---
# 项目中 30 个文件定义了类

class BankDocument:
    """
    银行文档类：代表一条知识库文档。
    包含类属性、实例属性、实例方法、特殊方法(__repr__)。
    """

    # 类属性：所有实例共享
    source_type: str = "bank_knowledge"  # 类级别常量

    def __init__(self, content: str, score: float = 0.0, doc_id: str | None = None):
        """构造函数：self 代表实例本身"""
        # 实例属性：每个实例独有
        self.content: str = content
        self.score: float = score
        self.doc_id: str = doc_id or f"doc_{id(self)}"  # 自动生成 ID

    def summary(self, max_len: int = 30) -> str:
        """实例方法：获取文档摘要"""
        text = self.content.strip()
        return text[:max_len] + ("..." if len(text) > max_len else "")

    def is_relevant(self, threshold: float = 0.6) -> bool:
        """判断文档是否满足相关度阈值"""
        return self.score >= threshold

    def __repr__(self) -> str:
        """特殊方法：定义打印时的显示格式"""
        return f"BankDocument(id={self.doc_id}, score={self.score:.2f})"

    def __eq__(self, other: object) -> bool:
        """特殊方法：定义 == 比较逻辑"""
        if not isinstance(other, BankDocument):
            return NotImplemented
        return self.doc_id == other.doc_id

print("【面向对象示例】")
# 创建实例
doc1 = BankDocument("个人转账限额为每日5万元", score=0.92, doc_id="D001")
doc2 = BankDocument("企业网银转账限额为每日100万元", score=0.78, doc_id="D002")
doc3 = BankDocument("跨境汇款需提供SWIFT代码", score=0.58)

print(f"  doc1: {doc1}")
print(f"  doc1.summary(): {doc1.summary()}")
print(f"  doc1.is_relevant(): {doc1.is_relevant()}")
print(f"  doc3.is_relevant(): {doc3.is_relevant()}")
print(f"  doc1 == doc2: {doc1 == doc2}")
print(f"  类属性: {BankDocument.source_type}")


# --- 知识点 4.2: 继承与方法重写 ---
# 父类定义通用逻辑，子类扩展特定功能

class ScoredDocument(BankDocument):
    """带评分信息的文档子类"""
    def __init__(self, content: str, score: float = 0.0,
                 doc_id: str | None = None, category: str = "通用"):
        # super() 调用父类构造函数
        super().__init__(content, score, doc_id)
        self.category: str = category  # 子类新增属性

    def summary(self, max_len: int = 30) -> str:
        """重写父类方法：在摘要中附加分类信息"""
        base = super().summary(max_len)  # 调用父类实现
        return f"[{self.category}] {base}"

    def __repr__(self) -> str:
        return (f"ScoredDocument(id={self.doc_id}, score={self.score:.2f}, "
                f"category='{self.category}')")

print(f"\n【继承示例】")
scored_doc = ScoredDocument("定期存款利率为年化3.5%", score=0.72, category="存款业务")
print(f"  {scored_doc}")
print(f"  summary: {scored_doc.summary()}")
print(f"  isinstance(scored_doc, BankDocument): {isinstance(scored_doc, BankDocument)}")


# --- 知识点 4.3: 抽象基类 (ABC) ---
# 项目中 vector_store.py 用 ABC 定义了向量存储抽象接口
from abc import ABC, abstractmethod

class BaseVectorStore(ABC):
    """
    向量存储抽象基类。
    强制子类实现 search 和 add 方法。
    """
    @abstractmethod
    def search(self, query_vector: list[float], top_k: int) -> list[tuple[str, float]]:
        """搜索最相似的 top_k 条文档"""
        ...

    @abstractmethod
    def add(self, doc_id: str, vector: list[float], metadata: dict[str, Any]) -> None:
        """添加文档向量"""
        ...

    # 非抽象方法可以有默认实现
    def count(self) -> int:
        """返回文档数量（默认实现返回 0）"""
        return 0

class InMemoryVectorStore(BaseVectorStore):
    """内存向量存储实现 — 必须实现所有抽象方法"""

    def __init__(self):
        self._vectors: dict[str, list[float]] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def search(self, query_vector: list[float], top_k: int) -> list[tuple[str, float]]:
        # 使用简单的点积作为相似度计算
        results: list[tuple[str, float]] = []
        for doc_id, vec in self._vectors.items():
            # 点积相似度
            sim = sum(a * b for a, b in zip(query_vector, vec))
            results.append((doc_id, round(sim, 4)))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def add(self, doc_id: str, vector: list[float], metadata: dict[str, Any]) -> None:
        self._vectors[doc_id] = vector
        self._metadata[doc_id] = metadata

    def count(self) -> int:
        return len(self._vectors)

print(f"\n【抽象基类示例】")
store = InMemoryVectorStore()
store.add("D001", [0.1, 0.5, 0.3], {"title": "转账限额"})
store.add("D002", [0.8, 0.2, 0.1], {"title": "理财产品"})
store.add("D003", [0.15, 0.45, 0.28], {"title": "汇款指南"})

query_vec: list[float] = [0.12, 0.48, 0.31]
top_results = store.search(query_vec, top_k=2)
print(f"  向量存储文档数: {store.count()}")
print(f"  搜索 '{query_vec}' 的 top2 结果:")
for doc_id, sim in top_results:
    print(f"    {doc_id}: 相似度={sim:.4f}")


# --- 知识点 4.4: @staticmethod 静态方法 ---
# 项目中最常用的装饰器之一（14 次）
# 不依赖实例(self)或类(cls)，只是逻辑上归入类中
import hashlib

class TextUtils:
    """文本工具类"""

    @staticmethod
    def compute_md5(text: str) -> str:
        """计算文本的 MD5 哈希（不依赖实例状态）"""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本"""
        import re
        # 去掉多余空白
        text = re.sub(r'\s+', ' ', text.strip())
        return text

    @staticmethod
    def is_valid_length(text: str, min_len: int = 2, max_len: int = 1000) -> bool:
        """检查文本长度是否合法"""
        return min_len <= len(text) <= max_len

print(f"\n【静态方法示例】")
print(f"  MD5('银行'): {TextUtils.compute_md5('银行')}")
print(f"  clean_text('  hello   world  '): '{TextUtils.clean_text('  hello   world  ')}'")
print(f"  is_valid_length('hi'): {TextUtils.is_valid_length('hi')}")
print(f"  is_valid_length('h'): {TextUtils.is_valid_length('h')}")


# --- 知识点 4.5: @dataclass 数据类 ---
# 项目中 15 个文件使用，是最重要的数据建模工具
# 自动生成 __init__、__repr__、__eq__ 等方法
from dataclasses import dataclass, field, asdict

@dataclass
class RetrievedDocument:
    """检索到的文档（数据类）"""
    doc_id: str                              # 必填字段
    content: str                             # 必填字段
    score: float                             # 必填字段
    # 带默认值的字段
    source: str = "unknown"
    # field(default_factory=...) 用于可变默认值（很重要！不能直接写 =[]）
    keywords: list[str] = field(default_factory=list)

@dataclass
class SearchResult:
    """搜索结果"""
    query: str
    documents: list[RetrievedDocument] = field(default_factory=list)
    total_time_ms: float = 0.0

    @property
    def top_doc(self) -> RetrievedDocument | None:
        """计算属性：获取最相关文档"""
        if not self.documents:
            return None
        # sorted + lambda，项目中 16 次使用
        return sorted(self.documents, key=lambda d: d.score, reverse=True)[0]

print(f"\n【数据类示例】")
# 创建数据类实例
ret_doc1 = RetrievedDocument(
    doc_id="D001", content="个人转账限额为每日5万元",
    score=0.92, source="bank_faq", keywords=["转账", "限额"]
)
ret_doc2 = RetrievedDocument(
    doc_id="D002", content="企业网银转账限额为每日100万元",
    score=0.78, source="bank_faq", keywords=["企业", "网银"]
)

search_result = SearchResult(
    query="转账限额",
    documents=[ret_doc1, ret_doc2],
    total_time_ms=125.5
)

print(f"  top_doc: {search_result.top_doc}")
print(f"  asdict(ret_doc1): {asdict(ret_doc1)}")

# frozen=True 创建不可变数据类
@dataclass(frozen=True)
class ImmutableConfig:
    """不可变配置"""
    model_name: str = "deepseek-v3"
    temperature: float = 0.7

config = ImmutableConfig()
# config.temperature = 0.9  # 这行会报错！frozen 实例不可修改
print(f"  ImmutableConfig: {config}")


# --- 知识点 4.6: 自定义异常类 ---
# 项目中 2 处自定义异常

class BankRAGException(Exception):
    """银行 RAG 系统的基类异常"""
    def __init__(self, message: str, error_code: str = "UNKNOWN"):
        super().__init__(message)
        self.error_code: str = error_code

class DocumentNotFoundError(BankRAGException):
    """文档未找到异常"""
    def __init__(self, doc_id: str):
        super().__init__(
            message=f"文档 {doc_id} 未找到",
            error_code="DOC_NOT_FOUND"
        )

print(f"\n【自定义异常示例】")
try:
    raise DocumentNotFoundError("D999")
except DocumentNotFoundError as e:
    print(f"  捕获异常: {e}, 错误码: {e.error_code}")


# ================================================================================
# Part 5: 模块与库 — pathlib、json、re、hashlib、datetime、threading、numpy
# ================================================================================
# 频次统计：
#   json 模块               — 10 次
#   re 模块                 — 10 次
#   pathlib 模块            — 10 次
#   hashlib 模块            — 6 次
#   time 模块               — 8 次
#   threading 模块           — 8 次
#   numpy 模块              — 7 次
#   datetime 模块            — 3 次
#   copy.deepcopy 模块       — 6 次
#   concurrent.futures       — 4 次
# ================================================================================

print("\n\n" + "=" * 70)
print("Part 5: 标准库与常用库")
print("=" * 70)


# --- 知识点 5.1: json 模块 ---
# 项目中 10 个文件使用，用于序列化/反序列化
import json

print("【json 模块示例】")
# Python dict → JSON 字符串（序列化）
bank_data: dict[str, Any] = {
    "bank_name": "杭州银行",
    "products": ["转账", "理财", "存款"],
    "stats": {"customers": 500000, "branches": 120},
    "is_listed": True,
    "unicode_text": "银行知识库"  # 中文
}
json_str: str = json.dumps(bank_data, ensure_ascii=False, indent=2)
print(f"  json.dumps (序列化):\n{json_str}")

# JSON 字符串 → Python dict（反序列化）
parsed: dict[str, Any] = json.loads('{"query": "转账限额", "top_k": 5}')
print(f"  json.loads (反序列化): {parsed}")

# 处理解析错误
try:
    json.loads("{invalid json}")
except json.JSONDecodeError as e:
    print(f"  JSON 解析错误: {e}")


# --- 知识点 5.2: re 正则表达式 ---
# 项目中 10 个文件使用
import re

print("\n【re 正则表达式示例】")
bank_text: str = """
联系电话：0571-88888888
业务编号：BK-2024-00123
金额：￥15,280.00
日期：2024-03-15
客服邮箱：service@hzbank.com
"""

# 提取电话号码
phone_pattern: str = r'\d{3,4}-\d{7,8}'
phones: list[str] = re.findall(phone_pattern, bank_text)
print(f"  电话号码: {phones}")

# 提取业务编号
biz_pattern: str = r'[A-Z]+-\d{4}-\d+'
biz_ids: list[str] = re.findall(biz_pattern, bank_text)
print(f"  业务编号: {biz_ids}")

# 提取金额
amount_pattern: str = r'￥[\d,]+\.\d{2}'
amounts: list[str] = re.findall(amount_pattern, bank_text)
print(f"  金额: {amounts}")

# re.sub 替换（文本清洗，项目 cleaner.py 中使用）
cleaned_text: str = re.sub(r'\s+', ' ', bank_text).strip()
print(f"  re.sub 清洗后: '{cleaned_text[:60]}...'")

# 按模式分割（项目 chunker.py 中正则分块）
sections: list[str] = re.split(r'[。！？\n]+', cleaned_text)
print(f"  re.split 分句: {[s.strip() for s in sections if s.strip()]}")


# --- 知识点 5.3: pathlib 路径操作 ---
# 项目中 10 个文件使用
from pathlib import Path

print("\n【pathlib 示例】")
# 当前文件路径
current_file: Path = Path(__file__).resolve()
print(f"  当前文件: {current_file}")
print(f"  文件名: {current_file.name}")
print(f"  后缀: {current_file.suffix}")
print(f"  父目录: {current_file.parent}")
print(f"  是否是文件: {current_file.is_file()}")

# 路径拼接（用 / 运算符，比 os.path.join 更直观）
data_dir: Path = current_file.parent / "data" / "documents"
print(f"  数据目录: {data_dir}")
print(f"  相对于父目录的路径: {data_dir.relative_to(current_file.parent)}")

# 检查路径是否存在
print(f"  data_dir 存在: {data_dir.exists()}")


# --- 知识点 5.4: hashlib 哈希 ---
# 项目中 6 次使用（MD5/SHA256/SHA1）
# 用途：缓存键生成、文档去重、内容指纹

print("\n【hashlib 示例】")
content: str = "个人转账限额为每日5万元"

# MD5（128 位哈希，项目中用于缓存键）
md5_hash: str = hashlib.md5(content.encode("utf-8")).hexdigest()
print(f"  MD5: {md5_hash} (长度={len(md5_hash)})")

# SHA256（256 位哈希，更安全，项目中用于内容指纹）
sha256_hash: str = hashlib.sha256(content.encode("utf-8")).hexdigest()
print(f"  SHA256: {sha256_hash[:32]}... (长度={len(sha256_hash)})")

# SHA1（项目中用于 Redis key 生成）
sha1_hash: str = hashlib.sha1(content.encode("utf-8")).hexdigest()
print(f"  SHA1: {sha1_hash} (长度={len(sha1_hash)})")

# 修改一个字，哈希完全不同（雪崩效应）
similar: str = "个人转账限额为每日4万元"
md5_similar: str = hashlib.md5(similar.encode("utf-8")).hexdigest()
print(f"  相似文本 MD5: {md5_similar}")
print(f"  两个 MD5 是否相同: {md5_hash == md5_similar}")


# --- 知识点 5.5: datetime 时间处理 ---
# 项目中 3 个文件使用
from datetime import datetime, timezone, timedelta

print("\n【datetime 示例】")
# 当前时间（带时区）
now_utc: datetime = datetime.now(timezone.utc)
print(f"  UTC 时间: {now_utc.isoformat()}")

# 北京时间
beijing_tz = timezone(timedelta(hours=8))
now_beijing: datetime = datetime.now(beijing_tz)
print(f"  北京时间: {now_beijing.strftime('%Y-%m-%d %H:%M:%S')}")

# 解析时间字符串（项目中用于解析文档日期）
date_str: str = "2024-03-15 10:30:00"
parsed_date: datetime = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
print(f"  解析 '{date_str}': {parsed_date}")

# 时间戳计算（项目中用于缓存过期判断）
created_at: datetime = datetime.now(timezone.utc)
age_seconds: float = (datetime.now(timezone.utc) - created_at).total_seconds()
print(f"  时间差: {age_seconds:.3f} 秒")

# 时间戳转 datetime（项目中用 mktime/strptime）
timestamp: float = 1710500000.0
dt_from_ts: datetime = datetime.fromtimestamp(timestamp, tz=timezone.utc)
print(f"  时间戳 {timestamp} → {dt_from_ts.isoformat()}")


# --- 知识点 5.6: threading 线程安全 ---
# 项目中 8 个文件使用 Lock / BoundedSemaphore
import threading

print("\n【threading 示例】")

class ThreadSafeCounter:
    """线程安全的计数器（用 Lock 保护共享状态）"""
    def __init__(self):
        self._value: int = 0
        self._lock: threading.Lock = threading.Lock()

    def increment(self) -> int:
        with self._lock:          # 项目中 14 处 context manager 用法
            self._value += 1
            return self._value

    @property
    def value(self) -> int:
        with self._lock:
            return self._value

counter = ThreadSafeCounter()
for i in range(5):
    counter.increment()
print(f"  线程安全计数器: {counter.value}")


# --- 知识点 5.7: concurrent.futures 线程池 ---
# 项目中 4 个文件使用 ThreadPoolExecutor
from concurrent.futures import ThreadPoolExecutor, as_completed

print("\n【concurrent.futures 示例】")
def fetch_embedding(text: str) -> tuple[str, float]:
    """模拟获取文本嵌入（耗时 IO 操作）"""
    time.sleep(0.03)
    return (text, len(text) * 0.1)

texts_to_embed: list[str] = [
    "转账限额", "理财产品", "定期存款", "跨境汇款", "信用卡"
]

# 使用 with 语句管理线程池生命周期
with ThreadPoolExecutor(max_workers=3) as executor:
    # 提交任务
    futures = {
        executor.submit(fetch_embedding, text): text
        for text in texts_to_embed
    }
    # as_completed 按完成顺序获取结果
    for future in as_completed(futures):
        text, score = future.result()
        print(f"    完成: '{text}' → 得分={score:.1f}")


# --- 知识点 5.8: numpy 数组操作 ---
# 项目中 7 个文件使用，用于向量计算和余弦相似度
try:
    import numpy as np

    print("\n【numpy 示例】")
    # 创建嵌入向量
    emb1: np.ndarray = np.array([0.1, 0.5, 0.3], dtype=np.float32)
    emb2: np.ndarray = np.array([0.8, 0.2, 0.1], dtype=np.float32)
    emb3: np.ndarray = np.array([0.12, 0.48, 0.31], dtype=np.float32)

    print(f"  emb1: {emb1}")
    print(f"  emb2: {emb2}")
    print(f"  emb3: {emb3}")

    # 点积（内积）计算相似度
    dot_ab: float = float(np.dot(emb1, emb2))
    dot_ac: float = float(np.dot(emb1, emb3))
    print(f"  点积相似度 1-2: {dot_ab:.4f}, 1-3: {dot_ac:.4f}")

    # L2 范数归一化后计算余弦相似度
    cosine_ab: float = float(
        np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    )
    cosine_ac: float = float(
        np.dot(emb1, emb3) / (np.linalg.norm(emb1) * np.linalg.norm(emb3))
    )
    print(f"  余弦相似度 1-2: {cosine_ab:.4f}, 1-3: {cosine_ac:.4f}")
    print(f"  结论: emb3 与 emb1 更相似 (余弦相似度更高)")

    # numpy 批量操作
    all_embs: np.ndarray = np.asarray([emb1, emb2, emb3], dtype=np.float32)
    norms: np.ndarray = np.linalg.norm(all_embs, axis=1)
    print(f"  各向量 L2 范数: {norms}")

except ImportError:
    print("\n  [跳过] numpy 未安装，请执行 pip install numpy")


# ================================================================================
# Part 6: 设计模式 — 缓存（LRU/TTL）、单例、依赖注入、策略模式
# ================================================================================
# 频次统计：
#   LRU 缓存模式              — 2 个独立实现（embedding_cache、query_cache）
#   TTL 缓存模式              — 2 个（retrieval_cache 语义缓存）
#   模块级单例                 — 3 处（plus_settings、global_config 等）
#   依赖注入                   — 2 次（FastAPI Depends）
#   惰性导入                   — 6 次（try/except import）
#   if __name__ == "__main__" — 4 次
# ================================================================================

print("\n\n" + "=" * 70)
print("Part 6: 设计模式")
print("=" * 70)


# --- 知识点 6.1: LRU 缓存模式 ---
# 项目中 embedding_cache.py 和 query_cache.py 实现了 LRU 缓存
# 核心：使用 OrderedDict 的 move_to_end + popitem
from collections import OrderedDict

class SimpleLRUCache:
    """
    简易 LRU（Least Recently Used）缓存。
    当缓存满时，淘汰最久未使用的条目。
    """

    def __init__(self, max_size: int = 5):
        self.max_size: int = max_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._lock: threading.Lock = threading.Lock()   # 线程安全

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key not in self._cache:
                return None
            # 刚访问的条目移到末尾（最近使用）
            self._cache.move_to_end(key)
            return self._cache[key]

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            # 超出容量时淘汰最旧的（FIFO 端）
            if len(self._cache) > self.max_size:
                old_key, old_val = self._cache.popitem(last=False)
                print(f"    [LRU] 淘汰: {old_key}")

    def __len__(self) -> int:
        return len(self._cache)

    def __repr__(self) -> str:
        return f"LRUCache({list(self._cache.keys())})"

print("【LRU 缓存示例】")
lru = SimpleLRUCache(max_size=3)
lru.put("doc_1", "转账限额文档")
lru.put("doc_2", "理财产品文档")
lru.put("doc_3", "存款利率文档")
print(f"  初始: {lru}")
lru.get("doc_1")              # 访问 doc_1，它变"刚使用"
lru.put("doc_4", "贷款指南文档")   # 触发淘汰：doc_2 最久未使用
print(f"  加入 doc_4 后: {lru}")


# --- 知识点 6.2: 模块级单例 ---
# 项目中 config.py 通过模块级变量实现单例
# plus_settings = PlusSettings() → 整个进程只有一个实例

class AppConfig:
    """应用配置（单例模式）"""
    _instance: AppConfig | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls):
        """线程安全的单例实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # 双重检查
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:   # 防止重复初始化
            return
        self.model_name: str = "deepseek-v3"
        self.temperature: float = 0.7
        self.top_k: int = 5
        self._initialized = True

print(f"\n【单例模式示例】")
cfg1 = AppConfig()
cfg2 = AppConfig()
print(f"  cfg1 is cfg2: {cfg1 is cfg2}")             # True：同一个对象
print(f"  cfg1.model_name: {cfg1.model_name}")
cfg1.model_name = "gpt-4"
print(f"  修改 cfg1 后 cfg2.model_name: {cfg2.model_name}")  # 也变了


# --- 知识点 6.3: 惰性导入 ---
# 项目中 6 处使用 try/except 处理可选依赖
# 某些库不是必装的（如 redis、pymilvus、torch），不安装时不报错

print(f"\n【惰性导入示例】")
optional_libs: dict[str, bool] = {}

# redis 是可选依赖
try:
    import redis  # type: ignore
    optional_libs["redis"] = True
except ImportError:
    optional_libs["redis"] = False

# pandas 仅在评估模块中使用
try:
    import pandas  # type: ignore
    optional_libs["pandas"] = True
except ImportError:
    optional_libs["pandas"] = False

# jieba 用于中文分词
try:
    import jieba  # type: ignore
    optional_libs["jieba"] = True
except ImportError:
    optional_libs["jieba"] = False

print(f"  可选依赖状态: {optional_libs}")


# --- 知识点 6.4: copy.deepcopy ---
# 项目中 6 处使用 deepcopy，防止修改引用类型参数污染原数据
import copy

print(f"\n【deepcopy 示例】")
original_conf: dict[str, Any] = {
    "model": "deepseek-v3",
    "params": {"temperature": 0.7, "top_p": 0.9}
}
# 浅拷贝：修改嵌套 dict 仍会影响原对象
shallow = original_conf.copy()
shallow["params"]["temperature"] = 0.1
print(f"  浅拷贝后 original.params: {original_conf['params']}")  # 也被改了！

# 深拷贝：完全独立
original_conf["params"]["temperature"] = 0.7  # 恢复
deep = copy.deepcopy(original_conf)
deep["params"]["temperature"] = 0.1
print(f"  深拷贝后 original.params: {original_conf['params']}")  # 不受影响


# --- 知识点 6.5: if __name__ == "__main__" ---
# 项目中 4 处使用。作用：
#   直接执行 python xx.py  → 条件为 True，执行代码
#   import xx 作为模块导入  → 条件为 False，不执行


# ================================================================================
# Part 7: 综合实战 — 迷你银行知识库 RAG 系统
# ================================================================================
# 串联以上所有知识点，构建一个可运行的迷你 RAG 系统。
# 流程：文档管理 → 嵌入向量化 → 混合检索 → 重排序 → 缓存判断 → 答案生成
# ================================================================================

print("\n\n" + "=" * 70)
print("Part 7: 综合实战 — 迷你银行知识库问答系统 (Mini RAG)")
print("=" * 70)

# ── 7.1: 配置模块（数据类 + 单例） ──
@dataclass
class MiniRAGConfig:
    """迷你 RAG 系统配置"""
    model_name: str = "deepseek-v3"
    embedding_dim: int = 128
    top_k: int = 3
    similarity_threshold: float = 0.5
    cache_size: int = 10
    use_rerank: bool = True

# 模块级单例（项目中 3 处使用此模式）
rag_config: MiniRAGConfig = MiniRAGConfig()


# ── 7.2: 文档解析与清洗（re + 字符串方法） ──
class DocumentProcessor:
    """文档处理：清洗、分句、去重"""

    @staticmethod
    def clean(text: str) -> str:
        """清洗文本：去 HTML 标签、压缩空白、统一标点"""
        # re.sub 去标签
        text = re.sub(r'<[^>]+>', '', text)
        # 压缩多余空白
        text = re.sub(r'\s+', ' ', text)
        # 统一中文标点
        text = text.replace('，', '，').replace('。', '。')
        return text.strip()

    @staticmethod
    def split_sentences(text: str) -> list[str]:
        """按句号/问号/感叹号/换行分句"""
        raw = re.split(r'[。！？\n]+', text)
        return [s.strip() for s in raw if len(s.strip()) >= 5]

    @staticmethod
    def compute_doc_id(content: str) -> str:
        """用 SHA256 生成文档唯一 ID（去重依据）"""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


# ── 7.3: 嵌入向量化（numpy + 闭包） ──
class SimpleEmbedder:
    """简易嵌入器：将文本映射为固定维度向量"""

    def __init__(self, dim: int = 128, seed: int = 42):
        self.dim = dim
        import random as _random
        _random.seed(seed)
        # 为每个 Unicode 码点生成随机向量（模拟词向量表）
        self._char_vectors: dict[int, np.ndarray] = {}
        for code in range(0x4E00, 0x9FFF):  # 中文常用范围
            # 实际项目中用真正的 embedding 模型
            vec: np.ndarray = np.random.randn(dim).astype(np.float32)
            vec = vec / (np.linalg.norm(vec) + 1e-8)  # 归一化
            self._char_vectors[code] = vec

    def encode(self, text: str) -> np.ndarray:
        """
        将文本编码为向量。
        策略：取文本中每个字符的向量，求平均。
        实际项目中使用 SiliconFlow / OpenAI Embedding API。
        """
        if not text:
            return np.zeros(self.dim, dtype=np.float32)
        chars = [c for c in text if ord(c) in self._char_vectors]
        if not chars:
            return np.random.randn(self.dim).astype(np.float32)
        vectors = [self._char_vectors[ord(c)] for c in chars]
        avg: np.ndarray = sum(vectors) / len(vectors)
        return avg.astype(np.float32)


# ── 7.4: 缓存系统（LRU + 锁） ──
class EmbeddingCache:
    """嵌入缓存：避免重复计算相同文本的嵌入向量"""

    def __init__(self, max_size: int = 100):
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()

    def get(self, text: str) -> np.ndarray | None:
        key = hashlib.md5(text.encode()).hexdigest()
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key].copy()  # copy 防止外部修改
            return None

    def put(self, text: str, vector: np.ndarray) -> None:
        key = hashlib.md5(text.encode()).hexdigest()
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = vector.copy()
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)


# ── 7.5: 向量存储（ABC 抽象基类 + 继承） ──
class VectorDB:
    """向量数据库：存储文档向量并提供搜索"""

    def __init__(self):
        self._store: dict[str, dict[str, Any]] = {}

    def insert(self, doc_id: str, content: str, vector: np.ndarray,
               metadata: dict[str, Any] | None = None) -> None:
        self._store[doc_id] = {
            "content": content,
            "vector": vector.astype(np.float32),
            "metadata": metadata or {},
        }

    def search(self, query_vector: np.ndarray, top_k: int = 3
               ) -> list[tuple[str, str, float]]:
        """余弦相似度搜索，返回 (doc_id, 内容, 相似度)"""
        results: list[tuple[str, str, float]] = []
        q_norm = float(np.linalg.norm(query_vector))
        for doc_id, info in self._store.items():
            vec = info["vector"]
            # 余弦相似度 = 点积 / (||A|| × ||B||)
            dot = float(np.dot(query_vector, vec))
            d_norm = float(np.linalg.norm(vec))
            similarity = dot / (q_norm * d_norm + 1e-8)
            results.append((doc_id, info["content"], round(similarity, 4)))
        # sorted + lambda 排序（项目中 16 次）
        results.sort(key=lambda x: x[2], reverse=True)
        return results[:top_k]

    def count(self) -> int:
        return len(self._store)


# ── 7.6: BM25 关键词搜索（Collections + 分词） ──
class SimpleBM25:
    """简易 BM25 关键词检索（中文用 jieba 分词）"""

    def __init__(self):
        self._docs: list[tuple[str, str]] = []  # [(doc_id, content), ...]

    def add(self, doc_id: str, content: str) -> None:
        self._docs.append((doc_id, content))

    def search(self, query: str, top_k: int = 3) -> list[tuple[str, str, float]]:
        """基于词频的关键词匹配"""
        try:
            import jieba
            query_words: set[str] = set(jieba.lcut(query))
        except ImportError:
            # 无 jieba 时退化为字符匹配
            query_words = set(query)
        results: list[tuple[str, str, float]] = []

        for doc_id, content in self._docs:
            try:
                import jieba
                doc_words: list[str] = jieba.lcut(content)
            except ImportError:
                doc_words = list(content)
            # 计算匹配得分（命中词数 / 总查询词数）
            doc_set: set[str] = set(doc_words)
            hits: int = len(query_words & doc_set)
            score: float = hits / max(len(query_words), 1)
            if score > 0:
                results.append((doc_id, content, round(score, 4)))

        results.sort(key=lambda x: x[2], reverse=True)
        return results[:top_k]


# ── 7.7: 重排序器（策略模式） ──
class Reranker:
    """对检索结果二次排序"""

    @staticmethod
    def rerank(query: str, candidates: list[tuple[str, str, float]],
               top_k: int = 3) -> list[tuple[str, str, float]]:
        """
        重排序逻辑：对候选文档进行更精细的相关度计算。
        实际项目中调用 SiliconFlow Rerank API。
        这里用简化的关键词密度算法。
        """
        reranked: list[tuple[str, str, float]] = []
        for doc_id, content, _ in candidates:
            # 计算查询词在文档中的出现密度
            query_chars = set(query)
            content_chars = list(content)
            matches = sum(1 for c in content_chars if c in query_chars)
            density = matches / max(len(content_chars), 1)
            # 综合得分 = 原始得分 × 0.3 + 密度 × 0.7
            new_score = round(density * 0.7, 4)
            reranked.append((doc_id, content, new_score))
        reranked.sort(key=lambda x: x[2], reverse=True)
        return reranked[:top_k]


# ── 7.8: 答案生成器（生成器 + 异常处理） ──
class AnswerGenerator:
    """基于检索结果生成答案"""

    @staticmethod
    def generate(query: str, docs: list[tuple[str, str, float]]) -> Iterator[str]:
        """
        流式生成答案（生成器模式）。
        实际项目中调用 LLM（如 DeepSeek-V3）的 stream API。
        """
        if not docs:
            yield "抱歉，没有找到相关的银行知识来回答您的问题。"
            return

        # 取最相关的文档内容
        best_content = docs[0][1]
        best_score = docs[0][2]

        # 模拟流式生成答案
        yield f"📋 基于知识库（相关度: {best_score:.0%}）\n\n"
        yield f"根据我行相关规定，{best_content}。"
        yield "\n\n---\n📖 参考来源:"
        for i, (doc_id, content, score) in enumerate(docs[:3]):
            yield f"\n  [{i+1}] {content[:40]}..."

    @staticmethod
    def generate_full(query: str, docs: list[tuple[str, str, float]]) -> str:
        """非流式版本：生成完整答案"""
        parts = list(AnswerGenerator.generate(query, docs))
        return "".join(parts)


# ── 7.9: 知识库管理器（综合编排类） ──
class KnowledgeBase:
    """
    银行知识库管理器 — 编排所有组件。
    使用依赖注入模式：各组件的实例可灵活替换。
    """

    def __init__(self, config: MiniRAGConfig | None = None):
        self.config = config or rag_config
        self.processor = DocumentProcessor()      # 文档处理
        self.embedder = SimpleEmbedder(dim=self.config.embedding_dim)  # 嵌入
        self.cache = EmbeddingCache(max_size=self.config.cache_size)   # 缓存
        self.vector_db = VectorDB()               # 向量存储
        self.bm25 = SimpleBM25()                  # 关键词检索
        self.reranker = Reranker()                # 重排序
        self.answer_gen = AnswerGenerator()        # 答案生成
        self._ingested_count: int = 0

    def ingest_documents(self, raw_texts: list[str]) -> int:
        """
        文档摄入管道：
          清洗 → 去重 → 嵌入（带缓存）→ 存入向量DB + BM25 索引
        """
        added = 0
        for text in raw_texts:
            # 步骤 1: 清洗
            cleaned = self.processor.clean(text)
            if len(cleaned) < 5:
                continue

            # 步骤 2: 生成唯一 ID（SHA256 去重）
            doc_id = self.processor.compute_doc_id(cleaned)

            # 步骤 3: 生成嵌入向量（先查缓存）
            vec = self.cache.get(cleaned)
            if vec is None:
                vec = self.embedder.encode(cleaned)
                self.cache.put(cleaned, vec)

            # 步骤 4: 存储
            self.vector_db.insert(doc_id, cleaned, vec,
                                  metadata={"length": len(cleaned)})
            self.bm25.add(doc_id, cleaned)
            added += 1

        self._ingested_count += added
        return added

    def ask(self, question: str, stream: bool = False
            ) -> str | Iterator[str]:
        """
        问答接口：检索 + 重排序 + 答案生成。
        这是 RAG 的核心管道（Pipeline）。
        """
        # 步骤 1: 查询嵌入
        query_vec = self.embedder.encode(question)

        # 步骤 2: 混合检索（向量检索 + BM25 关键词检索）
        vec_results = self.vector_db.search(
            query_vec, top_k=self.config.top_k
        )
        bm25_results = self.bm25.search(
            question, top_k=self.config.top_k
        )

        # 步骤 3: 合并去重（集合去重）
        merged: dict[str, tuple[str, str, float]] = {}
        for doc_id, content, score in vec_results + bm25_results:
            if doc_id not in merged or score > merged[doc_id][2]:
                merged[doc_id] = (doc_id, content, score)

        candidates = list(merged.values())

        # 步骤 4: 重排序
        if self.config.use_rerank and candidates:
            candidates = self.reranker.rerank(
                question, candidates, top_k=self.config.top_k
            )

        # 步骤 5: 生成答案
        if stream:
            return self.answer_gen.generate(question, candidates)
        else:
            return self.answer_gen.generate_full(question, candidates)

    @property
    def stats(self) -> dict[str, int]:
        """系统统计信息"""
        return {
            "ingested_docs": self._ingested_count,
            "vector_count": self.vector_db.count(),
            "bm25_count": len(self.bm25._docs),
            "cache_size": len(self.cache._cache),
        }


# ── 7.10: 运行演示 ──
def run_demo() -> None:
    """运行迷你 RAG 系统演示"""

    # 银行知识库文档（模拟）
    bank_docs: list[str] = [
        "个人转账限额为每日5万元人民币，超过限额需要到柜面办理。",
        "企业网银转账限额为每日100万元人民币，可申请提高至500万元。",
        "跨境汇款需提供SWIFT代码、收款银行名称和账号。",
        "定期存款年化利率：1年期3.2%，3年期3.8%，5年期4.2%。",
        "信用卡还款日为每月25日，逾期将产生万分之五的日息。",
        "手机银行APP支持指纹和面部识别两种登录方式。",
        "理财产品购买起点金额为1万元，风险等级分为R1-R5。",
        "贷款年利率最低3.45%，需提供收入证明和征信报告。",
    ]

    # 创建知识库
    kb = KnowledgeBase()

    # 文档摄入
    count = kb.ingest_documents(bank_docs)
    print(f"\n📚 文档摄入完成，共 {count} 条")
    print(f"   系统统计: {kb.stats}")

    # 提问测试
    test_questions: list[str] = [
        "个人转账限额是多少？",
        "跨境汇款需要什么？",
        "定期存款利率是多少？",
    ]

    for i, q in enumerate(test_questions, 1):
        print(f"\n{'='*50}")
        print(f"❓ 问题 {i}: {q}")

        # 流式输出答案
        print("🤖 答案: ", end="")
        answer_stream = kb.ask(q, stream=True)
        if isinstance(answer_stream, Iterator):
            for chunk in answer_stream:
                print(chunk, end="", flush=True)
        print()

    print(f"\n{'='*50}")
    print(f"✅ 最终系统状态: {kb.stats}")


# 知识点 1.6: if __name__ == "__main__" 模式
if __name__ == "__main__":
    print("\n" + "█" * 70)
    print("█  Python 知识点汇总演示 (hz_bank_rag 项目)")
    print("█" * 70)

    # Part 1-6 已经通过模块级别代码自动执行
    # Part 7 显式运行
    run_demo()

    print("\n" + "█" * 70)
    print("█  演示完成！请对照 py_kb.md 文档理解各知识点")
    print("█" * 70)

    # 汇总知识点数量
    knowledge_points = {
        "类型标注 (Type Hints)": "41 次 (几乎所有文件)",
        "f-strings": "30 次",
        "OOP 类定义": "30 次",
        "列表推导式": "28 次",
        "异常处理 (try/except)": "26 次",
        "len() 内置函数": "25 次",
        "isinstance() 类型检查": "18 次",
        "min()/max() 内置函数": "18 次",
        "sorted() + lambda": "16 次",
        "字符串方法": "15 次",
        "@dataclass 数据类": "15 次",
        "上下文管理器 (with)": "14 次",
        "@staticmethod 静态方法": "14 次",
        "条件表达式": "14 次",
        "嵌套函数/闭包": "12 次",
        "json 模块": "10 次",
        "re 正则表达式": "10 次",
        "pathlib 模块": "10 次",
        "threading 线程安全": "8 次",
        "numpy 向量计算": "7 次",
        "generator (yield)": "6 次",
        "copy.deepcopy": "6 次",
        "hashlib 哈希": "6 次",
        "惰性导入 (try/except import)": "6 次",
        "concurrent.futures 线程池": "4 次",
        "abc 抽象基类": "2 次",
        "@lru_cache 装饰器": "2 次",
        "@contextmanager": "1 次",
    }

    print("\n📊 项目知识点频次统计:")
    for kp, freq in sorted(knowledge_points.items(),
                            key=lambda x: int(x[1].split()[0])
                                           if x[1][0].isdigit() else 0,
                            reverse=True):
        print(f"  • {kp}: {freq}")
