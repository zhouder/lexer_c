from .token import Token, TokenType
from .token import KEYWORDS, OPERATORS, DELIMITERS
from .matcher import (
    match_whitespace, match_identifier,
    match_float, match_hex_int, match_oct_int, match_dec_int,
    match_string_or_char, Trie, is_id_continue
)

class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.n = len(text)
        self.pos = 0
        self.line = 1
        self.col = 1
        
        self.trie = Trie()
        for op in OPERATORS:
            self.trie.add(op, "OP")
        for dl in DELIMITERS:
            self.trie.add(dl, "DL")

    # 推进
    def _advance(self, s: str):
        for ch in s:
            if ch == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1
        self.pos += len(s)

    # 提前看
    def _peek(self, k=1) -> str:
        return self.text[self.pos:self.pos+k]
    
    # 预处理
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
        # 块注释
        if self._peek(2) == "/*":
            end = self.text.find("*/", self.pos + 2)
            if end == -1:
                lex = self.text[self.pos:]
                tok = Token(TokenType.ERROR, lex, self.line, self.col)
                self._advance(lex)
                return tok 
            self._advance(self.text[self.pos:end+2])
            return True
        # 单行注释 
        if self._peek(2) == "//":
            j = self.text.find("\n", self.pos)
            if j == -1:
                self._advance(self.text[self.pos:])
            else:
                self._advance(self.text[self.pos:j])
            return True
        return False

    # 字符串/字符 ——
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

    # 主接口
    def next_token(self) -> Token:
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

        # 字符串/字符
        sc = self._try_string_or_char()
        if sc is not None:
            return sc

        # 试所有候选（最长匹配）
        candidates = []

        # 数字
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

        # 运算符/界符（Trie最长匹配）
        op_lex, op_tag = self.trie.match_longest(self.text, start)
        if op_lex is not None:
            ttype = TokenType.OP if op_tag == "OP" else TokenType.DL
            candidates.append((len(op_lex), ttype))

        # 标识符/关键字
        Lid = match_identifier(self.text, start)
        if Lid > 0:
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
                p = 1 
            return (l, p)

        L, ttype = max(candidates, key=pri)
        lex = self.text[self.pos:self.pos+L]

        # 以 0 开头的专门判定
        if ttype == TokenType.NUM10 and lex == '0':
            j = self.pos + 1
            if j < self.n and self.text[j] in ('x', 'X'):
                L16_try = match_hex_int(self.text, self.pos)
                if L16_try > 0:
                    L = L16_try
                    ttype = TokenType.NUM16
                    lex = self.text[self.pos:self.pos+L]
                else:
                    k = j + 1
                    while k < self.n and is_id_continue(self.text[k]):
                        k += 1
                    bad_lex = self.text[self.pos:k] if k > j + 1 else self.text[self.pos:j+1]
                    tok = Token(TokenType.ERROR, bad_lex, self.line, self.col)
                    self._advance(bad_lex)
                    return tok
            elif j < self.n and self.text[j] in '01234567':
                L8_try = match_oct_int(self.text, self.pos)
                if L8_try > 0:
                    L = L8_try
                    ttype = TokenType.NUM8
                    lex = self.text[self.pos:self.pos+L]
            elif j < self.n and self.text[j] in '89':
                k = j + 1
                while k < self.n and is_id_continue(self.text[k]):
                    k += 1
                bad_lex = self.text[self.pos:k]
                tok = Token(TokenType.ERROR, bad_lex, self.line, self.col)
                self._advance(bad_lex)
                return tok

        # 合法数字后后缀检查（012t、0x5BT、123abc ）
        if ttype in (TokenType.FLOAT, TokenType.NUM16, TokenType.NUM8, TokenType.NUM10):
            j = self.pos + L
            if j < self.n and is_id_continue(self.text[j]):
                k = j
                while k < self.n and is_id_continue(self.text[k]):
                    k += 1
                bad_lex = self.text[self.pos:k]
                tok = Token(TokenType.ERROR, bad_lex, self.line, self.col)
                self._advance(bad_lex)
                return tok

        # 若是 ID/RW，判定关键字
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
