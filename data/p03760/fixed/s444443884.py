odd = input()
even =input()
odd_list = []
even_list = []

for i in odd:
    odd_list.append(i)
for j in even:
    even_list.append(j)
even_list.append("")

for i in range(len(odd_list)):
    print(odd_list[i],end = "")
    print(even_list[i],end = "")
