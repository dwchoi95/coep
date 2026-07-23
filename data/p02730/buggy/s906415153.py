import math
a= input()
length=math.floor(len(a)/2)
def kaibun(p):
    length_p=math.floor(len(p)/2)
    total_p = 0
    for i in range(length_p):
        if p[i] is not p[-1*i -1]:
            return False
            break
        else:
            total_p += 1
        if total_p == length_p:
            return True
if kaibun(a):
    if kaibun(a[:length+1]):
        print('Yes')
    elif length==1:
        print('Yes')
    else:
        print('No')
else:
    print('No')

