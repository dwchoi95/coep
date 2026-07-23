input()
list1 = list(map(int, input().split()))
list1.sort()
result=""
for i in range(0,len(list1)):
    result += str(list1[i])+" "
print(result)