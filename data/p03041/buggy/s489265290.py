inputstr1 = input().split()
n = inputstr1[0]
k = inputstr1[1]
s = input()
s_list = list(s)
s_list[int(k) - 1] = s_list[int(k)-1].lower()
s = "".join(s_list)
print("S:"+s)
