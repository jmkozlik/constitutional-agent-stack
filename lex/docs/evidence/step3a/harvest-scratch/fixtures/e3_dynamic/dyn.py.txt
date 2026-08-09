import mod


def run(name):
    fn = getattr(mod, name)
    return fn(1)
