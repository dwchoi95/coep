
import sys
S = input()
w = int(input())
x = 0

S_list = list(S)

while True:
    sys.stdout.write(S_list[x])
    x = x + w
    if x > len(S_list) or x + w > len(S_list):
        break
