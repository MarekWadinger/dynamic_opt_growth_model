"""Simulation of the system."""
from inspect import signature
from typing import Callable, Union

from scipy.integrate import solve_ivp

from core.generator import GenProt, validate_gen


def simulate(
    system: Callable,
    u: Union[GenProt, list],
    sim_time: int = 100,
    t_s: int = 1,
    x0: Union[list[float], None] = None,
    ref_gen: Union[GenProt, None] = None,
) -> list[list]:
    """Simulation of the system in the open-loop/closed-loop.

    Args:
        system: _description_
        u (optional): Function to generate the inputs or input history
        sim_time (optional): Time samples for the simulation
        t_s (optional): Sampling time in seconds [s]
        x0 (optional): Initial conditions
        ref_gen (optional): Function to generate the reference for closed-loop.
        If defined, u must be a function.

    Returns:
        Simulation results for time, outputs and inputs
    """
    t_out: list[int] = []
    y_out: list[Union[list[float], float]] = []
    y_ref: list[Union[list[float], float]] = []
    u_out: list[Union[list[float], float]] = []

    # Initial mass of structural and non-structural dry weight
    if x0 is None:
        len_x = len(signature(system).parameters["x"].annotation.__args__)
        x0 = [0.0] * len_x
    x_ode_prev = x0

    # Required for gen validation
    t: int = 0
    if ref_gen and callable(ref_gen):
        if callable(u):
            validate_gen(ref_gen, **locals())
            x_ref: Union[list[float], float] = 0.0  # u might use x_ref
        else:
            raise TypeError("ref_gen is defined but u is not Callable")

    if callable(u):
        validate_gen(u, **locals())

    for t in range(sim_time):
        tspan = [t, t + t_s]

        if ref_gen is not None:
            x_ref = ref_gen(**locals())
            y_ref.append(x_ref)
        if callable(u):
            u_ = u(**locals())
        else:
            u_ = u[t]

        x_ode = solve_ivp(system, tspan, x_ode_prev, args=(u_,), method="RK45")
        x_ode_prev = x_ode.y[:, -1]

        y_out.append(x_ode_prev)
        t_out.append(t)
        u_out.append(u_)

    if ref_gen is not None:
        return [t_out, y_out, u_out, y_ref]

    return [t_out, y_out, u_out]
