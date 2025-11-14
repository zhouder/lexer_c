#include <stdio.h>

union Data{
    int intValue;
    char charValue[2];
};
void main(){
    union Data data;
    data.intValue=0x1234;//十六进制数
    data.charValue[0]=0101;//八进制
    data.charValue[1]=97;
    if(data.intValue%2==0)printf("%c",data.charValue[0]);
    else printf("%c",data.charValue[1]);
}