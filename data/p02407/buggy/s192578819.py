N = int(input())
Arr = list(map(int, input().split()))
for i in range(N):
 if i==N-1:
  print(Arr[0])
 else:
  print(str(Arr[N-1-i]) + " ")