"""
Deterministic orchestration for AI SysAdmin Agent.

Generates structured JSON plans before any execution.
Plans are deterministic (no random, time, or UUID dependencies).
"""

from __future__ import annotations

from typing import Dict, List, Any


# Keywords that trigger approval requirement
RISKY_KEYWORDS = [
    "restart", "reboot", "shutdown", "halt", "stop",
    "delete", "remove", "rm", "kill", "drop",
    "install", "upgrade", "update", "modify",
    "write", "format", "destroy"
]


def create_plan(user_input: str) -> Dict[str, Any]:
    """
    Generate a deterministic JSON plan from user input.
    
    Returns a structured plan with:
    - goal: trimmed user input (max 120 chars)
    - assumptions: list of assumptions
    - steps: list of action steps (max 10)
    - safety_notes: list of safety considerations
    
    Never raises exceptions - returns safe fallback on any error.
    
    Args:
        user_input: User's request/query
        
    Returns:
        dict: Structured plan
    """
    try:
        # Normalize input
        if not user_input or not user_input.strip():
            return _create_fallback_plan("No input provided")
        
        user_input = user_input.strip()
        
        # Create goal (max 120 chars)
        goal = user_input[:120]
        if len(user_input) > 120:
            goal = goal + "..."
        
        # Analyze input for risk keywords
        input_lower = user_input.lower()
        has_risky_keywords = any(keyword in input_lower for keyword in RISKY_KEYWORDS)
        
        # Determine if this is a query vs action
        is_query = any(word in input_lower for word in [
            "what", "show", "list", "check", "status", "view", "get", "describe"
        ])
        
        # Build assumptions
        assumptions = []
        if has_risky_keywords:
            assumptions.append("This operation may modify system state")
            assumptions.append("User has appropriate permissions")
        if is_query:
            assumptions.append("This is a read-only query")
        else:
            assumptions.append("This operation may require approval")
        
        # Generate steps (deterministic based on input characteristics)
        steps = _generate_steps(user_input, input_lower, has_risky_keywords, is_query)
        
        # Limit to max 10 steps
        if len(steps) > 10:
            steps = steps[:10]
        
        # Build safety notes
        safety_notes = []
        if has_risky_keywords:
            safety_notes.append("This operation contains potentially destructive actions")
            safety_notes.append("Review all steps carefully before approval")
        else:
            safety_notes.append("This operation appears to be low-risk")
        
        return {
            "goal": goal,
            "assumptions": assumptions,
            "steps": steps,
            "safety_notes": safety_notes
        }
        
    except Exception as e:
        # Never crash - return safe fallback
        print(f"[ORCHESTRATOR] ERROR in create_plan: {e}")
        return _create_fallback_plan(str(e))


def _generate_steps(
    user_input: str, 
    input_lower: str, 
    has_risky_keywords: bool, 
    is_query: bool
) -> List[Dict[str, Any]]:
    """
    Generate plan steps based on input analysis.
    Deterministic - no random or time-based logic.
    """
    steps = []
    step_id = 1
    
    # Step 1: Always validate/parse input
    steps.append({
        "id": step_id,
        "action": "Parse and validate user request",
        "reason": "Ensure request is understood correctly",
        "requires_approval": False
    })
    step_id += 1
    
    # Step 2: Knowledge base lookup (if appears to be a query)
    if is_query:
        steps.append({
            "id": step_id,
            "action": "Query knowledge base for relevant documentation",
            "reason": "Find existing solutions and best practices",
            "requires_approval": False
        })
        step_id += 1
    
    # Step 3: Inventory lookup (if mentions devices/servers)
    device_keywords = ["server", "device", "host", "router", "switch", "firewall"]
    if any(keyword in input_lower for keyword in device_keywords):
        steps.append({
            "id": step_id,
            "action": "Lookup target devices in inventory",
            "reason": "Verify device exists and retrieve connection details",
            "requires_approval": False
        })
        step_id += 1
    
    # Step 4: Main action (varies by request type)
    if has_risky_keywords:
        # Risky action - requires approval
        action_desc = f"Execute: {user_input[:60]}"
        if len(user_input) > 60:
            action_desc += "..."
            
        steps.append({
            "id": step_id,
            "action": action_desc,
            "reason": "Primary operation requested by user",
            "requires_approval": True
        })
        step_id += 1
        
        # Step 5: Verification for risky actions
        steps.append({
            "id": step_id,
            "action": "Verify operation completed successfully",
            "reason": "Ensure system state is as expected",
            "requires_approval": False
        })
        step_id += 1
        
    else:
        # Safe query/action
        action_desc = f"Retrieve: {user_input[:60]}"
        if len(user_input) > 60:
            action_desc += "..."
            
        steps.append({
            "id": step_id,
            "action": action_desc,
            "reason": "Gather requested information",
            "requires_approval": False
        })
        step_id += 1
    
    # Step 6: Format response
    steps.append({
        "id": step_id,
        "action": "Format and present results to user",
        "reason": "Provide clear, actionable information",
        "requires_approval": False
    })
    
    return steps


def _create_fallback_plan(reason: str) -> Dict[str, Any]:
    """
    Create a minimal safe fallback plan.
    Used when input is empty or error occurs.
    """
    return {
        "goal": "Handle request safely",
        "assumptions": ["Input validation failed or was empty"],
        "steps": [
            {
                "id": 1,
                "action": "Request clarification from user",
                "reason": f"Cannot proceed: {reason}",
                "requires_approval": False
            }
        ],
        "safety_notes": ["This is a fallback plan due to invalid input"]
    }


def execute_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a plan (if execution is enabled).
    
    Checks EXECUTION_ENABLED config flag.
    Returns execution status and message.
    
    Never raises exceptions.
    
    Args:
        plan: The plan dict from create_plan()
        
    Returns:
        dict: Execution result with 'executed' and 'message' keys
    """
    try:
        # Import here to avoid circular dependency
        from app.config.settings import EXECUTION_ENABLED
        
        if not EXECUTION_ENABLED:
            return {
                "executed": False,
                "message": "Execution is disabled. Enable EXECUTION_ENABLED=true to run actions."
            }
        
        # Execution is enabled but not implemented in v1.x
        # This is a placeholder for future implementation
        return {
            "executed": True,
            "message": "Execution pipeline not implemented in v1.x. Plan generated successfully."
        }
        
    except Exception as e:
        # Never crash
        print(f"[ORCHESTRATOR] ERROR in execute_plan: {e}")
        return {
            "executed": False,
            "message": f"Execution failed: {str(e)}"
        }

