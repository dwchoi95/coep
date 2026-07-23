def warshall_floyd(graph):
    num_v = len(graph)
    for k in range(num_v):
        for i in range(num_v):
            for j in range(num_v):
                graph[i][j] = min(graph[i][j], graph[i][k] + graph[k][j])
    return graph


h, w = map(int, input().split())
route = []

for i in range(10):
    S = list(map(int, input().split()))
    route.append(S)
graph = warshall_floyd(route)
result = 0
for i in range(h):
    A = list(map(int, input().split()))
    for a in A:
        if a != -1:
            result += graph[a][1]
print(result)

