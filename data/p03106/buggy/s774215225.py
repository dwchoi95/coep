a = list(map(int, input().split()))
num1 = a[0]
num2 = a[1]
list1 = []
list2 = []
max = a[2]
for i in range(1, num1 + 1):
  if num1 % i == 0:
    list1.append(i)
    
for i in range(1, num2 + 1):
  if num2 % i == 0:
    list2.append(i)

list3 = list(set(list1) & set(list2))
list3.sort()

print(list3[max -1])