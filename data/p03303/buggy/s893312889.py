S = input()
w = int(input())

for index, s in enumerate(S):
    if index % w == 0:
        print(s)

