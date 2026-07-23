p,q = input().split()
q_ = int(q) -1 
n = input()
x = n.replace(n[q_], n[q_].lower(), 1)
print(x)