n, q = [int(i) for i in input().split()]
s = input()
l_list = []
r_list = []
for i in range(q):
    l, r = [int(i) for i in input().split()]
    l_list.append(l)
    r_list.append(r)

ac_map = [0 for i in range(n+1)]
for i in range(1, n+1):
    if s[i-1:i+1] == "AC":
        ac_map[i] = ac_map[i-1] +1
    else:
        ac_map[i] = ac_map[i-1]
for i in range(q):
    ans = ac_map[r_list[i]-1] - ac_map[l_list[i]-1]
    print(ans)