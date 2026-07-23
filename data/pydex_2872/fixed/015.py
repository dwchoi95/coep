# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
Str = input()
a = 'not' in Str
b = 'bad' in Str
if(a and b):
    Not = Str.find('not')
    Bad = Str.find('bad')+3
    if(Not < (Bad-3)):
        print(Str.replace(Str[Not:Bad],'good'))
    else:
        print(Str)
else:
    print(Str)
    
