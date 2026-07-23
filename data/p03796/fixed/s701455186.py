n = int(input())
ans = 1
dummy1,dummy2 = divmod(n,2)
for i in range(1,dummy1+1):
  ans *= i
  ans *= n+1-i
  ans = ans % (10**9+7)
if dummy2 == 1:
  ans = ((dummy1+1)*ans % (10**9+7))
print(ans)



