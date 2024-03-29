from abc import ABC, abstractmethod

import casadi as ca


class Ventilation(ABC):
    """Ventilation model interface

    Interface for Ventilation models
    """

    def __init__(self, max_flow):
        self.max_flow = max_flow  # Maximum flow in 1/s

    @abstractmethod
    def transform_one(self, signal: float) -> float:
        pass


class SimpleVentilation(Ventilation):
    """Ventilation model

    Simple Ventilation model that takes a signal percentage and returns the airflow

    Examples:
    >>> max_flow = 1000  # Maximum airflow in 1/s
    >>> ventilation = SimpleVentilation(max_flow)
    >>> ventilation.transform_one(50)
    500.0
    """

    def __init__(self, max_flow: float):
        self.max_flow = max_flow

    def transform_one(
        self, signal: float | ca.GenericExpressionCommon
    ) -> float | ca.MX:
        # Ensure signal is within the range of 0 to 100
        if isinstance(signal, ca.GenericExpressionCommon):
            signal = ca.if_else(signal < 0, 0, signal)
            signal = ca.if_else(signal > 100, 100, signal)
        else:
            signal = max(0.0, min(100.0, signal))

        # Calculate airflow based on the signal
        return (signal / 100.0) * self.max_flow
