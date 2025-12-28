"""
Tests for app/core/orchestrator.py

Validates deterministic plan generation and execution gating.
"""

import pytest
from app.core.orchestrator import create_plan, execute_plan


class TestCreatePlan:
    """Test plan generation logic."""
    
    def test_create_plan_returns_dict(self):
        """Plan should always return a dict."""
        plan = create_plan("check server status")
        assert isinstance(plan, dict)
    
    def test_create_plan_has_required_fields(self):
        """Plan should have goal and steps fields."""
        plan = create_plan("restart nginx")
        
        assert "goal" in plan
        assert "steps" in plan
        assert "assumptions" in plan
        assert "safety_notes" in plan
    
    def test_create_plan_steps_is_list(self):
        """Steps should be a list."""
        plan = create_plan("list all servers")
        
        assert isinstance(plan["steps"], list)
    
    def test_create_plan_max_10_steps(self):
        """Plan should have at most 10 steps."""
        # Even with complex input, should cap at 10
        plan = create_plan("restart all servers and check status and verify logs and backup data")
        
        assert len(plan["steps"]) <= 10
    
    def test_create_plan_empty_input(self):
        """Empty input should return minimal fallback plan."""
        plan = create_plan("")
        
        assert isinstance(plan, dict)
        assert "goal" in plan
        assert "steps" in plan
        assert len(plan["steps"]) == 1  # Fallback has 1 step
    
    def test_create_plan_whitespace_input(self):
        """Whitespace-only input should return fallback plan."""
        plan = create_plan("   \n\t  ")
        
        assert isinstance(plan, dict)
        assert len(plan["steps"]) == 1
    
    def test_create_plan_risky_keyword_restart(self):
        """Keyword 'restart' should flag at least one step for approval."""
        plan = create_plan("restart nginx on server1")
        
        # At least one step should require approval
        approval_steps = [s for s in plan["steps"] if s.get("requires_approval", False)]
        assert len(approval_steps) >= 1
    
    def test_create_plan_risky_keyword_delete(self):
        """Keyword 'delete' should flag at least one step for approval."""
        plan = create_plan("delete old log files")
        
        approval_steps = [s for s in plan["steps"] if s.get("requires_approval", False)]
        assert len(approval_steps) >= 1
    
    def test_create_plan_risky_keyword_shutdown(self):
        """Keyword 'shutdown' should flag at least one step for approval."""
        plan = create_plan("shutdown server for maintenance")
        
        approval_steps = [s for s in plan["steps"] if s.get("requires_approval", False)]
        assert len(approval_steps) >= 1
    
    def test_create_plan_safe_query(self):
        """Safe query should not require approval."""
        plan = create_plan("show server status")
        
        # All steps should be safe (no approval needed)
        approval_steps = [s for s in plan["steps"] if s.get("requires_approval", False)]
        assert len(approval_steps) == 0
    
    def test_create_plan_goal_truncated(self):
        """Goal should be truncated to 120 characters."""
        long_input = "a" * 200
        plan = create_plan(long_input)
        
        # Goal should be at most 123 chars (120 + "...")
        assert len(plan["goal"]) <= 123
    
    def test_create_plan_deterministic(self):
        """Same input should produce same plan (deterministic)."""
        input_text = "check nginx status on web01"
        
        plan1 = create_plan(input_text)
        plan2 = create_plan(input_text)
        
        # Plans should be identical
        assert plan1["goal"] == plan2["goal"]
        assert len(plan1["steps"]) == len(plan2["steps"])
        
        # Step IDs should match
        for i, step in enumerate(plan1["steps"]):
            assert step["id"] == plan2["steps"][i]["id"]
            assert step["action"] == plan2["steps"][i]["action"]
    
    def test_create_plan_never_raises(self):
        """Plan creation should never raise exceptions."""
        # Try various problematic inputs
        test_inputs = [
            None,  # Will be handled as falsy
            "",
            "   ",
            "a" * 10000,  # Very long
            "special chars: !@#$%^&*()",
            "unicode: 你好世界 🚀",
        ]
        
        for test_input in test_inputs:
            try:
                if test_input is None:
                    plan = create_plan("")  # Convert None to empty string
                else:
                    plan = create_plan(test_input)
                assert isinstance(plan, dict)
            except Exception as e:
                pytest.fail(f"create_plan raised exception for input '{test_input}': {e}")


class TestExecutePlan:
    """Test plan execution logic."""
    
    def test_execute_plan_returns_dict(self):
        """Execution should always return a dict."""
        plan = create_plan("test")
        result = execute_plan(plan)
        
        assert isinstance(result, dict)
    
    def test_execute_plan_has_executed_field(self):
        """Result should have 'executed' boolean field."""
        plan = create_plan("test")
        result = execute_plan(plan)
        
        assert "executed" in result
        assert isinstance(result["executed"], bool)
    
    def test_execute_plan_has_message_field(self):
        """Result should have 'message' string field."""
        plan = create_plan("test")
        result = execute_plan(plan)
        
        assert "message" in result
        assert isinstance(result["message"], str)
    
    def test_execute_plan_disabled_by_default(self):
        """Execution should be disabled by default (EXECUTION_ENABLED=false)."""
        plan = create_plan("restart nginx")
        result = execute_plan(plan)
        
        # Default config has EXECUTION_ENABLED=false
        assert result["executed"] is False
        assert "disabled" in result["message"].lower()
    
    def test_execute_plan_never_raises(self):
        """Execution should never raise exceptions."""
        # Try with various plan structures
        test_plans = [
            {},
            {"goal": "test"},
            {"steps": []},
            None,  # Invalid input
        ]
        
        for plan in test_plans:
            try:
                if plan is None:
                    result = execute_plan({})  # Convert None to empty dict
                else:
                    result = execute_plan(plan)
                assert isinstance(result, dict)
            except Exception as e:
                pytest.fail(f"execute_plan raised exception for plan '{plan}': {e}")


class TestIntegration:
    """Integration tests for plan creation and execution flow."""
    
    def test_full_workflow_safe_query(self):
        """Test complete workflow for safe query."""
        # 1. Create plan
        plan = create_plan("show all servers")
        
        assert isinstance(plan, dict)
        assert len(plan["steps"]) > 0
        
        # 2. Verify no approval needed
        approval_steps = [s for s in plan["steps"] if s.get("requires_approval", False)]
        assert len(approval_steps) == 0
        
        # 3. Execute (should be disabled)
        result = execute_plan(plan)
        assert result["executed"] is False
    
    def test_full_workflow_risky_action(self):
        """Test complete workflow for risky action."""
        # 1. Create plan
        plan = create_plan("restart all production servers")
        
        assert isinstance(plan, dict)
        
        # 2. Verify approval required
        approval_steps = [s for s in plan["steps"] if s.get("requires_approval", False)]
        assert len(approval_steps) >= 1
        
        # 3. Execute (should be disabled)
        result = execute_plan(plan)
        assert result["executed"] is False

