a = list(map(int, input().split()))
a = list(a[i] for i in range(len(a)-1,-1,-1))
print(" ".join(map(str, a)))