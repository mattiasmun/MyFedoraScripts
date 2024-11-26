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
    b = (b == float) or (b == np.float64)
    return gp.mpfr(str(a)) if b else gp.mpfr(a)

def limit_denominator(x, max_den = _lf(1e15)):
	#Finds the best rational approximation of an mpq with a denominator <= max_den.
	#Args:
	#	x: The mpq number to approximate.
	#	max_den: The maximum allowed denominator.
	#Returns:
	#	The best rational approximation as an mpq.
	A = frac_to_cont_frac(x)
	return cont_frac_to_frac(A, max_den)

_A = np.full(1000, gp.mpz(0))

def frac_to_cont_frac(p, q = 1):
	if type(p) == gp.mpq:
		p, q = p.numerator, p.denominator
	A, i = _A.copy(), 0
	while q:
		if len(A) == i:
			A = np.concatenate((A, _A))
		A[i] = gp.mpz(p // q)
		p, q = q, p % q
		i += 1
	return A[:i]

def cont_frac_to_frac(seq, max_den = _lf(1e15)):
	#Convert the simple continued fraction in `seq`
	#into a fraction, num / den
	n, d, num, den = 0, 1, 1, 0
	for u in seq:
		n, d, num, den = num, den, gp.fma(num, u, n), gp.fma(den, u, d)
		if den > max_den:
			if d > 0:
				return gp.mpq(n, d)
	return gp.mpq(num, den)\
"""
exec(cmds)
x = frac_to_cont_frac(π)
y = cont_frac_to_frac(x[:34])

