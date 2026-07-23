from collections import defaultdict
def main():
    N = int(input())
    A = [int(a) for a in input().split()]

    edge = defaultdict(int)

    for i in range(N):
        edge[A[i]] += 1

    edge = [ [k, v] for k, v in edge.items() if v >= 2 ]
    edge.sort(key = lambda x : x[0])

    if len(edge) >= 2 :
        if edge[-1][1] >= 4:
            print(max(edge[-1][0]**2, edge[-1][0]*edge[-2][0]))
        else:
            print(edge[-1][0]*edge[-2][0])
        
    elif len(edge) == 1:
        if edge[-1][1] >= 4:
            print(edge[-1][0]**2)
        else:
            print(0)
    else:
        print(0)

if __name__ == "__main__":
    main()