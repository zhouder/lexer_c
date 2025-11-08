#include <stdio.h>

int main()
{
    /* 这是一个注释 */
    char greeting[] = "Hello, C compiler!\n";
    char single_quote_char = '\'';
    char backslash_char = '\\';
    char tab_char = '\t';

    printf("%s", greeting);
    printf("单引号字符: %c\n", single_quote_char);
    printf("反斜杠字符: %c\n", backslash_char);
    printf("制表符: %c\n", tab_char);

    int a = 10;
    int b = 012t;
    int c = 0x5B;
    float pi = 3.14;

    if (a > 5)
    {
        return 0;
    }
    else
    {
        return 1;
    }
}
/*