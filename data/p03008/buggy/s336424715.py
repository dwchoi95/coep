def knapsack_123(values,weights,capacity):
    work = [0 for i in range(capacity+1)]
    for v,w in zip(values,weights):
        for c in range(w, capacity+1):
            work[c]=max(work[c],work[c-w]+v)
    return work[-1]
def sol(inp=input):
    n=int(inp())
    prices_a=list(map(int,inp().split()))+[1]
    prices_b=list(map(int,inp().split()))+[1]
    
    valA=knapsack_123(values=prices_b,weights=prices_a,capacity=n)
    print(valA)
    valB=knapsack_123(values=prices_a,weights=prices_b,capacity=valA)
    return '{}'.format(valB)
print(sol())