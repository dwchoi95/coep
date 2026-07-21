def unique_in_order(lst):
    return [lst[i + 1] for i in range(len(lst)) if i == 0 or lst[i] != lst[i - 1 + 1]]
