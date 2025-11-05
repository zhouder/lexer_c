from typing import Optional, Tuple

WHITESPACE = set(" \t\r\n\f\v")

# 识别单个字符
def is_alpha(c: str) -> bool:
    return ('a' <= c <= 'z') or ('A' <= c <= 'Z')

def is_digit(c: str) -> bool:
    return '0' <= c <= '9'

def is_hex(c: str) -> bool:
    return is_digit(c) or ('a' <= c <= 'f') or ('A' <= c <= 'F')

def is_oct(c: str) -> bool:
    return '0' <= c <= '7'

def is_id_start(c: str) -> bool:
    return is_alpha(c) or c == '_'

def is_id_continue(c: str) -> bool:
    return is_id_start(c) or is_digit(c)

def match_while(text: str, pos: int, pred) -> int:
    i, n = pos, len(text)
    while i < n and pred(text[i]):
        i += 1
    return i - pos

# 跳过空白符
def match_whitespace(text: str, pos: int) -> int:
    return match_while(text, pos, lambda ch: ch in WHITESPACE)

# 匹配标识符
def match_identifier(text: str, pos: int) -> int:
    n = len(text)
    if pos >= n or not is_id_start(text[pos]):
        return 0
    i = pos + 1
    while i < n and is_id_continue(text[i]):
        i += 1
    return i - pos

# 匹配浮点数（十进制）
def match_float(text: str, pos: int) -> int:
    n = len(text)
    i = pos

    if i >= n or not is_digit(text[i]):
        return 0

    i += match_while(text, i, is_digit)

    if i >= n or text[i] != '.':
        return 0
    i += 1

    if i >= n or not is_digit(text[i]):
        return 0
    i += match_while(text, i, is_digit)

    if i < n and text[i] in ('e', 'E'):
        j = i + 1
        if j < n and text[j] in ('+', '-'):
            j += 1
        k = j + match_while(text, j, is_digit)
        if k == j:
            return 0
        i = k

    return i - pos

# 匹配16进制
def match_hex_int(text: str, pos: int) -> int:
    n = len(text)
    if pos + 2 <= n and pos < n and text[pos] == '0' and pos + 1 < n and text[pos+1] in ('x','X'):
        j = pos + 2
        start = j
        j += match_while(text, j, is_hex)
        if j > start:
            return j - pos
    return 0

# 匹配8进制
def match_oct_int(text: str, pos: int) -> int:
    n = len(text)
    if pos < n and text[pos] == '0':
        j = pos + 1
        if j < n and is_oct(text[j]):
            j += match_while(text, j, is_oct)
            return j - pos
    return 0

# 匹配10进制
def match_dec_int(text: str, pos: int) -> int:
    n = len(text)
    if pos >= n or not is_digit(text[pos]):
        return 0
    if text[pos] == '0':
        return 1
    j = pos + 1
    j += match_while(text, j, is_digit)
    return j - pos

# 字符串或字符常量（支持转义，字符串不跨行；返回 (length, is_string, is_error)）
def match_string_or_char(text: str, pos: int):
    n = len(text)
    if pos >= n or text[pos] not in ("'", '"'):
        return (0, False, False)

    quote = text[pos]
    i = pos + 1
    while i < n:
        c = text[i]
        if c == "\\":           # 跳过转义对，例如 \" \n \t \\
            i += 2
            continue
        if c == quote:            # 成功闭合
            return (i - pos + 1, quote == '"', False)
        if c == "\n" and quote == '"':  # C89 字符串不跨行
            break
        i += 1

    # 未闭合：至少消费开引号，避免死循环
    return (max(1, i - pos), quote == '"', True)

# —— 新增：base36 裸写形状 —— 
def is_base36(c: str) -> bool:
    return ('0' <= c <= '9') or ('a' <= c <= 'z') or ('A' <= c <= 'Z')

def match_base36_bare(text: str, pos: int) -> int:
    """
    裸写 36 进制形态：[A-Za-z0-9]+ 且 “至少 1 字母 + 至少 1 数字”。
    这里只做形状识别；是否采用由 lexer 的上下文来决定。
    """
    n = len(text)
    i = pos
    if i >= n or not is_base36(text[i]):
        return 0
    has_alpha = False
    has_digit = False
    while i < n and is_base36(text[i]):
        ch = text[i]
        if '0' <= ch <= '9':
            has_digit = True
        else:
            has_alpha = True
        i += 1
    if has_alpha and has_digit:
        return i - pos
    return 0
# —— 新增结束 —— 

# 运算符/界符的最长匹配（使用嵌套 dict 实现的简单 Trie）
class Trie:
    def __init__(self):
        self.root = {"next": {}}

    def add(self, s: str, tag: str):
        node = self.root
        for ch in s:
            node = node["next"].setdefault(ch, {"next": {}})
        node["end"] = True
        node["tag"] = tag

    def match_longest(self, text: str, pos: int):
        node = self.root
        i, n = pos, len(text)
        last_hit = None

        while i < n:
            ch = text[i]
            nxt = node["next"].get(ch)
            if nxt is None:
                break
            node = nxt
            i += 1
            if node.get("end"):
                last_hit = (i, node.get("tag"))

        if last_hit is None:
            return (None, None)
        end_i, tag = last_hit
        return (text[pos:end_i], tag)