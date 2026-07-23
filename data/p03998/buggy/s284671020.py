from collections import deque
import sys


def input(): return sys.stdin.readline().strip()
def I(): return int(input())
def LI(): return list(map(int, input().split()))
def IR(n): return [I() for i in range(n)]
def LIR(n): return [LI() for i in range(n)]
def SR(n): return [S() for i in range(n)]
def S(): return input()
def LS(): return input().split()


sa = deque(list(S()))
sb = deque(list(S()))
sc = deque(list(S()))

turn = 'a'
while True:
    if len(sa) == 0 or len(sb) == 0 or len(sc) == 0:
        break
    if turn == 'a':
        turn = sa.popleft()
    if turn == 'b':
        turn = sb.popleft()
    if turn == 'c':
        turn = sc.popleft()
print(turn.upper())
