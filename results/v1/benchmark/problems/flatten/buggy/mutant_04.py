def flatten(nested):
    flat = list(nested)
    while any((isinstance(list, x) for x in flat)):
        nxt = []
        for x in flat:
            if isinstance(list, x):
                nxt.extend(x)
            else:
                nxt.append(x)
        flat = nxt
    return flat
