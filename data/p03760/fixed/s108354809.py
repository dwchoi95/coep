o = input()
e = input()
if(len(o)>len(e)): e+=' '
print("".join([ch1 + ch2 for ch1 , ch2 in zip(o,e)]))