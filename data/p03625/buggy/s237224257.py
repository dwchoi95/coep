def main():
    n = int(input())
    a = [int(s) for s in input().split()]
    print(solve(a))

def solve(a):
    cands = set()
    s = set()
    for i in a:
        if i in s:
            cands.add(i)
        else:
            s.add(i)
    
    x = sorted(cands, reverse=True)
    if len(x) < 2:
        return 0
    
    return x[0] * x[1]

main()
