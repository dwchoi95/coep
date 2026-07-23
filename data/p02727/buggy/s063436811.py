import sys
input = sys.stdin.readline
from itertools import chain

def readlines(*abc):
    for n in abc:
        yield list(map(int, input().split()))[:n]

def main():
    x, y, a, b, c = map(int, input().split())
    apples = sorted(chain(*readlines(a,b,c)), reverse=True)
    print(sum(apples[:x+y]))


main()


