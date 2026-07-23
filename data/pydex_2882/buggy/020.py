# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
1st = input().split(',')
a=1st[0]
b=1st[1]
def prime_chk(num):
    if num > 1:
        for i in range(2,num):
            if (num % i) == 0:
                return False
                break
        else:
            return True
    else:
        return False
def decrypter(a,b):
    x,y = a[::-1], b[::-1]
    x,y=int(x),int(y)
    px,py = prime_chk(x),prime_chk(y)
    if px and py:
        answer = x+y
    elif py or py:
        answer = int(a)+int(b)
    else:
        answer = int(a)*int(b)
    return answer
print(decrypter(a,b))