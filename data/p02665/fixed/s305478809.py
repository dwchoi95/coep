n = int(input())+1
a = list(map(int, input().split()))
m_node = [1]*n
node = 0
total = 0

if n == 1:
    if a[0] != 1:
        print("-1", end="")
        exit()
    else:
        print("1", end="")
        exit()

for i in range(1, n):
    m_node[i] = (m_node[i-1] - a[i-1])*2
    if m_node[i] <= 0:
        print("-1", end="")
        exit()
for i in reversed(range(n)):
    if a[i] > m_node[i]:
        print("-1", end="")
        exit()
    node = min((node+a[i]), m_node[i])
    total += node

print(total, end="")
