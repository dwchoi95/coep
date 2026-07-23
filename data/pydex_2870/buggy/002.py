# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
i = input()
S = lower(i)
l = len(S)
if(l%2!=0)
    B = S[:(l+1)/2]
    E = S[:(l+1)/2:-1]
    print(B,E)
    if(B==E)
        print(i,'is a palindrome.')
    else
        print(i,'is NOT a palindrome.')
else
    B = S[:l/2]
    E = S[:l/2:-1]
    print(B,E)