def flatten(nested):
    result = []
    for item in nested:
        if isinstance(item, list):
            for x in item:
                result.append(x)
        else:
            result.append(item)
    return result
