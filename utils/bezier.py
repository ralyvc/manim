import numpy as np

from scipy import linalg
from utils.simple_functions import choose

CLOSED_THRESHOLD = 0.0


def bezier(points):
    n = len(points) - 1
    return lambda t: sum([
        ((1 - t)**(n - k)) * (t**k) * choose(n, k) * point
        for k, point in enumerate(points)
    ])


def partial_bezier_points(points, a, b):
    """
    Given an array of points which define
    a bezier curve, and two numbers 0<=a<b<=1,
    return an array of the same size, which
    describes the portion of the original bezier
    curve on the interval [a, b].

    This algorithm is pretty nifty, and pretty dense.
    """
    a_to_1 = np.array([
        bezier(points[i:])(a)
        for i in range(len(points))
    ])
    return np.array([
        bezier(a_to_1[:i + 1])((b - a) / (1. - a))
        for i in range(len(points))
    ])


# Linear interpolation variants

def interpolate(start, end, alpha):
    return (1 - alpha) * start + alpha * end


def mid(start, end):
    return (start + end) / 2.0


def inverse_interpolate(start, end, value):
    return np.true_divide(value - start, end - start)


def match_interpolate(new_start, new_end, old_start, old_end, old_value):
    return interpolate(
        new_start, new_end,
        inverse_interpolate(old_start, old_end, old_value)
    )


def clamp(lower, upper, val):
    if val < lower:
        return lower
    elif val > upper:
        return upper
    return val

# Figuring out which bezier curves most smoothly connect a sequence of points


def get_smooth_handle_points(points):
    points = np.array(points)
    num_handles = len(points) - 1
    dim = points.shape[1]
    if num_handles < 1:
        return np.zeros((0, dim)), np.zeros((0, dim))
    # Must solve 2*num_handles equations to get the handles.
    # l and u are the number of lower an upper diagonal rows
    # in the matrix to solve.
    l, u = 2, 1
    # diag is a representation of the matrix in diagonal form
    # See https://www.particleincell.com/2012/bezier-splines/
    # for how to arive at these equations
    diag = np.zeros((l + u + 1, 2 * num_handles))
    diag[0, 1::2] = -1
    diag[0, 2::2] = 1
    diag[1, 0::2] = 2
    diag[1, 1::2] = 1
    diag[2, 1:-2:2] = -2
    diag[3, 0:-3:2] = 1
    # last
    diag[2, -2] = -1
    diag[1, -1] = 2
    # This is the b as in Ax = b, where we are solving for x,
    # and A is represented using diag.  However, think of entries
    # to x and b as being points in space, not numbers
    b = np.zeros((2 * num_handles, dim))
    b[1::2] = 2 * points[1:]
    b[0] = points[0]
    b[-1] = points[-1]

    def solve_func(b):
        return linalg.solve_banded((l, u), diag, b)
    if is_closed(points):
        # Get equations to relate first and last points
        matrix = diag_to_matrix((l, u), diag)
        # last row handles second derivative
        matrix[-1, [0, 1, -2, -1]] = [2, -1, 1, -2]
        # first row handles first derivative
        matrix[0, :] = np.zeros(matrix.shape[1])
        matrix[0, [0, -1]] = [1, 1]
        b[0] = 2 * points[0]
        b[-1] = np.zeros(dim)

        def solve_func(b):
            return linalg.solve(matrix, b)
    handle_pairs = np.zeros((2 * num_handles, dim))
    for i in range(dim):
        handle_pairs[:, i] = solve_func(b[:, i])
    return handle_pairs[0::2], handle_pairs[1::2]


def diag_to_matrix(l_and_u, diag):
    """
    Converts array whose rows represent diagonal
    entries of a matrix into the matrix itself.
    See scipy.linalg.solve_banded
    """
    l, u = l_and_u
    dim = diag.shape[1]
    matrix = np.zeros((dim, dim))
    for i in range(l + u + 1):
        np.fill_diagonal(
            matrix[max(0, i - u):, max(0, u - i):],
            diag[i, max(0, u - i):]
        )
    return matrix


def is_closed(points):
    return np.linalg.norm(points[0] - points[-1]) < CLOSED_THRESHOLD
