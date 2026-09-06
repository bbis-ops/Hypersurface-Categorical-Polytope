"""Exact formal verification of the activation boundary through degree 20.

Run from the repository root: python experiments/activation_contact_check.py
Uses only the standard library. Global optimality is proved in the companion
research note; this script independently checks the formal algebra.
"""

from fractions import Fraction as Q


ORDER = 20


def add(*series):
    result = {}
    for terms in series:
        for k, c in terms.items():
            result[k] = result.get(k, Q(0)) + c
    return {k: c for k, c in result.items() if c and k <= ORDER}


def scale(terms, c, shift=0):
    return {k+shift: c*v for k, v in terms.items() if k+shift <= ORDER and c*v}


def multiply(left, right):
    result = {}
    for i, a in left.items():
        for j, b in right.items():
            if i+j <= ORDER:
                result[i+j] = result.get(i+j, Q(0)) + a*b
    return {k: c for k, c in result.items() if c}


def power(terms, n):
    result = {0: Q(1)}
    for _ in range(n):
        result = multiply(result, terms)
    return result


def inverse(terms):
    result = {0: 1/terms[0]}
    for n in range(1, ORDER+1):
        coefficient = -sum(terms.get(k, Q(0))*result.get(n-k, Q(0))
                           for k in range(1, n+1))/terms[0]
        if coefficient:
            result[n] = coefficient
    assert multiply(terms, result) == {0: Q(1)}
    return result


def verify():
    u, v = {0: Q(1, 8)}, {0: Q(1, 2)}
    # Iterate the exact implicit equations in the truncated series ring.
    for _ in range(12):
        new_u = add(scale(power(v, 2), Q(1, 2)), scale(power(u, 5), Q(-3), 7))
        new_v = add({0: Q(1, 2)},
                    scale(multiply(power(u, 6), inverse(power(v, 5))), Q(-4), 6))
        u, v = new_u, new_v

    first = add(u, scale(power(u, 5), Q(3), 7), scale(power(v, 2), Q(-1, 2)))
    second = add(multiply(power(v, 5), add(scale(v, Q(2)), {0: Q(-1)})),
                 scale(power(u, 6), Q(8), 6))
    assert first == second == {}, "coexistence equations failed"
    critical = add(scale(power(v, 2), Q(3, 2)), scale(v, Q(-5, 4)),
                   scale(multiply(power(u, 5), inverse(power(v, 2))), Q(3, 2), 6))
    expected = {0: Q(-1, 4), 6: Q(1, 2**14), 12: Q(-1, 2**22),
                13: Q(-9, 2**26), 18: Q(7, 2**32), 19: Q(9, 2**32),
                20: Q(135, 2**38)}
    assert critical == expected, (critical, expected)

    # Check both zero value and stationarity, not just the rearranged equations.
    value = add(scale(power(v, 6), Q(-1)), power(v, 5), multiply(critical, power(v, 4)),
                scale(power(u, 6), Q(-1), 6), scale(power(u, 10), Q(-9), 13))
    derivative = add(scale(power(v, 5), Q(-6)), scale(power(v, 4), Q(5)),
                     scale(multiply(critical, power(v, 3)), Q(4)),
                     scale(multiply(v, power(u, 5)), Q(-6), 6))
    assert value == derivative == {}, "critical value or stationary equation failed"
    assert v[6] == Q(-1, 2048)
    assert u[6] == Q(-1, 4096) and u[7] == Q(-3, 32768)

    print(f"Exact coexistence, zero value, and stationarity verified through degree {ORDER}.")
    for k, coefficient in sorted(critical.items()):
        print(f"lambda_c: s^{k:2d} coefficient = {coefficient}")
    print("Contact prefactor = 1/16.")
    print("s^18 path coefficient =", -critical[12]/16)
    print("s^19 path coefficient =", -critical[13]/16)


if __name__ == "__main__":
    verify()
