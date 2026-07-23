i1 = input()
i1 = i1.split()
types = int(i1[0])
select = int(i1[1])

i2 = input()
i2 = [int(n) for n in i2.split()]
i2.sort(reverse=True)

summary = sum(i2)
threshold = summary / (select * 4)




if i2[select-1] < threshold :
    print("No")
else:
    print("Yes")
