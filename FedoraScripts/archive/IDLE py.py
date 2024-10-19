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
print(π, φ, ψ)\
"""
exec(cmds)
