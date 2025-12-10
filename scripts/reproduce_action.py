import chainlit as cl
import json

try:
    print("Attempting to create Action...")
    action_data = {"hostname": "SRV-01", "command": "show platform resources", "reason": "Testing"}
    
    # Simulate the call exactly as in chat.py
    act = cl.Action(
        name="approve_execution", 
        value=json.dumps(action_data), 
        label="✅ ODOBRI", 
        description=f"Run {action_data.get('command')}"
    )
    print("Success:", act)
except Exception as e:
    print("Caught Exception:")
    print(e)

print("-" * 20)
print("Checking Action fields via Pydantic...")
try:
    # Print schema or fields if possible
    print(cl.Action.model_json_schema())
except:
    pass
