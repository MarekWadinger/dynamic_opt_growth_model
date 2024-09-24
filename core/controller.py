import numpy as np
import pandas as pd
from casadi import dot, vertcat, vertsplit
from do_mpc.controller import MPC
from do_mpc.model import Model
from do_mpc.simulator import Simulator

from core.greenhouse_model import A_p as greenhouse_area
from core.greenhouse_model import heater, ventilation
from core.greenhouse_model import model as gh_model
from examples.GES_Example import z


class GreenHouseModel(Model):  # Create a model instance
    def __init__(
        self,
        climate_vars,
        dt=60,
    ):
        super().__init__("discrete")

        # Define state and control variables
        t = self.set_variable(var_type="_tvp", var_name="t", shape=(1, 1))
        x = self.set_variable(var_type="_x", var_name="x", shape=(len(z), 1))
        u = self.set_variable(var_type="_u", var_name="u", shape=(2, 1))
        tvp = {
            name: self.set_variable(var_type="_tvp", var_name=name)
            for name in climate_vars
        }

        # Define the model equations
        def f(t, x, u, tvp):
            return vertcat(
                *gh_model(
                    t, vertsplit(x), vertsplit(u), climate=tuple(tvp.values())
                )
            )

        k1 = f(t, x, u, tvp)
        k2 = f(t, x + dt / 2 * k1, u, tvp)
        k3 = f(t, x + dt / 2 * k2, u, tvp)
        k4 = f(t, x + dt * k3, u, tvp)
        x_next = x + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        # x_next = backward_euler_step(f, t, x, u, tvp, dt)
        # x_next = bdf2_step(f, t + dt, x, x_next, u, tvp, dt)

        self.set_rhs("x", x_next)

        self.setup()


class EconomicMPC(MPC):
    def __init__(
        self,
        model,
        climate,
        lettuce_price=0.0054,  # EUR/g
        greenhouse_area=greenhouse_area,  # m^2
        N=60,  # number of control intervals
        dt=60,  # sampling time in seconds
        x_ref=np.array([50.0, 5.0]),  # reference state
        u_min=[0.0, 0.0],
        u_max=[100.0, 100.0],
    ):
        # Define optimization variables
        self.x = model.x["x"]
        self.u = model.u["u"]

        self.climate = climate

        self.lettuce_price = lettuce_price
        self.greenhouse_area = greenhouse_area

        assert len(u_min) == model.n_u
        assert len(u_max) == model.n_u

        # Create an MPC instance
        super().__init__(model)

        # Set parameters
        setup_mpc = {
            "n_horizon": N,
            "t_step": dt,
            "supress_ipopt_output": True,
            "state_discretization": "discrete",
            "nlpsol_opts": {
                "ipopt": {  # https://coin-or.github.io/Ipopt/OPTIONS.html
                    "max_iter": 3,
                    "linear_solver": "MA57",  # https://licences.stfc.ac.uk/product/coin-hsl
                    "warm_start_init_point": "yes",
                    "mu_allow_fast_monotone_decrease": "yes",
                    "print_level": 0,
                    # "output_file": "ipopt.out",
                    "print_user_options": "yes",
                    "print_options_documentation": "yes",
                    "print_frequency_iter": 4,
                }
            },
        }
        self.set_param(**setup_mpc)
        # Define objective
        self.set_objective(
            mterm=dot(self.x[-2] - x_ref[0], self.x[-2] - x_ref[0])
            * 0,  # ca.DM(0)
            lterm=(
                -dot(
                    self.lettuce_price * self.x[-2] * self.greenhouse_area,
                    self.lettuce_price * self.x[-2] * self.greenhouse_area,
                )
                + dot(
                    ventilation.signal_to_eur(self.u[0]),
                    ventilation.signal_to_eur(self.u[0]),
                )
                + dot(
                    ventilation.signal_to_co2_eur(self.u[0]),
                    ventilation.signal_to_co2_eur(self.u[0]),
                )
                + dot(
                    heater.signal_to_eur(self.u[1]),
                    heater.signal_to_eur(self.u[1]),
                )
                + dot(
                    heater.signal_to_co2_eur(self.u[1]),
                    heater.signal_to_co2_eur(self.u[1]),
                )
                + dot(
                    self.lettuce_price * z[-2] * self.greenhouse_area,
                    self.lettuce_price * self.x[-2] * self.greenhouse_area,
                )
            ),
        )

        self.set_rterm(
            u=np.array([1] * model.n_u)
        )  # Parametrize with size of greenhouse and Ts

        # Define path constraints
        self.bounds["lower", "_u", "u"] = u_min
        self.bounds["upper", "_u", "u"] = u_max

        self.bounds["lower", "_x", "x"] = [0.0] * model.n_x
        # # Small violation due to numerical instability
        # self.set_nl_cons(
        #     "x", -model.x["x"], ub=0, soft_constraint=True, penalty_term_cons=10000
        # )

        # self.set_nl_cons("u", self.u_prev["u"] - model.u["u"], ub=0)

        # Get the template
        tvp_mpc_template = self.get_tvp_template()

        # Define the function (indexing is much simpler ...)
        def tvp_mpc_fun(t_now):
            if isinstance(t_now, np.ndarray):
                t_now = t_now[0]
            # N is the horizon with given ts
            for k in range(N + 1):
                tvp_mpc_template["_tvp", k, "t"] = t_now + k
                for key in self.climate.columns:
                    tvp_mpc_template["_tvp", k, key] = self.climate[key][
                        pd.Timestamp(self.climate.index[0])
                        + pd.Timedelta(seconds=t_now + k)
                    ]
            return tvp_mpc_template

        # Set the tvp_fun:
        self.set_tvp_fun(tvp_mpc_fun)

        self.setup()


class GreenhouseSimulator(Simulator):
    def __init__(self, model, climate, dt=60):
        super().__init__(model)

        self.climate = climate

        params_simulator = {"t_step": dt}

        self.set_param(**params_simulator)

        # Get the template
        tvp_sim_template = self.get_tvp_template()

        # Define the function (indexing is much simpler ...)
        def tvp_sim_fun(t_now):
            if isinstance(t_now, np.ndarray):
                t_now = t_now[0]
            tvp_sim_template["t"] = t_now
            for key in climate.columns:
                tvp_sim_template[key] = climate[key][
                    pd.Timestamp(self.climate.index[0])
                    + pd.Timedelta(seconds=t_now)
                ]
            return tvp_sim_template

        # Set the tvp_fun:
        self.set_tvp_fun(tvp_sim_fun)

        self.setup()