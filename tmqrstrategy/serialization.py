from tmqr.errors import ArgumentError
from pydoc import locate


def object_to_full_path(obj) -> str:
    """
    Converts object instance to full-qualified path like 'package.module.ClassName'
    :param obj: any object class
    :return:
    """
    module_name = obj.__module__

    if module_name == '__main__':
        raise ArgumentError(f"Serialization of objects from '__main__' namespace is not allowed, if you are using "
                            f"Jupyter/IPython session try to save class object to separate module.")

    try:
        # In case when the object is Class (i.e. type itself)
        return f"{module_name}.{obj.__qualname__}"
    except AttributeError:
        # The case when the object is class instance
        return f"{module_name}.{obj.__class__.__name__}"


def object_from_path(obj_path):
    """
    Loads object class from full-qualified path like 'package.module.ClassName'
    :param obj_path: full-qualified path like 'package.module.ClassName'
    :return:
    """
    obj = locate(obj_path)

    if obj is None:
        raise ArgumentError(f"Failed to load object from {obj_path}. Try to check that object path is valid "
                            f"and package path in the $PYTHONPATH environment variable")

    return obj
