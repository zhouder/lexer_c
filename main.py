import sys
from collections import defaultdict
from service.lexer import Lexer
from service.token import TYPE_CN

def main(path: str):
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    tokens = Lexer(src).tokenize()

    by_line = defaultdict(list)
    for t in tokens:
        by_line[t.line].append(t)

    max_line = src.count("\n") + 1
    for ln in range(1, max_line + 1):
        if ln not in by_line:
            continue
        for t in by_line[ln]:
            print(f"({t.line}, {TYPE_CN.get(t.type, t.type.name)}, {t.lexeme})")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法：python main.py test.c")
        sys.exit(1)
    main(sys.argv[1])
