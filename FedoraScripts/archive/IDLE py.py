#!/bin/python3
cmds = """\
import gmpy2 as gp
import numpy as np
from timeit import timeit
ctx = gp.get_context()
ctx.precision = 127
ctx.allow_complex = True
π = gp.const_pi()
φ = 0.5 + gp.sqrt(1.25)
ψ = gp.mpfr('1.465571231876768026656731225219939108025')
_the_str = "π, φ, ψ = " + str(π) + ", " + str(φ) + ", " + str(ψ)
print(_the_str)
_1 = gp.mpfr(1)
_m1, _0, _2 = -_1, _1 - _1, _1 + _1
def _lf(a):
    b = type(a)
    b = (b == float) or (b == np.float_)
    return gp.mpfr(str(a)) if b else gp.mpfr(a)\
"""
exec(cmds)
