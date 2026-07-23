n = input()

ran = list(range(1,10))
product = [x*y for x in ran for y in ran]
print("Yes") if n in product else print("No")