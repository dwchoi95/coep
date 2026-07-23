odd = input()
even =input()
odd_list = []
even_list = []

for (a,b) in zip(odd,even):
    odd_list.append(a)
    even_list.append(b)
even_list.append("")

for i in range(len(odd_list)):
    print(odd_list[i],end = "")
    print(even_list[i],end = "")
