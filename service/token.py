from dataclasses import dataclass
from enum import Enum, auto
import re

class TokenType(Enum):
    RW = auto()        # 关键字
    ID = auto()        # 标识符
    NUM10 = auto()     # 十进制数
    NUM8 = auto()      # 八进制数
    NUM16 = auto()     # 十六进制数
    FLOAT = auto()     # 浮点数
    CS_STR = auto()    # 字符串常量
    CS_CHAR = auto()   # 字符常量
    OP = auto()        # 运算符
    DL = auto()        # 界符
    CM = auto()        # 注释（不输出）
    ERROR = auto()     # 词法错误
    EOF = auto()       # 文件结束

TYPE_CN = {
    TokenType.RW: "关键字",
    TokenType.ID: "标识符",
    TokenType.NUM10: "十进制数",
    TokenType.NUM8: "八进制数",
    TokenType.NUM16: "十六进制数",
    TokenType.FLOAT: "浮点数",
    TokenType.CS_STR: "字符串常量",
    TokenType.CS_CHAR: "字符常量",
    TokenType.OP: "运算符",
    TokenType.DL: "界符",
    TokenType.CM: "注释",
    TokenType.ERROR: "错误",
}

@dataclass
class Token:
    type: TokenType
    lexeme: str
    line: int
    col: int

# 关键字(c89/c90标准)
KEYWORDS = {
    "auto","double","int","struct","break","else","long","switch","case","enum",
    "register","typedef","char","extern","return","union","const","float","short",
    "unsigned","continue","for","signed","void","default","goto","sizeof","volatile",
    "do","if","static","while","printf"
}

# 运算符（按长度降序确保最长匹配）
OPERATORS = [
    ">>=", "<<=", "==", "!=", ">=", "<=",
    "++", "--", "&&", "||",
    "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
    "<<", ">>", "->",
    ".", "+","-","*","/","%","&","|","^","~","!","=","<",">","?"
]

# 界符
DELIMITERS = ["...", "(", ")", "[", "]", "{", "}", ";", ",", ":"]
