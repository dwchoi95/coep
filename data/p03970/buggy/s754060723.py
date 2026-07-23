def string_trnase(s):
    answer = 'CODEFESTIVAL2016'
    iters = 0
    s = list(s)
    for i in range(0, 16):
        if s[i] != answer[i]:
            iters += 1
    print(iters)


print('Enter a string: ')
string_trnase(input())