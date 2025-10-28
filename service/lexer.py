from .token import Token, TokenType
from .token import KEYWORDS, OPERATORS, DELIMITERS
from .matcher import (
    match_whitespace, match_identifier,
    match_float, match_hex_int, match_oct_int, match_dec_int,
    match_string_or_char, Trie
)

class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.n = len(text)
        self.pos = 0
        self.line = 1
        self.col = 1
        # 预构建 OP/DL 的 Trie 以实现最长匹配
        self.trie = Trie()
        for op in OPERATORS:
            self.trie.add(op, "OP")
        for dl in DELIMITERS:
            self.trie.add(dl, "DL")

    # —— 位移与窥探 ——
    def _advance(self, s: str):
        for ch in s:
            if ch == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1
        self.pos += len(s)

    def _peek(self, k=1) -> str:
        return self.text[self.pos:self.pos+k]

    # —— 忽略：空白 / 注释 / 预处理行 ——
    def _skip_ws(self) -> bool:
        n = match_whitespace(self.text, self.pos)
        if n > 0:
            self._advance(self.text[self.pos:self.pos+n])
            return True
        return False

    def _at_line_start(self) -> bool:
        i = self.pos - 1
        while i >= 0 and self.text[i] in " \t":
            i -= 1
        return i < 0 or self.text[i] == "\n"

    def _skip_pp_line(self) -> bool:
        if self._peek(1) == "#" and self._at_line_start():
            j = self.pos
            while j < self.n:
                if self.text[j] == "\\" and j + 1 < self.n and self.text[j+1] == "\n":
                    j += 2
                    continue
                if self.text[j] == "\n":
                    break
                j += 1
            self._advance(self.text[self.pos:j])
            return True
        return False

    def _skip_comments(self):
        # 块注释 /* ... */
        if self._peek(2) == "/*":
            end = self.text.find("*/", self.pos + 2)
            if end == -1:
                lex = self.text[self.pos:]
                tok = Token(TokenType.ERROR, lex, self.line, self.col)
                self._advance(lex)
                return tok  # 未闭合，交给上层返回错误
            self._advance(self.text[self.pos:end+2])
            return True
        # 单行注释 // ...（兼容）
        if self._peek(2) == "//":
            j = self.text.find("\n", self.pos)
            if j == -1:
                self._advance(self.text[self.pos:])
            else:
                self._advance(self.text[self.pos:j])
            return True
        return False

    # —— 字符串/字符（含未闭合错误） ——
    def _try_string_or_char(self):
        length, is_string, is_error = match_string_or_char(self.text, self.pos)
        if length == 0:
            return None
        ttype = TokenType.CS_STR if is_string else TokenType.CS_CHAR
        lex = self.text[self.pos:self.pos+length]
        if is_error:
            tok = Token(TokenType.ERROR, lex, self.line, self.col)
        else:
            tok = Token(ttype, lex, self.line, self.col)
        self._advance(lex)
        return tok

    # —— 主接口：生成下一个 token ——
    def next_token(self) -> Token:
        # 统一跳过：空白 / 注释 / 预处理行
        progressed = True
        while progressed:
            progressed = False
            if self._skip_ws():
                progressed = True
            cm = self._skip_comments()
            if cm is True:
                progressed = True
            elif isinstance(cm, Token):   # 未闭合块注释 -> 错误
                return cm
            if self._skip_pp_line():
                progressed = True

        if self.pos >= self.n:
            return Token(TokenType.EOF, "", self.line, self.col)

        # 1) 字符串/字符
        sc = self._try_string_or_char()
        if sc is not None:
            return sc

        # 2) 试所有候选（按最长匹配；同长按优先级）
        candidates = []

        # 数字：优先尝试浮点（避免把 "1." 拆成 1 和 "."）
        start = self.pos
        Lf = match_float(self.text, start)
        if Lf > 0:
            candidates.append((Lf, TokenType.FLOAT))

        L16 = match_hex_int(self.text, start)
        if L16 > 0:
            candidates.append((L16, TokenType.NUM16))

        L8 = match_oct_int(self.text, start)
        if L8 > 0:
            candidates.append((L8, TokenType.NUM8))

        L10 = match_dec_int(self.text, start)
        if L10 > 0:
            candidates.append((L10, TokenType.NUM10))

        # 运算符/界符（Trie 最长匹配）
        op_lex, op_tag = self.trie.match_longest(self.text, start)
        if op_lex is not None:
            ttype = TokenType.OP if op_tag == "OP" else TokenType.DL
            candidates.append((len(op_lex), ttype))

        # 标识符/关键字
        Lid = match_identifier(self.text, start)
        if Lid > 0:
            # 暂时先当作 ID，真正确定类型时再看关键字集合
            candidates.append((Lid, None))

        if not candidates:
            bad = self.text[self.pos]
            tok = Token(TokenType.ERROR, bad, self.line, self.col)
            self._advance(bad)
            return tok

        # 取最长；若等长，优先级：数字 > OP/DL > ID/RW
        def pri(entry):
            l, tt = entry
            if tt in (TokenType.FLOAT, TokenType.NUM16, TokenType.NUM8, TokenType.NUM10):
                p = 3
            elif tt in (TokenType.OP, TokenType.DL):
                p = 2
            else:
                p = 1  # ID/RW
            return (l, p)

        L, ttype = max(candidates, key=pri)
        lex = self.text[self.pos:self.pos+L]

        # 若是 ID/RW，二次判定关键字
        if ttype is None:
            ttype = TokenType.RW if lex in KEYWORDS else TokenType.ID

        tok = Token(ttype, lex, self.line, self.col)
        self._advance(lex)
        return tok

    def tokenize(self):
        out = []
        while True:
            t = self.next_token()
            if t.type == TokenType.EOF:
                break
            out.append(t)
        return out
