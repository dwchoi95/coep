a,b = map(int,input(). split ())
if not a % 2 == 0 and not b % 2 == 0:
    print('NO')
elif a > 100 or b > 100:
    print('NO')
elif not isinstance(a, int) or not isinstance(b, int):
    print('NO')
elif 2 * a <= b <= 4 * a:
    print('YES')
else:
    print('NO')