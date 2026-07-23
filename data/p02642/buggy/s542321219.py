import sys











stdin = sys.stdin
sys.setrecursionlimit(10 ** 7)
MIN = -10 ** 9
MOD = 10 ** 9 + 7
INF = float("inf")
IINF = 10 ** 18

def main():
    n = int(stdin.readline().rstrip())
    
    As = list(map(int, stdin.readline().rstrip().split()))
    
    
    
    
    As.sort(reverse=True)
    l = []
    l.append(As.pop())

    for i in range(1,n):
        t = As.pop()
        
        u = len(l)
        flag = False
        for j in range(u):
            if t%l[j] == 0:
                flag=True
        if flag==False:
            l.append(t)
    print(len(l))






main()
