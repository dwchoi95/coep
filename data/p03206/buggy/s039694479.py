target = int(input())
common_msg = "Christmas"
additional_msg = "Eve"
print(common_msg + " ".join(["Eve" for i in range(25 - target)]))
