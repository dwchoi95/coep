
import sys
S = input()
w = int(input())
x = 0

S_list = list(S)

sys.stdout.write(S_list[0])
while True:
    x = x + w
    if x >= len(S_list):
        break
    sys.stdout.write(S_list[x])