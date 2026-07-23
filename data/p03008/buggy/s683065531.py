def knapsack_123(values,weights,capacity):
    work = [0 for i in range(capacity+1)]
    for c in range(1, capacity+1):
        candidates = [val + work[c-weight]
                      for val,weight in zip(values,weights) if weight <= c]
        work[c] = max(candidates) if candidates != [] else 0
    return work[-1]
def sol(inp=input):
    n=int(inp())
    prices_a=list(map(int,inp().split()))+[1]
    prices_b=list(map(int,inp().split()))+[1]
    valA=knapsack_123(values=prices_b,weights=prices_a,capacity=n)
    valB=knapsack_123(values=prices_a,weights=prices_b,capacity=valA)
    return '{}'.format(valB)