from collections import Counter
import sys

sys.setrecursionlimit(10 ** 6)
int1 = lambda x: int(x) - 1
p2D = lambda x: print(*x, sep="\n")
def MI(): return map(int, sys.stdin.readline().split())
def LI(): return list(map(int, sys.stdin.readline().split()))
def LLI(rows_number): return [LI() for _ in range(rows_number)]

def main():
    n=int(input())
    aa=LI()
    cnt=Counter(aa)
    mx=-1
    for a,an in sorted(cnt.items(),reverse=True):
        if an>3 and mx==-1:
            print(a*a)
            break
        elif an>1:
            if mx==-1:mx=a
            else:
                print(mx*a)
                break
    else:
        print(0)



main()