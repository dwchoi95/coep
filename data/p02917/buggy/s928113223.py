n = int(input())
B = list(map(int,(input().split())))

list_A = [0]*n

list_A[0] = B[0]
list_A[n-1] = B[n-2]
for i in range(1,n-2):
    list_A[i] = min(B[i],B[i+1])

print(list_A)
print(sum(list_A))


