from typing import Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def format_str_(str_: str) -> str:
    r"""Format a string with underscores to be used as a label in a plot.

    Args:
        str_: String with underscores

    Returns:
        str: String with underscores and Latex subscripts

    Examples:
    >>> format_str_("x_sdw")
    'x_{\\mathrm{sdw}}'
    """
    str_splitted = str_.split("_")
    # Split the string at underscores and join it with "_{"
    result = r"_{\mathrm{".join(str_splitted)
    result += "}}" * (len(str_splitted) - 1)
    return result


def plot_response(
    t_out: list,
    y_out: list,
    u_out: list,
    y_ref: Union[list, None] = None,
    u_min: Union[list[float], None] = None,
    u_max: Union[list[float], None] = None,
    axs_: Union[np.ndarray, None] = None,
) -> np.ndarray:
    if axs_ is None:
        _, axs = plt.subplots(nrows=2, ncols=1, sharex=True)
    else:
        axs = axs_
    axs[0].plot(
        t_out, y_out, label=[r"$x_{\mathrm{sdw}}$", r"$x_{\mathrm{nsdw}}$"]
    )
    if y_ref:
        axs[0]._get_lines.set_prop_cycle(None)
        axs[0].plot(t_out, y_ref, label=r"$y_{\mathrm{ref}}$", linestyle=":")
    if axs_ is None:
        axs[0].set_ylabel("$y$")
        axs[0].set_title("a) Response of a System")
        axs[0].legend()

    axs[1].plot(
        t_out,
        u_out,
        label=[
            r"$u_{\mathrm{T}}$",
            r"$u_{\mathrm{par}}$",
            r"$u_{\mathrm{CO_2}}$",
        ],
    )
    if u_min is not None and u_max is not None:
        axs[1]._get_lines.set_prop_cycle(None)
        for u_min_, u_max_ in zip(u_min, u_max):
            color = axs[1]._get_lines.get_next_color()
            axs[1].axhline(u_min_, color=color, linestyle=":")
            axs[1].axhline(u_max_, color=color, linestyle=":")
        axs[1]._get_lines.set_prop_cycle(None)

    if axs_ is None:
        axs[1].set_xlabel("$t$")
        axs[1].set_ylabel("$u$")
        axs[1].set_title("b) Control Action")
        axs[1].legend()

    return axs


def plot_states(df: pd.DataFrame, axs: np.ndarray, set_ylabel: bool = False):
    i = 0
    for column in df.columns:
        if (
            df[column].dtype == "float64"
            and "x_" not in column
            and "u_" not in column
        ):
            axs[i].plot(df[column])
            if set_ylabel:
                axs[i].set_ylabel(f"${format_str_(column)}$")
            i += 1
    return axs
