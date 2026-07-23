s = input()
lst = s.split()

ex1 = int(lst[0])
ex2 = int(lst[1])
ret = "no"

for i in range(ex1+1):
    if 4 * (ex1 - i) + 2 * i == ex2:
        ret= "yes"

print(ret)
