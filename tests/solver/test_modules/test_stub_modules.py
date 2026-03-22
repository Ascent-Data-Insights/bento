"""Tests for the three stub constraint modules: ev_fuel, shift_limits, priority_sla."""

import pytest
import pyomo.environ as pyo

from backend.solver.modules import REGISTRY
from backend.solver.modules.ev_fuel import EvFuelModule
from backend.solver.modules.shift_limits import ShiftLimitsModule
from backend.solver.modules.priority_sla import PrioritySlaModule


class TestEvFuelModule:
    def test_registered(self):
        assert "ev_fuel" in REGISTRY

    def test_metadata_key(self):
        m = EvFuelModule()
        assert m.get_metadata().key == "ev_fuel"

    def test_metadata_name(self):
        m = EvFuelModule()
        assert m.get_metadata().name == "EV/Fuel Range"

    def test_metadata_description_not_empty(self):
        m = EvFuelModule()
        assert m.get_metadata().description

    def test_implemented_false(self):
        assert EvFuelModule.implemented is False

    def test_validate_returns_empty_list(self):
        m = EvFuelModule()
        model = pyo.ConcreteModel()
        assert m.validate(model, m.get_data_schema()(), {}) == []

    def test_add_to_model_raises(self):
        m = EvFuelModule()
        model = pyo.ConcreteModel()
        with pytest.raises(NotImplementedError):
            m.add_to_model(model, m.get_data_schema()(), {})

    def test_get_data_schema_returns_model(self):
        m = EvFuelModule()
        schema = m.get_data_schema()
        assert schema is not None
        # Should be instantiable with no args
        schema()


class TestShiftLimitsModule:
    def test_registered(self):
        assert "shift_limits" in REGISTRY

    def test_metadata_key(self):
        m = ShiftLimitsModule()
        assert m.get_metadata().key == "shift_limits"

    def test_metadata_name(self):
        m = ShiftLimitsModule()
        assert m.get_metadata().name == "Shift Limits"

    def test_metadata_description_not_empty(self):
        m = ShiftLimitsModule()
        assert m.get_metadata().description

    def test_implemented_false(self):
        assert ShiftLimitsModule.implemented is False

    def test_validate_returns_empty_list(self):
        m = ShiftLimitsModule()
        model = pyo.ConcreteModel()
        assert m.validate(model, m.get_data_schema()(), {}) == []

    def test_add_to_model_raises(self):
        m = ShiftLimitsModule()
        model = pyo.ConcreteModel()
        with pytest.raises(NotImplementedError):
            m.add_to_model(model, m.get_data_schema()(), {})

    def test_get_data_schema_returns_model(self):
        m = ShiftLimitsModule()
        schema = m.get_data_schema()
        assert schema is not None
        schema()


class TestPrioritySlaModule:
    def test_registered(self):
        assert "priority_sla" in REGISTRY

    def test_metadata_key(self):
        m = PrioritySlaModule()
        assert m.get_metadata().key == "priority_sla"

    def test_metadata_name(self):
        m = PrioritySlaModule()
        assert m.get_metadata().name == "Priority/SLA"

    def test_metadata_description_not_empty(self):
        m = PrioritySlaModule()
        assert m.get_metadata().description

    def test_implemented_false(self):
        assert PrioritySlaModule.implemented is False

    def test_validate_returns_empty_list(self):
        m = PrioritySlaModule()
        model = pyo.ConcreteModel()
        assert m.validate(model, m.get_data_schema()(), {}) == []

    def test_add_to_model_raises(self):
        m = PrioritySlaModule()
        model = pyo.ConcreteModel()
        with pytest.raises(NotImplementedError):
            m.add_to_model(model, m.get_data_schema()(), {})

    def test_get_data_schema_returns_model(self):
        m = PrioritySlaModule()
        schema = m.get_data_schema()
        assert schema is not None
        schema()


class TestRegistryContainsAllModules:
    def test_all_five_modules_registered(self):
        expected = {"time_windows", "co_delivery", "ev_fuel", "shift_limits", "priority_sla"}
        assert expected.issubset(set(REGISTRY.keys()))

    def test_implemented_modules_flagged_true(self):
        assert getattr(REGISTRY["time_windows"], "implemented", True) is True
        assert getattr(REGISTRY["co_delivery"], "implemented", True) is True

    def test_stub_modules_flagged_false(self):
        assert getattr(REGISTRY["ev_fuel"], "implemented", True) is False
        assert getattr(REGISTRY["shift_limits"], "implemented", True) is False
        assert getattr(REGISTRY["priority_sla"], "implemented", True) is False
