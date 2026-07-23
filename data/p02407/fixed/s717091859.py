n = input()
a = [int(x) for x in input().split()]
a.reverse()
print(" ".join(map(str, a)))