import collections

N = int(input())
A = list(map(int,input().split()))

nums = []
roll = [-1,0,1]

for i in range(N):
  for j in range(3):
    d = A[i] + roll[j]
    nums.append(d)

num = collections.Counter(nums).most_common()
print(num[0][1])