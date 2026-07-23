input_one = input().split()
i = int(input_one[0])
two = input_one[1]
count = 0



while  i <= int(two):
    
    i = str(i)
    if i[0] == i[4]:
        if i[1] == i[3]:
            count += 1

    i = int(i) + 1
print(count)