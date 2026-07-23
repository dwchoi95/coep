if __name__=="__main__":
    l = list(input())
    N = len(l)
    results = [1]
    for i in range(0,N-1):
        if not l[i]==l[i+1]:
            results.append(max(i+1,N-i-1))
    print(min(results))