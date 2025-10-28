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

def match_whitespace(text: str, pos: int) -> int:
    return match_while(text, pos, lambda ch: ch in WHITESPACE)

def match_identifier(text: str, pos: int) -> int:
    n = len(text)
    if pos >= n or not is_id_start(text[pos]):
        return 0
    i = pos + 1
    while i < n and is_id_continue(text[i]):
        i += 1
    return i - pos

def _match_exponent(text: str, pos: int) -> int:
    # [eE][+-]?[0-9]+
    n = len(text)
    i = pos
    if i < n and text[i] in ('e', 'E'):
        i += 1
        if i < n and text[i] in ('+', '-'):
            i += 1
        start_digits = i
        i += match_while(text, i, is_digit)
        if i > start_digits:
            return i - pos
    return 0

def match_float(text: str, pos: int) -> int:
    """
    支持三种形式（十进制）：
      1) digits '.' digits* [exp]      如 1.  1.0  1.0e+2
      2) '.' digits+ [exp]             如 .5  .5e3
      3) digits [exp]                  如 1e10
    返回匹配长度，失败则 0。
    """
    n = len(text)
    i = pos
    if i >= n:
        return 0
    best = 0

    # 1) digits '.' digits* [exp]
    j = i
    j += match_while(text, j, is_digit)
    if j > i and j < n and text[j] == '.':
        k = j + 1
        k += match_while(text, k, is_digit)
        k += _match_exponent(text, k)
        best = max(best, k - i)

    # 2) '.' digits+ [exp]
    if text[i] == '.' and i + 1 < n and is_digit(text[i+1]):
        j = i + 1 + match_while(text, i + 1, is_digit)
        j += _match_exponent(text, j)
        best = max(best, j - i)

    # 3) digits [exp]
    j = i + match_while(text, i, is_digit)
    if j > i:
        k = j + _match_exponent(text, j)
        if k > j:  # 必须有 exponent 才算 float
            best = max(best, k - i)

    return best

def match_hex_int(text: str, pos: int) -> int:
    # 0[xX][0-9a-fA-F]+
    n = len(text)
    if pos + 2 <= n and pos < n and text[pos] == '0' and pos + 1 < n and text[pos+1] in ('x','X'):
        j = pos + 2
        start = j
        j += match_while(text, j, is_hex)
        if j > start:
            return j - pos
    return 0

def match_oct_int(text: str, pos: int) -> int:
    # 0[0-7]+  （注意：单独的 "0" 不算八进制，归十进制）
    n = len(text)
    if pos < n and text[pos] == '0':
        j = pos + 1
        if j < n and is_oct(text[j]):
            j += match_while(text, j, is_oct)
            return j - pos
    return 0

def match_dec_int(text: str, pos: int) -> int:
    # 0 | [1-9][0-9]*
    n = len(text)
    if pos >= n or not is_digit(text[pos]):
        return 0
    if text[pos] == '0':
        return 1
    j = pos + 1
    j += match_while(text, j, is_digit)
    return j - pos

def match_string_or_char(text: str, pos: int) -> Tuple[int, bool, bool]:
    """
    返回 (len, is_string, is_error)
      - is_string=True 表示字符串，否则为字符常量
      - is_error=True 表示未闭合错误
    允许转义，不允许字符串跨行（C89）。
    """
    n = len(text)
    if pos >= n or text[pos] not in ("'", '"'):
        return (0, False, False)
    quote = text[pos]
    i = pos + 1
    while i < n:
        c = text[i]
        if c == '\\':
            i += 2  # 跳过转义对
            continue
        if c == quote:
            return (i - pos + 1, quote == '"', False)
        if c == '\n' and quote == '"':
            break
        i += 1
    # 未闭合
    # 至少消费开引号，避免死循环
    return (max(1, i - pos), quote == '"', True)

class TrieNode:
    __slots__ = ("children", "tag")
    def __init__(self):
        self.children = {}
        self.tag = None  # e.g. "OP" / "DL"

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def add(self, s: str, tag: str):
        node = self.root
        for ch in s:
            node = node.children.setdefault(ch, TrieNode())
        node.tag = tag

    def match_longest(self, text: str, pos: int) -> Tuple[Optional[str], Optional[str]]:
        node = self.root
        i, n = pos, len(text)
        last_tag = None
        last_i = pos
        while i < n:
            ch = text[i]
            if ch not in node.children:
                break
            node = node.children[ch]
            i += 1
            if node.tag is not None:
                last_tag = node.tag
                last_i = i
        if last_tag is None:
            return (None, None)
        return (text[pos:last_i], last_tag)
