n = int(input())
temp = 1
     
for i in range(1,n+1):
  temp = temp * i
  temp = temp % ((10**9)+7)
     
print(temp % (10 ** 9 + 7))
