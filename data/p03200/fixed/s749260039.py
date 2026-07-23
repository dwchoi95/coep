data = list(input())

count = 0


count_b = 0
for i in range(len(data)):
    
    if data[i] == 'W':
        count += count_b
        
        
        
    else:
        count_b += 1
    
    
print(count)
