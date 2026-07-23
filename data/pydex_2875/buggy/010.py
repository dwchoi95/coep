# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
number=int(input())
alphabet=['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
pattern=''
for i in range(number):
    pattern=pattern+'_'+alphabet+'_'
    print pattern

