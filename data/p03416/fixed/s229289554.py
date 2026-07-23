def is_palindromic(n):
    if str(n) == str(n)[::-1]:
        return True
    else:
        return False

res = 0
A,B = map(int, input().split())
for i in range(A, B+1):
    if is_palindromic(i):
       res += 1 
print(res)