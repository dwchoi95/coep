sa = list(input())
sb = list(input())
sc = list(input())

d = 'a'
cnta = 0
cntb = 0
cntc = 0
A = len(sa)
B = len(sb)
C = len(sc)

while 1:
    if d == 'a':
        cnta += 1
        if cnta == A+1:
            print('A')
            break
        d = sa.pop(0)
    elif d == 'b':
        cntb += 1
        if cntb == B+1:
            print('B')
            break
        d = sb.pop(0)
    else:
        cntc += 1
        if cntc == C+1:
            print('C')
            break
        d = sc.pop(0)