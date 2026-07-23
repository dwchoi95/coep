# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
strI = input()
K = 0
listinput =strl.split(',')
for i in range(0,len(listinput)):
    Lstr =listinput[i]
    if(len(Lstr)>=2):
    flag =0
    if Lstr[0] == Lstr[len(Lstr)-1]:
        K = K+1
print (K)