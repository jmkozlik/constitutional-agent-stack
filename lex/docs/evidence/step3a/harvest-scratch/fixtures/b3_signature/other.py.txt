from mod import target


def caller_two():
    return target(2)


def caller_three():
    f = target
    return f(3)
