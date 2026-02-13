"""Work flow state machine."""
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
import logging


logger = logging.getLogger(__name__)


@dataclass
class StateTransition:
    """State transition definition."""
    
    from_state: str
    to_state: str
    conditions: Optional[List[str]] = None  # Optional conditions that must be met


class WorkflowStateMachine:
    """
    Finite state machine for patient workflow.
    
    Pure domain logic - defines and validates state transitions.
    """
    
    # Define all valid states
    STATES = {
        "intake": {
            "display_name": "Patient Intake",
            "description": "Initial patient registration and intake",
            "allows_transitions_to": ["assessment"]
        },
        "assessment": {
            "display_name": "Assessment",
            "description": "Clinical and psychosocial assessment",
            "allows_transitions_to": ["scoring"]
        },
        "scoring": {
            "display_name": "Risk Scoring",
            "description": "PRS scoring and risk assessment",
            "allows_transitions_to": ["routing"]
        },
        "routing": {
            "display_name": "Routing",
            "description": "Route to appropriate center",
            "allows_transitions_to": ["assignment"]
        },
        "assignment": {
            "display_name": "Clinician Assignment",
            "description": "Assign to clinician/care team",
            "allows_transitions_to": ["active"]
        },
        "active": {
            "display_name": "Active Care",
            "description": "Patient in active care",
            "allows_transitions_to": ["completed"]
        },
        "completed": {
            "display_name": "Care Completed",
            "description": "Patient completed program",
            "allows_transitions_to": []
        },
        "archived": {
            "display_name": "Archived",
            "description": "Patient record archived",
            "allows_transitions_to": []
        }
    }
    
    def __init__(self):
        """Initialize state machine."""
        self._validate_states()
    
    def _validate_states(self) -> None:
        """Validate state definitions."""
        for state, config in self.STATES.items():
            for target in config.get("allows_transitions_to", []):
                if target not in self.STATES:
                    raise ValueError(f"Invalid target state {target} from {state}")
    
    def is_valid_transition(
        self,
        from_state: str,
        to_state: str
    ) -> bool:
        """Check if transition is valid."""
        if from_state not in self.STATES:
            return False
        
        allowed_targets = self.STATES[from_state].get("allows_transitions_to", [])
        return to_state in allowed_targets
    
    def get_allowed_transitions(self, current_state: str) -> List[str]:
        """Get list of allowed next states."""
        if current_state not in self.STATES:
            return []
        
        return self.STATES[current_state].get("allows_transitions_to", [])
    
    def get_state_info(self, state: str) -> Optional[Dict]:
        """Get state information."""
        return self.STATES.get(state)
    
    def get_all_states(self) -> List[str]:
        """Get all valid states."""
        return list(self.STATES.keys())
    
    def can_transition(
        self,
        from_state: str,
        to_state: str,
        conditions: Optional[Dict] = None
    ) -> tuple[bool, str]:
        """
        Check if transition is valid with optional conditions.
        
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        if from_state not in self.STATES:
            return False, f"Invalid current state: {from_state}"
        
        if to_state not in self.STATES:
            return False, f"Invalid target state: {to_state}"
        
        allowed = self.STATES[from_state].get("allows_transitions_to", [])
        if to_state not in allowed:
            return (
                False,
                f"Cannot transition from {from_state} to {to_state}. "
                f"Allowed transitions: {', '.join(allowed)}"
            )
        
        # Check conditions if provided
        if conditions:
            # Add custom validation logic here
            pass
        
        return True, ""
    
    def get_transition_path(
        self,
        from_state: str,
        to_state: str
    ) -> Optional[List[str]]:
        """
        Find transition path between two states using BFS.
        
        Returns:
            List of states from -> to, or None if unreachable
        """
        if from_state == to_state:
            return [from_state]
        
        if from_state not in self.STATES or to_state not in self.STATES:
            return None
        
        queue = [(from_state, [from_state])]
        visited = {from_state}
        
        while queue:
            current, path = queue.pop(0)
            
            for next_state in self.STATES[current].get("allows_transitions_to", []):
                if next_state == to_state:
                    return path + [next_state]
                
                if next_state not in visited:
                    visited.add(next_state)
                    queue.append((next_state, path + [next_state]))
        
        return None
