import os


def alpha(x):
    return x + 1


def beta(y):
    return alpha(y) * 2


class Gamma:
    def method(self):
        return beta(3)
