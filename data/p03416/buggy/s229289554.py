def is_palindromic(n):
    if str(n) == str(n)[::-1]:
        True
    else:
        False

A,B = map(int, input().split())
for i in range(A, B):
    if is_palindromic(i):
        print(i)