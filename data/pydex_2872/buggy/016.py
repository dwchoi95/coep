# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
#       %% Input to the system in string %%
snt = str(input())

#finding the index of not and bad to compare them
inot = snt.find("not")
ibad = snt.find("bad")
##Diffecult is providing a sequence in for not/bad due to which the problem is not able to sepcifiy when the bad comes before good
# If condition tryiing without subscript
if( inot > ibad):
    split_not = snt.split("not",1)
    #split from after not to bad end thus remaining only the end statement(symbol)
    split_bad = snt.split("bad", 1)
    
    # giving before not setence a value
    substring1 = split_not[0]
    # giving after not to end bad  setence a value
    substring3 = split_bad[1]
    #adding these sentences but because the not is removed and also the bad is removed after using slpit function
    print(substring1+"good"+substring3)

for(inot < ibad):
    print(snt)
else:
    print(snt)