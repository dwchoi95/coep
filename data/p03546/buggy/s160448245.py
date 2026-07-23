def warshall_floyd(graph):
    num_v = len(graph)
    for i in range(num_v):
        for j in range(num_v):
            for k in range(num_v):
                graph[i][j] = min(graph[i][j], graph[i][k] + graph[k][j])
    return graph


h, w = map(int, input().split())
route = [[float("inf") for _ in range(10)] for _ in range(10)]

for i in range(10):
    S = list(map(int, input().split()))
    for j in range(10):
        route[i][j] = S[j]
graph = warshall_floyd(route)
result = 0
for i in range(h):
    A = list(map(int, input().split()))
    for a in A:
        if a == -1:
            continue
        else:
            result += graph[a][1]
print(result)

