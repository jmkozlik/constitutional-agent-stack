from mod import Service


def run():
    svc = Service()
    return svc.handle({"a": 1})
