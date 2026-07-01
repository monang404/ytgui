"""
PATCH-0-01: AppState.duration field
Verifikasi bahwa field `duration` ada di AppState dataclass dan
tercantum di _state_to_dict().
"""

import pytest
from core.state import AppState, PlayerStatus, TrackInfo


class TestAppStateDurationField:
    """Checklist PATCH-0-01:
    - [x] AppState().duration tidak melempar AttributeError
    - [x] _state_to_dict(state) mengandung key "duration"
    """

    def test_appstate_has_duration_field(self):
        """AppState().duration harus bisa diakses tanpa AttributeError."""
        state = AppState()
        assert hasattr(state, "duration"), "AppState harus memiliki field 'duration'"
        assert state.duration == 0.0

    def test_appstate_duration_default_is_zero(self):
        """Default duration harus 0.0."""
        state = AppState()
        assert state.duration == 0.0

    def test_appstate_duration_is_settable(self):
        """Duration harus bisa diset ke value float."""
        state = AppState()
        state.duration = 212.0
        assert state.duration == 212.0

    def test_appstate_duration_in_dataclass_fields(self):
        """Duration harus menjadi field dataclass (bukan dynamic attribute)."""
        import dataclasses
        field_names = [f.name for f in dataclasses.fields(AppState)]
        assert "duration" in field_names, "duration harus field dataclass, bukan dynamic attribute"

    def test_state_to_dict_contains_duration(self):
        """_state_to_dict() harus mengandung key 'duration'."""
        from server.serializers import state_to_dict as _state_to_dict
        state = AppState()
        state.duration = 300.0
        result = _state_to_dict(state)
        assert "duration" in result, "_state_to_dict harus mengandung key 'duration'"

    def test_state_to_dict_duration_value(self):
        """_state_to_dict() harus mengembalikan nilai duration yang benar."""
        from server.serializers import state_to_dict as _state_to_dict
        state = AppState()
        state.duration = 212.5
        result = _state_to_dict(state)
        assert result["duration"] == 212.5
