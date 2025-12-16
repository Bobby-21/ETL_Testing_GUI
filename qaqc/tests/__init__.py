import pkgutil
import importlib

# Dynamically import all modules in this package so that the @register decorator
# is executed for all test functions.
for _, module_name, _ in pkgutil.iter_modules(__path__):
    importlib.import_module(f".{module_name}", package=__name__)
