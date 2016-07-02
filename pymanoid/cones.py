#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 Stephane Caron <stephane.caron@normalesup.org>
#
# This file is part of pymanoid.
#
# pymanoid is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# pymanoid is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# pymanoid. If not, see <http://www.gnu.org/licenses/>.


import cdd

from exceptions import NaC, OptimalNotFound
from numpy import array, dot, eye, hstack, vstack, zeros
from utils import cvxopt_solve_qp, norm


def span_of_face(F):
    """
    Compute the span matrix S of the face matrix F, which is such that

        {F x <= 0}  if and only if  {x = F^S z, z >= 0}

    """
    b, A = zeros((F.shape[0], 1)), F
    # H-representation: b - A x >= 0
    # ftp://ftp.ifor.math.ethz.ch/pub/fukuda/cdd/cddlibman/node3.html
    # the input to pycddlib is [b, -A]
    mat = cdd.Matrix(hstack([b, -A]), number_type='float')
    mat.rep_type = cdd.RepType.INEQUALITY
    P = cdd.Polyhedron(mat)
    g = P.get_generators()
    V = array(g)
    rays = []
    for i in xrange(V.shape[0]):
        if V[i, 0] != 0:  # 1 = vertex, 0 = ray
            raise NaC(F)
        elif i not in g.lin_set:
            rays.append(V[i, 1:])
    return array(rays).T


def face_of_span(S):
    """
    Compute the face matrix F of the span matrix S, which is such that

        {x = S z, z >= 0}  if and only if  {F x <= 0}.

    """
    V = vstack([
        hstack([zeros((S.shape[1], 1)), S.T]),
        hstack([1, zeros(S.shape[0])])])
    # V-representation: first column is 0 for rays
    mat = cdd.Matrix(V, number_type='float')
    mat.rep_type = cdd.RepType.GENERATOR
    P = cdd.Polyhedron(mat)
    ineq = P.get_inequalities()
    H = array(ineq)
    if H.shape == (0,):  # H == []
        return H
    A = []
    for i in xrange(H.shape[0]):
        # H matrix is [b, -A] for A * x <= b
        if norm(H[i, 1:]) < 1e-10:
            continue
        elif abs(H[i, 0]) > 1e-10:  # b should be zero for a cone
            raise NaC(S)
        elif i not in ineq.lin_set:
            A.append(-H[i, 1:])
    return array(A)


def is_positive_combination(b, A):
    """
    Check if b can be written as a positive combination of lines from A.

    INPUT:

    - ``b`` -- test vector
    - ``A`` -- matrix of line vectors to combine

    OUTPUT:

    True if and only if b = A.T * x for some x >= 0.
    """
    m = A.shape[0]
    P, q = eye(m), zeros(m)
    #
    # NB: one could try solving a QP minimizing |A * x - b|^2 (and no equality
    # constraint), however the precision of the output is quite low (~1e-1).
    #
    G, h = -eye(m), zeros(m)
    try:
        x = cvxopt_solve_qp(P, q, G, h, A.T, b)
        return norm(dot(A.T, x) - b) < 1e-10 and min(x) > -1e-10
    except OptimalNotFound:
        return False
    return False


def is_redundant(F):
    """
    Check if a matrix of line vectors (typically the face representation of a
    polyhedral cone) is redundant.

    .. NOTE::

        When using cvxopt, this function may print out a significant number of
        messages "Terminated (singular KKT matrix)." in the terminal.

    """
    all_lines = set(range(F.shape[0]))
    return any([is_positive_combination(
        F[i], F[list(all_lines - set([i]))]) for i in all_lines])