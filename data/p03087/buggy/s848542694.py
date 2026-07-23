
x = input().split()
n = int(x[0]) 
q = int(x[1]) 
s = input()

def ind_Multi(a,b): 
    global n
    global s 
    index_L = []
    for i in range(a,b):
        if s[i] == "A":
            index_L.append(i)
    return index_L

            
        
t = [0] * n
if s[0] == "A":
    t[0] = 1
    
for i in range(0,n-1):
    if s[i:i+2] == "AC":
        
        if (i == 0) :
            t[i] =  + 1
        else:
            t[i] = t[i-1] + 1
    else :
        if i == 0:
            t[i] = 0
        else:
            t[i] = t[i-1]



def sc():
    global t
    global s
    global n
    global q
    global idbox
    maxx = 0
    count = 0
    com = [int(s)-1 for s in input().split()]
    print(com)
    idbox = ind_Multi(com[0],com[1])
    print(t[com[1]-1] - t[com[0]-1])
        
    

    

for i in range(q):
    
    sc()
