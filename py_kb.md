# hz_bank_rag 项目 Python 知识点全览

> 本文档汇总项目中 **48 个 Python 文件** 涉及的全部知识点，
> 标记了每个知识点的 **使用频次（出现的文件数）**，
> 并配以 **可执行的数据案例**。
> 配套可执行代码见 `py_kb.py`。

---

## 目录

- [一、基础语法](#一基础语法)
  - [1.1 from \_\_future\_\_ import annotations](#11-from-__future__-import-annotations)
  - [1.2 类型标注 Type Hints](#12-类型标注-type-hints)
  - [1.3 f-strings 格式化字符串](#13-f-strings-格式化字符串)
  - [1.4 条件表达式（三元运算符）](#14-条件表达式三元运算符)
  - [1.5 异常处理 try/except](#15-异常处理-tryexcept)
  - [1.6 内置函数总览](#16-内置函数总览)
  - [1.7 字符串方法](#17-字符串方法)
- [二、数据结构与推导式](#二数据结构与推导式)
  - [2.1 列表推导式](#21-列表推导式)
  - [2.2 字典推导式](#22-字典推导式)
  - [2.3 sorted() + lambda](#23-sorted--lambda)
  - [2.4 元组与解包](#24-元组与解包)
  - [2.5 集合 set](#25-集合-set)
  - [2.6 dict 常用操作](#26-dict-常用操作)
- [三、函数进阶](#三函数进阶)
  - [3.1 lambda 表达式](#31-lambda-表达式)
  - [3.2 嵌套函数与闭包](#32-嵌套函数与闭包)
  - [3.3 装饰器 Decorator](#33-装饰器-decorator)
  - [3.4 生成器 Generator](#34-生成器-generator)
  - [3.5 上下文管理器 Context Manager](#35-上下文管理器-context-manager)
- [四、面向对象编程](#四面向对象编程)
  - [4.1 基本类定义](#41-基本类定义)
  - [4.2 继承与方法重写](#42-继承与方法重写)
  - [4.3 抽象基类 ABC](#43-抽象基类-abc)
  - [4.4 @staticmethod 静态方法](#44-staticmethod-静态方法)
  - [4.5 @dataclass 数据类](#45-dataclass-数据类)
  - [4.6 自定义异常类](#46-自定义异常类)
- [五、标准库与常用库](#五标准库与常用库)
  - [5.1 json 模块](#51-json-模块)
  - [5.2 re 正则表达式](#52-re-正则表达式)
  - [5.3 pathlib 路径操作](#53-pathlib-路径操作)
  - [5.4 hashlib 哈希](#54-hashlib-哈希)
  - [5.5 datetime 时间处理](#55-datetime-时间处理)
  - [5.6 threading 线程安全](#56-threading-线程安全)
  - [5.7 concurrent.futures 线程池](#57-concurrentfutures-线程池)
  - [5.8 numpy 数组操作](#58-numpy-数组操作)
- [六、设计模式](#六设计模式)
  - [6.1 LRU 缓存模式](#61-lru-缓存模式)
  - [6.2 模块级单例](#62-模块级单例)
  - [6.3 惰性导入](#63-惰性导入)
  - [6.4 copy.deepcopy 深拷贝](#64-copydeepcopy-深拷贝)
  - [6.5 if \_\_name\_\_ == "\_\_main\_\_"](#65-if-__name__--__main__)
- [七、频次总表](#七频次总表)

---

## 一、基础语法

### 1.1 from \_\_future\_\_ import annotations

| 属性 | 值 |
|------|-----|
| **频次** | **41 个文件**（几乎所有文件） |
| **作用** | 让类型标注变为"惰性字符串"，允许用 `X \| Y` 联合类型语法，允许前向引用 |
| **项目来源** | 每个 `.py` 文件的首行 |

**原理**：Python 3.10 之前不支持 `str | None` 语法，加了这行导入后，类型标注不会在运行时求值，而是被当作字符串处理，从而兼容新语法。

```python
# 必须放在文件最开头（docstring 之后、其他代码之前）
from __future__ import annotations

# 现在可以使用 str | None 语法（Python 3.7~3.9 也兼容）
def get_answer(query: str) -> str | None:
    if "转账" in query:
        return "每日限额5万元"
    return None

result: str | None = get_answer("转账限额")
print(result)  # 每日限额5万元
```

---

### 1.2 类型标注 Type Hints

| 属性 | 值 |
|------|-----|
| **频次** | **41 个文件** |
| **作用** | 为变量、函数参数、返回值添加类型说明 |
| **项目来源** | 几乎所有文件 |

**为什么用类型标注？**
- IDE 自动补全更智能
- `mypy` 等工具可以静态检查类型错误
- 代码可读性更高

```python
from typing import Any, Iterator, Callable

# 基础类型
user_name: str = "张三"
user_age: int = 30
balance: float = 15280.55
is_vip: bool = True

# 容器类型（Python 3.10+ 可用 list[X] 代替 List[X]）
questions: list[str] = ["转账限额", "如何开通网银"]
scores: dict[str, float] = {"转账限额": 0.92, "网银": 0.85}
embedding: tuple[str, float] = ("转账", 0.95)

# 可选类型：值可以是 str 或 None
maybe_answer: str | None = None

# 函数类型标注
def search(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    return [{"content": "结果", "score": 0.9}]

# Callable 类型：表示"可调用对象"
filter_func: Callable[[dict], bool] = lambda d: d["score"] > 0.5
```

**数据案例**：
```
输入: user_name = "张三", user_age = 30, balance = 15280.55
输出: 类型标注不影响运行，但 IDE 会提示 user_name 是 str 类型
```

---

### 1.3 f-strings 格式化字符串

| 属性 | 值 |
|------|-----|
| **频次** | **30 个文件** |
| **作用** | 在字符串中嵌入变量和表达式 |
| **项目来源** | 日志输出、错误消息、构造查询等 |

```python
query: str = "转账限额"
top_k: int = 5
score: float = 0.8732

# 基础用法
print(f"查询: {query}, 返回条数: {top_k}")
# 输出: 查询: 转账限额, 返回条数: 5

# 格式说明符 :.2f 表示保留两位小数
print(f"得分: {score:.2f}")
# 输出: 得分: 0.87

# :.0% 表示百分比格式
print(f"得分: {score:.0%}")
# 输出: 得分: 87%

# 调试模式 f"{var=}"（Python 3.8+）
print(f"{query=}, {top_k=}")
# 输出: query='转账限额', top_k=5

# 内嵌表达式
docs = [{"score": 0.92}, {"score": 0.78}]
print(f"平均得分: {sum(d['score'] for d in docs) / len(docs):.2f}")
# 输出: 平均得分: 0.85
```

---

### 1.4 条件表达式（三元运算符）

| 属性 | 值 |
|------|-----|
| **频次** | **14 个文件** |
| **作用** | 一行内完成条件判断赋值 |
| **语法** | `值_为真时 if 条件 else 值_为假时` |

```python
# Python 没有 ? : 三元运算符，用这种写法
original: str | None = "  银行转账  "
cleaned: str = original.strip() if original else "默认文本"
print(cleaned)  # 银行转账

# 项目中的典型用法
doc_id: str | None = None
final_id: str = doc_id if doc_id else f"doc_{id(object())}"
print(final_id)  # doc_140234567890（自动生成 ID）

# 嵌套三元（不推荐过度嵌套）
score: float = 0.45
level: str = "高" if score >= 0.8 else ("中" if score >= 0.5 else "低")
print(f"得分 {score} → 等级: {level}")  # 等级: 低
```

---

### 1.5 异常处理 try/except

| 属性 | 值 |
|------|-----|
| **频次** | **26 个文件** |
| **作用** | 捕获运行时错误，防止程序崩溃 |
| **变体** | `try/except`、`try/except/else/finally`、`try/finally`、`raise ... from exc` |

```python
import json

# 基础 try/except
try:
    result = 10 / 0
except ZeroDivisionError:
    print("错误：除数不能为零！")

# 多个 except 分支
try:
    data = '{"name": "张三"'  # 缺少右括号，无效 JSON
    parsed = json.loads(data)
except json.JSONDecodeError as e:
    print(f"JSON 解析错误: {e}")
except TypeError as e:
    print(f"类型错误: {e}")

# try/except/else/finally 完整结构
def safe_parse(text: str) -> dict | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
    else:
        print("解析成功")     # 仅在没有异常时执行
    finally:
        print("解析结束")     # 无论是否异常都执行

# 异常链（from exc）— 保留原始异常信息
try:
    json.loads("{invalid}")
except json.JSONDecodeError as exc:
    try:
        raise ValueError(f"配置格式错误") from exc
    except ValueError as ve:
        print(f"异常链: {ve}")  # 配置格式错误
```

**数据案例**：
```
输入: json.loads('{"name": "张三"')   # 缺少 }
异常: JSONDecodeError: Expecting ',' delimiter
捕获: 输出 "JSON 解析错误: ..."
程序: 继续运行，不会崩溃
```

---

### 1.6 内置函数总览

| 函数 | 频次 | 用途 |
|------|------|------|
| `len()` | 25 个文件 | 获取长度 |
| `min()` / `max()` | 18 个文件 | 最小/最大值 |
| `isinstance()` | 18 个文件 | 运行时类型检查 |
| `enumerate()` | 15 个文件 | 带索引遍历 |
| `round()` | 11 个文件 | 四舍五入 |
| `any()` / `all()` | 11 个文件 | 逻辑判断 |
| `range()` | 10 个文件 | 生成整数序列 |
| `sorted()` | 16 个文件 | 排序 |
| `int()` / `float()` / `str()` / `bool()` | 13 个文件 | 类型转换 |

```python
numbers: list[int] = [85, 92, 78, 96, 88, 73, 95]

# len() — 获取长度
print(len(numbers))           # 7

# min() / max() — 最值
print(min(numbers))           # 73
print(max(numbers))           # 96

# round() — 四舍五入
print(round(3.14159, 2))      # 3.14

# any() — 是否存在满足条件的元素
print(any(n >= 95 for n in numbers))   # True

# all() — 是否全部满足条件
print(all(n >= 60 for n in numbers))   # True

# enumerate() — 带索引遍历
for idx, val in enumerate(numbers[:3]):
    print(f"  [{idx}] {val}")
# 输出: [0] 85, [1] 92, [2] 78

# isinstance() — 类型检查
print(isinstance(42, int))              # True
print(isinstance("hello", str))         # True
print(isinstance(3.14, (int, float)))   # True

# 类型转换
print(int("42"))       # 42
print(float("3.14"))   # 3.14
print(str(100))        # "100"
print(bool(0))         # False
print(bool(1))         # True
```

---

### 1.7 字符串方法

| 属性 | 值 |
|------|-----|
| **频次** | **15 个文件** |
| **常用方法** | `.strip()`, `.lower()`, `.replace()`, `.split()`, `.join()`, `.count()`, `.find()` |

```python
text: str = "  银行个人转账业务介绍 v2.0\n"

# .strip() — 去除首尾空白
print(text.strip())           # "银行个人转账业务介绍 v2.0"

# .lower() / .upper() — 大小写转换
print("Hello".lower())        # "hello"

# .replace() — 替换子串
print(text.replace("v2.0", "v3.0"))  # "  银行个人转账业务介绍 v3.0\n"

# .split() — 分割字符串
print("a,b,c".split(","))     # ['a', 'b', 'c']

# .join() — 连接字符串
print(" | ".join(["A", "B", "C"]))   # "A | B | C"

# .count() — 计数
print(text.count("银行"))     # 1

# .find() — 查找位置
print(text.find("银行"))      # 2（索引位置）

# .startswith() / .endswith() — 前后缀判断
print(text.startswith("  "))  # True

# 切片
s = "银行个人转账业务介绍"
print(s[:2])     # "银行"
print(s[2:4])    # "个人"
print(s[::-1])   # "绍介务业账转人个行银"（反转）
```

---

## 二、数据结构与推导式

### 2.1 列表推导式

| 属性 | 值 |
|------|-----|
| **频次** | **28 个文件**（最常见的 Pythonic 写法） |
| **语法** | `[表达式 for 变量 in 可迭代对象 if 条件]` |

```python
documents = [
    {"content": "个人转账限额为每日5万元", "score": 0.92},
    {"content": "企业网银转账限额为每日100万元", "score": 0.78},
    {"content": "跨境汇款需提供SWIFT代码", "score": 0.65},
    {"content": "定期存款利率为年化3.5%", "score": 0.45},
]

# 基础推导式：提取得分 >= 0.7 的内容
high_scores = [doc["content"] for doc in documents if doc["score"] >= 0.7]
print(high_scores)
# ['个人转账限额为每日5万元', '企业网银转账限额为每日100万元']

# 带转换的推导式
labels = [f"{d['content'][:10]}... ({d['score']:.0%})" for d in documents]
print(labels)
# ['个人转账限额为每日5万元... (92%)', '企业网银转账限额为... (78%)', ...]

# 展平嵌套列表
nested = [[1, 2, 3], [4, 5], [6, 7, 8]]
flat = [x for row in nested for x in row]
print(flat)  # [1, 2, 3, 4, 5, 6, 7, 8]

# 等价的 for 循环写法（对比理解）
flat_old = []
for row in nested:
    for x in row:
        flat_old.append(x)
```

---

### 2.2 字典推导式

| 属性 | 值 |
|------|-----|
| **频次** | **10+ 个文件** |
| **语法** | `{key_expr: value_expr for 变量 in 可迭代对象 if 条件}` |

```python
documents = [
    {"content": "转账限额", "score": 0.92},
    {"content": "理财产品", "score": 0.78},
    {"content": "跨境汇款", "score": 0.65},
]

# 构建 内容→得分 映射
score_map = {doc["content"]: doc["score"] for doc in documents}
print(score_map)
# {'转账限额': 0.92, '理财产品': 0.78, '跨境汇款': 0.65}

# 反转映射（得分→内容）
reverse_map = {v: k for k, v in score_map.items()}
print(reverse_map)
# {0.92: '转账限额', 0.78: '理财产品', 0.65: '跨境汇款'}

# 带条件的字典推导式
high_map = {k: v for k, v in score_map.items() if v >= 0.7}
print(high_map)
# {'转账限额': 0.92, '理财产品': 0.78}
```

---

### 2.3 sorted() + lambda

| 属性 | 值 |
|------|-----|
| **频次** | **16 个文件** |
| **作用** | 对可迭代对象排序，`key` 参数指定排序依据 |

```python
documents = [
    {"content": "转账限额", "score": 0.92},
    {"content": "理财产品", "score": 0.78},
    {"content": "跨境汇款", "score": 0.65},
]

# 按得分降序排列
by_score = sorted(documents, key=lambda d: d["score"], reverse=True)
for doc in by_score:
    print(f"  {doc['score']:.2f}: {doc['content']}")
# 0.92: 转账限额
# 0.78: 理财产品
# 0.65: 跨境汇款

# 按字符串长度排序
words = ["跨境汇款", "个人", "转账", "SWIFT代码", "网银"]
by_len = sorted(words, key=lambda w: len(w), reverse=True)
print(by_len)
# ['SWIFT代码', '跨境汇款', '个人', '转账', '网银']

# 按多字段排序（先按 score 降序，再按 content 升序）
data = [{"name": "A", "score": 0.9}, {"name": "B", "score": 0.9}, {"name": "C", "score": 0.8}]
result = sorted(data, key=lambda d: (-d["score"], d["name"]))
print(result)
# [{'name': 'A', 'score': 0.9}, {'name': 'B', 'score': 0.9}, {'name': 'C', 'score': 0.8}]
```

---

### 2.4 元组与解包

| 属性 | 值 |
|------|-----|
| **频次** | **5 个文件** |
| **作用** | 不可变序列、多返回值、变量交换 |

```python
# 元组定义
doc_tuple: tuple[str, float] = ("转账限额文档", 0.92)
name, score = doc_tuple   # 解包
print(f"{name}: {score}")  # 转账限额文档: 0.92

# 变量交换
a, b = 10, 20
a, b = b, a
print(f"a={a}, b={b}")    # a=20, b=10

# 星号解包
first, *rest = [0.95, 0.88, 0.76, 0.65]
print(f"first={first}, rest={rest}")  # first=0.95, rest=[0.88, 0.76, 0.65]

# 多返回值
def get_stats(scores: list[float]) -> tuple[int, float, float]:
    return len(scores), sum(scores)/len(scores), max(scores)

count, avg, top = get_stats([0.92, 0.78, 0.65])
print(f"数量={count}, 平均={avg:.2f}, 最高={top:.2f}")
# 数量=3, 平均=0.78, 最高=0.92
```

---

### 2.5 集合 set

| 属性 | 值 |
|------|-----|
| **频次** | **4 个文件** |
| **作用** | 无序不重复、集合运算（并交差） |

```python
doc_a = {"转账", "限额", "网银", "个人"}
doc_b = {"转账", "SWIFT", "跨境", "企业"}

# 并集
print(doc_a | doc_b)     # {'转账', '限额', '网银', '个人', 'SWIFT', '跨境', '企业'}

# 交集（共同主题）
print(doc_a & doc_b)     # {'转账'}

# 差集（A 有 B 没有）
print(doc_a - doc_b)     # {'限额', '网银', '个人'}

# 对称差（只在一个集合中出现的）
print(doc_a ^ doc_b)     # {'限额', '网银', '个人', 'SWIFT', '跨境', '企业'}

# 成员检查
print("转账" in doc_a)   # True

# 去重
raw = ["转账", "限额", "转账", "网银", "限额"]
unique = list(set(raw))
print(unique)             # ['网银', '限额', '转账']（顺序可能不同）
```

---

### 2.6 dict 常用操作

| 属性 | 值 |
|------|-----|
| **频次** | `.get()` 16 个文件, `.pop()` 5 个文件 |
| **作用** | 键值对映射、配置管理、数据传递 |

```python
config = {"model": "deepseek-v3", "temperature": "0.7"}

# .get() — 安全获取，避免 KeyError
print(config.get("model"))                # "deepseek-v3"
print(config.get("unknown", "N/A"))       # "N/A"（默认值）

# .pop() — 取出并删除
temp = config.pop("temperature", "0.5")
print(f"取出: {temp}, 剩余: {config}")
# 取出: 0.7, 剩余: {'model': 'deepseek-v3'}

# .items() — 遍历键值对
for key, value in config.items():
    print(f"  {key} = {value}")

# dict 合并（Python 3.9+）
merged = config | {"max_tokens": "4096", "top_p": "0.9"}
print(merged)
# {'model': 'deepseek-v3', 'max_tokens': '4096', 'top_p': '0.9'}

# .update() — 原地更新
config.update({"model": "gpt-4", "verbose": True})
print(config)
# {'model': 'gpt-4', 'verbose': True}
```

---

## 三、函数进阶

### 3.1 lambda 表达式

| 属性 | 值 |
|------|-----|
| **频次** | **10 个文件** |
| **作用** | 定义匿名小函数，常作为 `sorted()` / `map()` / `filter()` 的回调 |
| **语法** | `lambda 参数: 返回值` |

```python
# lambda 定义
multiply = lambda x, y: x * y
print(multiply(3, 5))  # 15

# 用于 filter 筛选
products = ["转账", "理财", "存款", "贷款", "汇款"]
long = list(filter(lambda p: len(p) >= 2, products))
print(long)  # ['转账', '理财', '存款', '贷款', '汇款']

# 用于 map 映射
lengths = list(map(lambda p: len(p), products))
print(lengths)  # [2, 2, 2, 2, 2]

# 用于 sorted 排序
docs = [{"name": "A", "score": 0.7}, {"name": "B", "score": 0.9}]
sorted_docs = sorted(docs, key=lambda d: d["score"], reverse=True)
print(sorted_docs)  # [{'name': 'B', 'score': 0.9}, {'name': 'A', 'score': 0.7}]
```

---

### 3.2 嵌套函数与闭包

| 属性 | 值 |
|------|-----|
| **频次** | **12 个文件** |
| **作用** | 内层函数"记住"外层变量，常用于工厂函数、延迟执行 |
| **项目来源** | `main.py` 中的 `_invalidate_caches`、`event_generator` 等 |

```python
# 闭包工厂：根据阈值创建过滤函数
def create_filter(min_score: float):
    """外层函数定义阈值"""
    def filter_func(doc: dict) -> bool:
        # 内层函数"捕获"外层的 min_score → 闭包
        return doc["score"] >= min_score
    return filter_func

high_pass = create_filter(0.85)
low_pass = create_filter(0.50)

docs = [
    {"content": "转账", "score": 0.92},
    {"content": "存款", "score": 0.45},
    {"content": "理财", "score": 0.78},
]

print([d["content"] for d in docs if high_pass(d)])  # ['转账']
print([d["content"] for d in docs if low_pass(d)])    # ['转账', '理财']

# 闭包计数器
def make_counter():
    count = 0
    def increment():
        nonlocal count  # 声明使用外层变量
        count += 1
        return count
    return increment

counter = make_counter()
print(counter(), counter(), counter())  # 1 2 3
```

---

### 3.3 装饰器 Decorator

| 属性 | 值 |
|------|-----|
| **频次** | `@staticmethod` 14 次, `@lru_cache` 2 次, `@abstractmethod` 2 次 |
| **作用** | 不修改原函数代码，给函数"包裹"额外功能 |

```python
import time
from functools import lru_cache

# 自定义装饰器：计时
def timer(func):
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"  {func.__name__} 耗时: {elapsed:.4f}s")
        return result
    return wrapper

@timer
def slow_add(a: int, b: int) -> int:
    time.sleep(0.1)
    return a + b

print(slow_add(3, 5))
# slow_add 耗时: 0.1003s
# 8

# lru_cache 装饰器：缓存函数结果
call_count = 0

@lru_cache(maxsize=128)
def expensive_square(x: int) -> int:
    global call_count
    call_count += 1
    time.sleep(0.05)
    return x * x

print(expensive_square(5))   # 25 (call_count=1, 实际计算)
print(expensive_square(5))   # 25 (call_count=1, 命中缓存！不重新计算)
print(f"实际调用次数: {call_count}")  # 1
```

---

### 3.4 生成器 Generator

| 属性 | 值 |
|------|-----|
| **频次** | **6 个文件** |
| **作用** | 惰性计算，逐个产出值而非一次性返回列表 |
| **项目来源** | SSE 流式输出、大文件读取、数据管道 |

```python
from typing import Iterator

# 生成器函数（用 yield 代替 return）
def generate_scores(count: int) -> Iterator[float]:
    """逐个产出随机得分"""
    import random
    random.seed(42)
    for i in range(count):
        yield round(random.uniform(0.5, 1.0), 3)

gen = generate_scores(5)
print(type(gen))       # <class 'generator'>
print(next(gen))       # 手动获取第一个值
for score in gen:      # 遍历剩余值
    print(score)

# 生成器表达式（类似列表推导式，用圆括号）
score_gen = (d["score"] for d in [{"score": 0.9}, {"score": 0.5}] if d["score"] > 0.6)
print(list(score_gen))  # [0.9]

# 项目实际用途：SSE 流式输出
def sse_stream(answer: str) -> Iterator[str]:
    for i, char in enumerate(answer):
        yield f'data: {{"index": {i}, "text": "{char}"}}\n\n'
    yield "data: [DONE]\n\n"

for event in sse_stream("你好"):
    print(event.strip())
# data: {"index": 0, "text": "你"}
# data: {"index": 1, "text": "好"}
# data: [DONE]
```

---

### 3.5 上下文管理器 Context Manager

| 属性 | 值 |
|------|-----|
| **频次** | **14 个文件** |
| **作用** | 自动管理资源的获取和释放 |
| **项目来源** | 线程池、线程锁、HTTP 客户端、文件、临时文件等 |

```python
from contextlib import contextmanager

# 方式一：@contextmanager 装饰器（项目 metadata_store.py 使用）
@contextmanager
def db_connection(path: str):
    print(f"  连接到: {path}")
    conn = {"path": path, "data": {}}
    try:
        yield conn          # 资源交给 with 块
        print("  提交事务")
    except Exception as e:
        print(f"  回滚: {e}")
        raise
    finally:
        print("  关闭连接")

with db_connection("knowledge.db") as conn:
    conn["data"]["key"] = "value"
    print(f"  操作: {conn['data']}")
# 连接到: knowledge.db
# 操作: {'key': 'value'}
# 提交事务
# 关闭连接

# 方式二：定义 __enter__ / __exit__ 方法
class Timer:
    def __enter__(self):
        import time
        self.start = time.perf_counter()
        return self
    def __exit__(self, *args):
        import time
        self.elapsed = time.perf_counter() - self.start
        print(f"  耗时: {self.elapsed:.4f}s")

with Timer():
    sum(range(100000))
# 耗时: 0.0032s
```

---

## 四、面向对象编程

### 4.1 基本类定义

| 属性 | 值 |
|------|-----|
| **频次** | **30 个文件** |
| **核心概念** | 类属性、实例属性、实例方法、`__init__`、`__repr__`、`__eq__` |

```python
class BankDocument:
    # 类属性：所有实例共享
    source_type: str = "bank_knowledge"

    def __init__(self, content: str, score: float = 0.0, doc_id: str | None = None):
        # 实例属性：每个实例独有
        self.content = content
        self.score = score
        self.doc_id = doc_id or f"doc_{id(self)}"

    def summary(self, max_len: int = 30) -> str:
        """实例方法"""
        text = self.content.strip()
        return text[:max_len] + ("..." if len(text) > max_len else "")

    def is_relevant(self, threshold: float = 0.6) -> bool:
        return self.score >= threshold

    def __repr__(self) -> str:
        return f"BankDocument(id={self.doc_id}, score={self.score:.2f})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BankDocument):
            return NotImplemented
        return self.doc_id == other.doc_id

# 使用
doc = BankDocument("个人转账限额为每日5万元", score=0.92, doc_id="D001")
print(doc)                    # BankDocument(id=D001, score=0.92)
print(doc.summary(10))        # 个人转账限额为每日5...
print(doc.is_relevant())      # True
print(BankDocument.source_type)  # bank_knowledge
```

---

### 4.2 继承与方法重写

| 属性 | 值 |
|------|-----|
| **频次** | **6+ 个文件** |
| **核心概念** | 父类/子类、`super()`、方法重写、`isinstance()` |

```python
class ScoredDocument(BankDocument):
    """子类：在父类基础上增加 category 属性"""
    def __init__(self, content: str, score: float = 0.0,
                 doc_id: str | None = None, category: str = "通用"):
        super().__init__(content, score, doc_id)  # 调用父类构造函数
        self.category = category

    def summary(self, max_len: int = 30) -> str:
        """重写父类方法"""
        base = super().summary(max_len)  # 调用父类实现
        return f"[{self.category}] {base}"

doc = ScoredDocument("定期存款利率", score=0.72, category="存款业务")
print(doc.summary())                        # [存款业务] 定期存款利率
print(isinstance(doc, BankDocument))        # True（子类实例也是父类类型）
print(isinstance(doc, ScoredDocument))      # True
```

---

### 4.3 抽象基类 ABC

| 属性 | 值 |
|------|-----|
| **频次** | **2 个文件**（`vector_store.py`） |
| **作用** | 定义接口规范，强制子类实现指定方法 |

```python
from abc import ABC, abstractmethod

class BaseVectorStore(ABC):
    """抽象基类：定义向量存储的接口"""

    @abstractmethod
    def search(self, query: list[float], top_k: int) -> list[tuple[str, float]]:
        ...  # 子类必须实现

    @abstractmethod
    def add(self, doc_id: str, vector: list[float]) -> None:
        ...  # 子类必须实现

    def count(self) -> int:  # 非抽象方法可以有默认实现
        return 0

class InMemoryVectorStore(BaseVectorStore):
    """具体实现：内存向量存储"""
    def __init__(self):
        self._store: dict[str, list[float]] = {}

    def search(self, query: list[float], top_k: int) -> list[tuple[str, float]]:
        results = []
        for doc_id, vec in self._store.items():
            sim = sum(a * b for a, b in zip(query, vec))
            results.append((doc_id, round(sim, 4)))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def add(self, doc_id: str, vector: list[float]) -> None:
        self._store[doc_id] = vector

    def count(self) -> int:
        return len(self._store)

store = InMemoryVectorStore()
store.add("D001", [0.1, 0.5, 0.3])
store.add("D002", [0.8, 0.2, 0.1])
print(store.search([0.12, 0.48, 0.31], top_k=1))
# [('D001', 0.321)]（D001 更相似）
```

---

### 4.4 @staticmethod 静态方法

| 属性 | 值 |
|------|-----|
| **频次** | **14 个文件** |
| **特点** | 不依赖 `self` 或 `cls`，逻辑上归入类中 |

```python
import hashlib
import re

class TextUtils:
    @staticmethod
    def compute_md5(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    @staticmethod
    def clean_text(text: str) -> str:
        return re.sub(r'\s+', ' ', text.strip())

    @staticmethod
    def is_valid(text: str, min_len: int = 2) -> bool:
        return len(text) >= min_len

# 调用：不需要创建实例
print(TextUtils.compute_md5("银行"))        # 28 位十六进制字符串
print(TextUtils.clean_text("  hello  "))    # "hello"
print(TextUtils.is_valid("hi"))             # True
print(TextUtils.is_valid("h"))              # False
```

---

### 4.5 @dataclass 数据类

| 属性 | 值 |
|------|-----|
| **频次** | **15 个文件**（项目最重要的数据建模工具） |
| **作用** | 自动生成 `__init__`、`__repr__`、`__eq__` 等方法 |
| **进阶** | `frozen=True`（不可变）、`field(default_factory=...)`（可变默认值） |

```python
from dataclasses import dataclass, field, asdict

@dataclass
class RetrievedDocument:
    doc_id: str                              # 必填字段
    content: str                             # 必填字段
    score: float                             # 必填字段
    source: str = "unknown"                  # 带默认值
    keywords: list[str] = field(default_factory=list)  # 可变默认值必须用 field

doc = RetrievedDocument("D001", "转账限额", 0.92, keywords=["转账"])
print(doc)           # 自动生成的 repr
print(asdict(doc))   # 转为字典
# {'doc_id': 'D001', 'content': '转账限额', 'score': 0.92, 'source': 'unknown', 'keywords': ['转账']}

# frozen=True: 不可变（类似元组）
@dataclass(frozen=True)
class Config:
    model: str = "deepseek-v3"
    temperature: float = 0.7

cfg = Config()
# cfg.temperature = 0.9  # 报错！frozen 实例不可修改
```

**注意**：列表/字典等可变类型作为 dataclass 默认值时，**必须**用 `field(default_factory=list)`，不能直接写 `= []`，否则所有实例会共享同一个列表。

---

### 4.6 自定义异常类

| 属性 | 值 |
|------|-----|
| **频次** | **2 个文件** |
| **作用** | 定义业务特定的异常类型 |

```python
class BankRAGException(Exception):
    """基类异常"""
    def __init__(self, message: str, error_code: str = "UNKNOWN"):
        super().__init__(message)
        self.error_code = error_code

class DocumentNotFoundError(BankRAGException):
    """文档未找到"""
    def __init__(self, doc_id: str):
        super().__init__(f"文档 {doc_id} 未找到", "DOC_NOT_FOUND")

try:
    raise DocumentNotFoundError("D999")
except DocumentNotFoundError as e:
    print(f"异常: {e}, 错误码: {e.error_code}")
# 异常: 文档 D999 未找到, 错误码: DOC_NOT_FOUND
```

---

## 五、标准库与常用库

### 5.1 json 模块

| 属性 | 值 |
|------|-----|
| **频次** | **10 个文件** |
| **核心函数** | `json.dumps()` 序列化, `json.loads()` 反序列化 |

```python
import json

# Python dict → JSON 字符串
data = {"bank": "杭州银行", "products": ["转账", "理财"], "count": 120}
json_str = json.dumps(data, ensure_ascii=False, indent=2)
print(json_str)
# {
#   "bank": "杭州银行",
#   "products": ["转账", "理财"],
#   "count": 120
# }

# JSON 字符串 → Python dict
parsed = json.loads('{"query": "转账", "top_k": 5}')
print(parsed)           # {'query': '转账', 'top_k': 5}
print(parsed["query"])  # 转账

# 错误处理
try:
    json.loads("{invalid}")
except json.JSONDecodeError as e:
    print(f"解析失败: {e}")
```

---

### 5.2 re 正则表达式

| 属性 | 值 |
|------|-----|
| **频次** | **10 个文件** |
| **核心函数** | `re.findall()`, `re.sub()`, `re.split()` |

```python
import re

text = "联系电话：0571-88888888 业务编号：BK-2024-00123 金额：￥15,280.00"

# findall — 提取所有匹配
phones = re.findall(r'\d{3,4}-\d{7,8}', text)
print(phones)  # ['0571-88888888']

biz_ids = re.findall(r'[A-Z]+-\d{4}-\d+', text)
print(biz_ids)  # ['BK-2024-00123']

amounts = re.findall(r'￥[\d,]+\.\d{2}', text)
print(amounts)  # ['￥15,280.00']

# sub — 替换
cleaned = re.sub(r'\s+', ' ', "  hello   world  ").strip()
print(cleaned)  # "hello world"

# split — 分割
parts = re.split(r'[。！？\n]+', "你好。请问转账？限额多少！")
print(parts)  # ['你好', '请问转账', '限额多少', '']
```

---

### 5.3 pathlib 路径操作

| 属性 | 值 |
|------|-----|
| **频次** | **10 个文件** |
| **优势** | 比 `os.path` 更直观，用 `/` 拼接路径 |

```python
from pathlib import Path

p = Path(__file__).resolve()
print(f"文件名: {p.name}")          # py_kb.py
print(f"后缀: {p.suffix}")          # .py
print(f"父目录: {p.parent}")        # /path/to/...

# 路径拼接
data_dir = p.parent / "data" / "documents"
print(f"数据目录: {data_dir}")

# 检查路径
print(f"是文件: {p.is_file()}")
print(f"存在: {data_dir.exists()}")

# 创建目录
new_dir = p.parent / "temp_test_dir"
new_dir.mkdir(parents=True, exist_ok=True)
print(f"创建目录: {new_dir}")
new_dir.rmdir()  # 清理
```

---

### 5.4 hashlib 哈希

| 属性 | 值 |
|------|-----|
| **频次** | **6 个文件** |
| **算法** | MD5（缓存键）、SHA256（内容指纹）、SHA1（Redis key） |

```python
import hashlib

content = "个人转账限额为每日5万元"

# MD5 — 128 位（32 位十六进制字符串）
md5 = hashlib.md5(content.encode("utf-8")).hexdigest()
print(f"MD5: {md5}")     # 如: a1b2c3d4e5f6...

# SHA256 — 256 位（64 位十六进制字符串，更安全）
sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
print(f"SHA256: {sha256[:16]}...")  # 只显示前 16 位

# SHA1 — 160 位（40 位十六进制字符串）
sha1 = hashlib.sha1(content.encode("utf-8")).hexdigest()
print(f"SHA1: {sha1}")

# 雪崩效应：改一个字，哈希完全不同
similar = "个人转账限额为每日4万元"
print(f"原文 MD5:   {md5}")
print(f"相似 MD5:   {hashlib.md5(similar.encode()).hexdigest()}")
print(f"是否相同: {md5 == hashlib.md5(similar.encode()).hexdigest()}")  # False
```

---

### 5.5 datetime 时间处理

| 属性 | 值 |
|------|-----|
| **频次** | **3 个文件** |
| **核心类** | `datetime`, `timezone`, `timedelta` |

```python
from datetime import datetime, timezone, timedelta

# 当前 UTC 时间
now_utc = datetime.now(timezone.utc)
print(f"UTC: {now_utc.isoformat()}")

# 北京时间（UTC+8）
beijing_tz = timezone(timedelta(hours=8))
now_bj = datetime.now(beijing_tz)
print(f"北京: {now_bj.strftime('%Y-%m-%d %H:%M:%S')}")

# 解析时间字符串
dt = datetime.strptime("2024-03-15 10:30:00", "%Y-%m-%d %H:%M:%S")
print(f"解析: {dt}")

# 时间差计算
start = datetime.now(timezone.utc)
# ... 某些操作 ...
end = datetime.now(timezone.utc)
elapsed = (end - start).total_seconds()
print(f"耗时: {elapsed:.3f} 秒")

# 时间戳
ts = 1710500000.0
dt_from_ts = datetime.fromtimestamp(ts, tz=timezone.utc)
print(f"时间戳 {ts} → {dt_from_ts.isoformat()}")
```

---

### 5.6 threading 线程安全

| 属性 | 值 |
|------|-----|
| **频次** | **8 个文件** |
| **核心工具** | `threading.Lock`（互斥锁）、`threading.BoundedSemaphore`（信号量） |

```python
import threading

class ThreadSafeCounter:
    """线程安全计数器"""
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()  # 互斥锁

    def increment(self) -> int:
        with self._lock:  # 加锁保护共享状态
            self._value += 1
            return self._value

    @property
    def value(self) -> int:
        with self._lock:
            return self._value

counter = ThreadSafeCounter()
for _ in range(5):
    counter.increment()
print(f"计数器: {counter.value}")  # 5
```

**为什么需要锁？** 如果多个线程同时执行 `self._value += 1`，可能出现竞态条件（race condition），导致计数不准确。`Lock` 确保同一时间只有一个线程能修改 `_value`。

---

### 5.7 concurrent.futures 线程池

| 属性 | 值 |
|------|-----|
| **频次** | **4 个文件** |
| **核心类** | `ThreadPoolExecutor`, `as_completed` |

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def fetch_embedding(text: str) -> tuple[str, float]:
    """模拟耗时 IO 操作"""
    time.sleep(0.03)
    return (text, len(text) * 0.1)

texts = ["转账限额", "理财产品", "定期存款", "跨境汇款"]

# 使用 with 管理线程池生命周期
with ThreadPoolExecutor(max_workers=3) as executor:
    # 提交任务
    futures = {executor.submit(fetch_embedding, t): t for t in texts}
    # 按完成顺序获取结果
    for future in as_completed(futures):
        text, score = future.result()
        print(f"  完成: '{text}' → {score:.1f}")
```

---

### 5.8 numpy 数组操作

| 属性 | 值 |
|------|-----|
| **频次** | **7 个文件** |
| **核心用途** | 向量计算、余弦相似度、嵌入存储 |

```python
import numpy as np

# 创建向量
emb1 = np.array([0.1, 0.5, 0.3], dtype=np.float32)
emb2 = np.array([0.8, 0.2, 0.1], dtype=np.float32)
emb3 = np.array([0.12, 0.48, 0.31], dtype=np.float32)

# 点积
print(f"点积 1·2: {np.dot(emb1, emb2):.4f}")  # 0.2100
print(f"点积 1·3: {np.dot(emb1, emb3):.4f}")  # 0.3730

# 余弦相似度 = 点积 / (||A|| × ||B||)
cos_12 = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
cos_13 = np.dot(emb1, emb3) / (np.linalg.norm(emb1) * np.linalg.norm(emb3))
print(f"余弦 1-2: {cos_12:.4f}")  # 0.7889
print(f"余弦 1-3: {cos_13:.4f}")  # 0.9978 → emb3 与 emb1 更相似

# 批量操作
all_embs = np.asarray([emb1, emb2, emb3])
norms = np.linalg.norm(all_embs, axis=1)
print(f"范数: {norms}")
```

---

## 六、设计模式

### 6.1 LRU 缓存模式

| 属性 | 值 |
|------|-----|
| **频次** | **2 个文件**（`embedding_cache.py`, `query_cache.py`） |
| **核心** | `OrderedDict` + `move_to_end` + `popitem(last=False)` |

```python
from collections import OrderedDict
import threading

class SimpleLRUCache:
    def __init__(self, max_size: int = 5):
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()

    def get(self, key: str) -> str | None:
        with self._lock:
            if key not in self._cache:
                return None
            self._cache.move_to_end(key)  # 标记为最近使用
            return self._cache[key]

    def put(self, key: str, value: str) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            if len(self._cache) > self._max_size:
                old_key, _ = self._cache.popitem(last=False)  # 淘汰最旧
                print(f"  淘汰: {old_key}")

cache = SimpleLRUCache(max_size=3)
cache.put("A", "转账"); cache.put("B", "理财"); cache.put("C", "存款")
cache.get("A")  # 访问 A，A 变为最近使用
cache.put("D", "贷款")  # B 最久未使用，被淘汰
# 淘汰: B
```

---

### 6.2 模块级单例

| 属性 | 值 |
|------|-----|
| **频次** | **3 个文件** |
| **实现方式** | 模块级变量 或 `__new__` 双重检查 |

```python
# 方式一：模块级变量（项目中最常用）
# 在 config.py 中：settings = Settings()
# 整个进程只有一个实例

# 方式二：__new__ 双重检查
class AppConfig:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_done = False
        return cls._instance

    def __init__(self):
        if self._init_done:
            return
        self.model = "deepseek-v3"
        self._init_done = True

a = AppConfig()
b = AppConfig()
print(a is b)  # True — 同一个对象
```

---

### 6.3 惰性导入

| 属性 | 值 |
|------|-----|
| **频次** | **6 个文件** |
| **作用** | 处理可选依赖，不安装时不报错 |

```python
# 项目中的典型模式
optional_libs = {}

try:
    import redis          # 可选依赖
    optional_libs["redis"] = True
except ImportError:
    optional_libs["redis"] = False

try:
    import pandas         # 仅评估模块使用
    optional_libs["pandas"] = True
except ImportError:
    optional_libs["pandas"] = False

try:
    import jieba          # 中文分词
    optional_libs["jieba"] = True
except ImportError:
    optional_libs["jieba"] = False

print(optional_libs)  # {'redis': False, 'pandas': False, 'jieba': False}
```

---

### 6.4 copy.deepcopy 深拷贝

| 属性 | 值 |
|------|-----|
| **频次** | **6 个文件** |
| **作用** | 防止修改引用类型参数污染原始数据 |

```python
import copy

original = {"model": "deepseek-v3", "params": {"temperature": 0.7, "top_p": 0.9}}

# 浅拷贝：修改嵌套 dict 仍会影响原对象
shallow = original.copy()
shallow["params"]["temperature"] = 0.1
print(f"浅拷贝后 original: {original['params']}")
# {'temperature': 0.1, 'top_p': 0.9} ← 被污染了！

# 恢复
original["params"]["temperature"] = 0.7

# 深拷贝：完全独立
deep = copy.deepcopy(original)
deep["params"]["temperature"] = 0.1
print(f"深拷贝后 original: {original['params']}")
# {'temperature': 0.7, 'top_p': 0.9} ← 不受影响
```

---

### 6.5 if \_\_name\_\_ == "\_\_main\_\_"

| 属性 | 值 |
|------|-----|
| **频次** | **4 个文件** |
| **作用** | 区分"直接运行"和"作为模块导入" |

```python
# my_module.py
def helper():
    return "我是工具函数"

if __name__ == "__main__":
    # 直接运行 python my_module.py → 执行
    # import my_module → 不执行
    print("直接运行模式")
    print(helper())
```

---

## 七、频次总表

以下按出现文件数降序排列，统计来自项目全部 48 个 Python 文件：

| 排名 | 知识点 | 频次 | 说明 |
|------|--------|------|------|
| 1 | 类型标注 Type Hints | 41 | 几乎每个文件都在用 |
| 2 | `from __future__ import annotations` | 41 | PEP 604 联合类型兼容 |
| 3 | OOP 类定义 | 30 | 项目核心组织形式 |
| 4 | f-strings | 30 | 格式化字符串 |
| 5 | 列表推导式 | 28 | 最常见的 Pythonic 写法 |
| 6 | 异常处理 try/except | 26 | 防御性编程 |
| 7 | `len()` 内置函数 | 25 | 获取长度 |
| 8 | `isinstance()` 类型检查 | 18 | 运行时类型判断 |
| 9 | `min()`/`max()` 内置函数 | 18 | 最值计算 |
| 10 | `sorted()` + lambda | 16 | 排序 |
| 11 | `dict.get()` 方法 | 16 | 安全取值 |
| 12 | `enumerate()` 内置函数 | 15 | 带索引遍历 |
| 13 | `@dataclass` 数据类 | 15 | 数据建模 |
| 14 | 字符串方法 | 15 | `.strip()` `.replace()` 等 |
| 15 | `@staticmethod` 装饰器 | 14 | 无状态工具方法 |
| 16 | 上下文管理器 (with) | 14 | 资源管理 |
| 17 | 条件表达式 | 14 | 三元运算 |
| 18 | 类型转换 | 13 | `int()` `float()` 等 |
| 19 | 嵌套函数/闭包 | 12 | 工厂函数、延迟执行 |
| 20 | `round()` 内置函数 | 11 | 四舍五入 |
| 21 | `any()`/`all()` 内置函数 | 11 | 逻辑判断 |
| 22 | json 模块 | 10 | 序列化/反序列化 |
| 23 | re 正则表达式 | 10 | 模式匹配 |
| 24 | pathlib 模块 | 10 | 路径操作 |
| 25 | lambda 表达式 | 10 | 匿名函数 |
| 26 | `range()` 内置函数 | 10 | 整数序列 |
| 27 | `hasattr()`/`getattr()` 反射 | 9 | 动态属性访问 |
| 28 | threading 线程安全 | 8 | Lock / Semaphore |
| 29 | time 模块 | 8 | 计时、时间戳 |
| 30 | numpy 向量计算 | 7 | 嵌入、相似度 |
| 31 | generator (yield) | 6 | 惰性计算、流式输出 |
| 32 | copy.deepcopy | 6 | 深拷贝 |
| 33 | hashlib 哈希 | 6 | MD5/SHA256/SHA1 |
| 34 | 惰性导入 | 6 | 可选依赖处理 |
| 35 | 元组解包 | 5 | 多返回值 |
| 36 | concurrent.futures | 4 | 线程池并发 |
| 37 | 集合操作 | 4 | 并交差去重 |
| 38 | Pydantic BaseModel | 4 | API 数据验证 |
| 39 | `if __name__ == "__main__"` | 4 | 入口判断 |
| 40 | abc 抽象基类 | 2 | 接口定义 |
| 41 | `@lru_cache` | 2 | 结果缓存 |
| 42 | `@contextmanager` | 1 | 自定义上下文 |
| 43 | datetime 模块 | 3 | 时间处理 |
| 44 | sqlite3 模块 | 3 | 数据库操作 |
| 45 | FastAPI | 4 | Web 框架 |
| 46 | Pydantic-settings | 2 | 配置管理 |

---

> **学习建议**：先运行 `python py_kb.py` 看完整输出，再对照本文档逐个知识点理解。
> 每个知识点的频次反映了它在实际项目中的重要程度，频次越高的越需要优先掌握。
