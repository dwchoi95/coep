# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
#       %% Input to the system in string %%
Sentence = str(input())

#finding the index of not and bad to compare them
index_not = Sentence.find("not")
index_bad = Sentence.find("bad")

#Adding a les than statement so that i can compare better in if condition
Bad_comes_first = index_not < index_bad

# If condition tryiing without subscript
if( Bad_comes_first == True):
    split_not = Sentence.split("not",1)
    #split from after not to bad end thus remaining only the end statement(symbol)
    split_bad = Sentence.split("bad", 1)
    
    # giving before not setence a value
    substring1 = split_not[0]
    # giving after not to end bad  setence a value
    substring3 = split_bad[1]
    #adding these sentences but because the not is removed and also the bad is removed after using slpit function
    print(substring1+"good"+substring3)


else:
    print(Sentence)
