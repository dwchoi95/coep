def unique_in_order(lst):
    return [lst[i] for i in range(len(lst)) if i == 1 or lst[i] != lst[i - 1]]
