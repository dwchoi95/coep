import sys
input = sys.stdin.readline
from itertools import chain

def readlines(*xy):
    for n in xy:
        yield sorted(map(int, input().split()), reverse=True)[:n]

def main():
    x, y, a, b, c = map(int, input().split())
    apples = sorted(chain(*readlines(x,y,c)), reverse=True)
    print(sum(apples[:x+y]))


main()


