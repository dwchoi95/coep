def flatten(nested):
    result = []
    for item in nested:
        if isinstance(list, item):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result
