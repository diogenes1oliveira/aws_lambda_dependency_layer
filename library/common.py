from contextlib import wraps


def log_call(logger, f):
    @wraps(f)
    def inner(*args, **kwargs):
        args_str = ''
        if args:
            args_str += ', '.join(repr(a) for a in args)
        if kwargs:
            args_str += (', ' if args else '') + ', '.join(f'{k}={repr(v)}' for k, v in kwargs.items())
        logger.info(f'Called {f.__class__.__name__}.{f.__name__}({args_str})')
        f(*args, **kwargs)
    return inner
