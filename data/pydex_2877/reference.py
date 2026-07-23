myinput=input()
vs = myinput.split(',')
count=0

for v in vs:
    if len(v) >= 2 and v[0]==v[-1]:
        count += 1
    
print(count)