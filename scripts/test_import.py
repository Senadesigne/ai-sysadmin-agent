
try:
    from chainlit.types import PersistedUser
    print(f"SUCCESS: Imported from chainlit.types: {PersistedUser}")
except ImportError as e:
    print(f"FAILED chainlit.types: {e}")

try:
    from chainlit.user import PersistedUser
    print(f"SUCCESS: Imported from chainlit.user: {PersistedUser}")
except ImportError as e:
    print(f"FAILED chainlit.user: {e}")

try:
    from chainlit.data import PersistedUser
    print(f"SUCCESS: Imported from chainlit.data: {PersistedUser}")
except ImportError as e:
    print(f"FAILED chainlit.data: {e}")

try:
    from chainlit.data.literalai import PersistedUser
    print(f"SUCCESS: Imported from chainlit.data.literalai: {PersistedUser}")
except ImportError as e:
    print(f"FAILED chainlit.data.literalai: {e}")
