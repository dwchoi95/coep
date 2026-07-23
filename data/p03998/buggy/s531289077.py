sa = list(input())
sb = list(input())
sc = list(input())

d = 'a'

while 1:
    if d == 'a':
        d = sa.pop(0)
        if sa == []:
            print('A')
            break
        d = sa[0]
    elif d == 'b':
        d = sb.pop(0)
        if sb == []:
            print('B')
            break
        d = sb[0]
    else:
        d = sc.pop(0)
        if sc == []:
            print('C')
            break
        d = sc[0]