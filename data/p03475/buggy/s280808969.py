n = int(input())
csf = []
for i in range(n - 1):
    csf.append(list(map(int, input().split())))

for i in range(n):
    AnsSec = 0
    Now_Station = i
    while Now_Station < n - 1:
        if AnsSec > csf[Now_Station][1]:
            if csf[Now_Station][2] % AnsSec != 0:
                AnsSec += csf[Now_Station][2] - (AnsSec % csf[Now_Station][2] )
        else:
            AnsSec += csf[Now_Station][1] - AnsSec
        AnsSec += csf[Now_Station][0]
        Now_Station += 1
    print(AnsSec)
