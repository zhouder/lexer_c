# -*- coding: utf-8 -*-
from .token import Token, TokenType, KEYWORDS, OPERATORS, DELIMITERS
from .matcher import (
    match_whitespace, match_identifier,
    match_float, match_hex_int, match_oct_int, match_dec_int,
    match_string_or_char, match_base36_bare,
    Trie
)

class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.n = len(text)
        self.pos = 0
        self.line = 1
        self.col = 1

        # 运算符/界符 Trie（最长匹配）
        self.trie = Trie()
        for op in OPERATORS:
            self.trie.add(op, "OP")
        for dl in DELIMITERS:
            self.trie.add(dl, "DL")

        # —— 轻量上下文状态（为满足“无前后缀的 base36”需求）——
        self.in_decl = False         # 是否在声明语句中
        self.expect_ident = False    # 声明语句里是否正在期待变量名
        self.prev_token = None       # 上一个已输出的 token
        self.decl_is_int36 = False   # 本声明是否是 int36（直到遇到 ';' 结束）

    # 游标推进
    def _advance(self, s: str):
        for ch in s:
            if ch == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1
        self.pos += len(s)

    # 窥探
    def _peek(self, k=1) -> str:
        return self.text[self.pos:self.pos+k]

    # 跳过空白
    def _skip_ws(self) -> bool:
        n = match_whitespace(self.text, self.pos)
        if n > 0:
            self._advance(self.text[self.pos:self.pos+n])
            return True
        return False

    # 是否在行首（忽略前置空格与 Tab）
    def _at_line_start(self) -> bool:
        i = self.pos - 1
        while i >= 0 and self.text[i] in " \t":
            i -= 1
        return i < 0 or self.text[i] == "\n"

    # 跳过以 # 开头的整行预处理指令（支持反斜杠续行）
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

    # 跳过注释；未闭合块注释产生 ERROR
    def _skip_comments(self):
        # 块注释 /* ... */
        if self._peek(2) == "/*":
            end = self.text.find("*/", self.pos + 2)
            if end == -1:
                lex = self.text[self.pos:]
                tok = Token(TokenType.ERROR, lex, self.line, self.col)
                self._advance(lex)
                return tok
            self._advance(self.text[self.pos:end+2])
            return True
        # 单行注释 // ...
        if self._peek(2) == "//":
            j = self.text.find("\n", self.pos)
            if j == -1:
                self._advance(self.text[self.pos:])
            else:
                self._advance(self.text[self.pos:j])
            return True
        return False

    # 字符串/字符常量（含未闭合检测）
    def _try_string_or_char(self):
        length, is_string, is_error = match_string_or_char(self.text, self.pos)
        if length == 0:
            return None
        ttype = TokenType.CS_STR if is_string else TokenType.CS_CHAR
        lex = self.text[self.pos:self.pos+length]
        tok = Token(TokenType.ERROR if is_error else ttype, lex, self.line, self.col)
        self._advance(lex)
        self.prev_token = tok
        return tok

    # 当前是否处于“表达式位置”的粗略判断
    def _in_expr_context(self) -> bool:
        t = self.prev_token
        if t is None:
            return True
        # 这些分隔符之后通常进入表达式
        if t.type == TokenType.DL and t.lexeme in ("(", ",", "{", "[", ";"):
            return True
        # 运算符之后通常进入表达式
        if t.type == TokenType.OP and t.lexeme in (
            "=", "+", "-", "*", "/", "%", "&", "|", "^",
            "==", "!=", "<=", ">=", "<", ">", "&&", "||", "?", ":"
        ):
            return True
        # return 之后是表达式
        if t.type == TokenType.RW and t.lexeme == "return":
            return True
        # 声明语句中等号右侧是初始化表达式
        if self.in_decl and t.type == TokenType.OP and t.lexeme == "=":
            return True
        return False

    # 主接口
    def next_token(self) -> Token:
        # 统一跳过噪声
        progressed = True
        while progressed:
            progressed = False
            if self._skip_ws():
                progressed = True
            cm = self._skip_comments()
            if cm is True:
                progressed = True
            elif isinstance(cm, Token):
                return cm
            if self._skip_pp_line():
                progressed = True

        if self.pos >= self.n:
            return Token(TokenType.EOF, "", self.line, self.col)

        # 字符串/字符常量优先处理
        sc = self._try_string_or_char()
        if sc is not None:
            return sc

        # 收集候选（从同一 pos 开始）
        candidates = []
        start = self.pos

        # 数字（浮点 → base36 形状 → 16 → 8 → 10）
        Lf = match_float(self.text, start)
        if Lf > 0:
            candidates.append((Lf, TokenType.FLOAT))

        L36b = match_base36_bare(self.text, start)  # 裸写 base36（字母+数字）
        if L36b > 0:
            candidates.append((L36b, TokenType.NUM36))

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
            candidates.append((Lid, None))  # None 表示“尚未区分 ID/RW”

        # 无候选：报错并吃掉 1 个字符
        if not candidates:
            bad = self.text[self.pos]
            tok = Token(TokenType.ERROR, bad, self.line, self.col)
            self._advance(bad)
            self.prev_token = tok
            return tok

        # 最长匹配；等长时：数字 > OP/DL > ID/RW
        def pri(entry):
            l, tt = entry
            if tt in (TokenType.FLOAT, TokenType.NUM16, TokenType.NUM8, TokenType.NUM10, TokenType.NUM36):
                p = 3
            elif tt in (TokenType.OP, TokenType.DL):
                p = 2
            else:
                p = 1
            return (l, p)

        L, ttype = max(candidates, key=pri)
        lex = self.text[self.pos:self.pos+L]

        # ★ 关键字强制优先：只要是关键字词素，一律当关键字
        if lex in KEYWORDS:
            ttype = TokenType.RW
        else:
            # 若此前是“未定类型”则定为 ID
            if ttype is None:
                ttype = TokenType.ID

            # 在表达式位置，且形状为“字母+数字”的 base36：把 ID 改判为 NUM36
            if ttype == TokenType.ID:
                has_alpha = any(('a' <= c <= 'z') or ('A' <= c <= 'Z') for c in lex)
                has_digit = any('0' <= c <= '9' for c in lex)
                is_all_b36 = all(('0' <= c <= '9') or ('a' <= c <= 'z') or ('A' <= c <= 'Z') for c in lex)
                if has_alpha and has_digit and is_all_b36:
                    if (not self.expect_ident) and self._in_expr_context():
                        ttype = TokenType.NUM36

        # 在 int36 的声明初始化表达式中，纯数字也按 NUM36 处理
        if (self.in_decl and self.decl_is_int36
            and not self.expect_ident
            and self._in_expr_context()):
            if ttype in (TokenType.NUM10, TokenType.NUM8, TokenType.NUM16):
                ttype = TokenType.NUM36

        tok = Token(ttype, lex, self.line, self.col)
        self._advance(lex)

        # —— 维护声明/上下文状态 ——
        if tok.type == TokenType.RW and tok.lexeme == "int36":
            self.in_decl = True
            self.decl_is_int36 = True
            self.expect_ident = True
        elif tok.type == TokenType.DL and tok.lexeme == ";":
            self.in_decl = False
            self.decl_is_int36 = False
            self.expect_ident = False
        elif self.in_decl:
            if self.expect_ident and tok.type == TokenType.ID:
                self.expect_ident = False
            if tok.type == TokenType.DL and tok.lexeme == ",":
                self.expect_ident = True

        self.prev_token = tok
        return tok

    def tokenize(self):
        out = []
        while True:
            t = self.next_token()
            if t.type == TokenType.EOF:
                break
            out.append(t)
        return out