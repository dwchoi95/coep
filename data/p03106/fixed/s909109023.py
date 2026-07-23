a,b,c= input().split()
x,y,z=(int(a),int(b),int(c))
ans_list =[]
for i in range(min(x,y)):
    
    if x % (i+1) == 0 and y % (i+1) == 0:
        ans_list.append(i+1)
print(ans_list[len(ans_list)-z])