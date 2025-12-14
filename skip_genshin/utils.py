def track_changes(name: str, true_message: str, false_message: str):
    """
    Decorator that tracks boolean changes in function return values.
    Prints the name and the corresponding message when a change is detected.
    """
    last_value = None

    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal last_value
            current_value = func(*args, **kwargs)

            if last_value is None or current_value != last_value:
                if current_value:
                    print(f"{name}: {true_message}")
                else:
                    print(f"{name}: {false_message}")

            last_value = current_value
            return current_value

        return wrapper

    return decorator
