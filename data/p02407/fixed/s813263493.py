input()
list1 = list(map(int, input().split()))
list1.reverse()
result=""
for i in range(0,len(list1)):
    result += str(list1[i])
    if len(list1)-1 == i:
        pass
    else:
        result += " "
print(result)