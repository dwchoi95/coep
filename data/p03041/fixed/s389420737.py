p,q = input().split()
q_ = int(q) 
n = input()

print(n[:q_-1] + n[q_-1].lower() + n[q_:])


