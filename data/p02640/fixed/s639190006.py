a,b = map(int,input(). split ())
if not b % 2 == 0:
    print('No')
elif a > 100:
    print('No')
elif b > 100:
    print('No')
elif a < 1:
    print('No')
elif b < 1:
    print('No')
elif not isinstance(a, int):
    print('No')
elif not isinstance(b, int):
    print('No')
elif 2 * a <= b <= 4 * a:
    print('Yes')
else:
    print('No')