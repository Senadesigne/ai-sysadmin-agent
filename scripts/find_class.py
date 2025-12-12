
import pkgutil
import importlib
import inspect
import chainlit

def find_class(package, class_name):
    path = package.__path__
    prefix = package.__name__ + "."

    for module_info in pkgutil.walk_packages(path, prefix):
        try:
            module = importlib.import_module(module_info.name)
            if hasattr(module, class_name):
                cls = getattr(module, class_name)
                if inspect.isclass(cls):
                    print(f"FOUND: {class_name} in {module_info.name}")
                    return
        except Exception:
            pass

print("Searching for PersistedUser...")
find_class(chainlit, "PersistedUser")
