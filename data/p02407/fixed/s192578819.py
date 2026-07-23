N = int(input())
Arr = list(map(int, input().split()))
for i in range(N-1):
 print("{} ".format(Arr[N-1-i]), end="")
print(Arr[0])