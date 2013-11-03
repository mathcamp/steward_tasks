""" Tools for synchronizing requests and blocks """
import os

import contextlib
import functools
from collections import defaultdict
from multiprocessing import RLock


class LockAnnotation(object):
    """
    Lock provider

    ::

        @celery.task(base=StewardTask)
        @lock('mytask', expire=300, timeout=500)
        def mytask():
            # do something locked

    Inline locks::

        @celery.task(base=StewardTask)
        def say_hello(name):
            with lock.inline('hello_%s' % name):
                return "Hello %s!" % name

    """
    def __init__(self, factory):
        self._factory = factory

    def __call__(self, key, expire=None, timeout=None):
        """ Decorator for synchronizing a request """
        def wrapper(fxn):
            """ Wrapper for the synchronized request handler """
            @functools.wraps(fxn)
            def wrapped(*args, **kwargs):
                """ Acquire lock and call a function """
                with self._factory(key, expire=expire, timeout=timeout):
                    return fxn(*args, **kwargs)
            return wrapped
        return wrapper

    def inline(self, key, expire=None, timeout=None):
        """ Get a lock instance from the factory """
        return self._factory(key, expire=expire, timeout=timeout)


@contextlib.contextmanager
def noop():
    """ A no-op lock """
    yield


@contextlib.contextmanager
def file_lock(filename):
    """ Acquire a lock on a file using ``flock`` """
    import fcntl
    with open(filename, "w") as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_EX)
        yield


class ILockFactory(object):
    """
    Interface for generating locks

    Extend this class to use a different kind of lock for all of the
    synchronization in Steward.

    Parameters
    ----------
    settings : dict
        The application's settings

    """
    def __init__(self, settings):
        self._settings = settings

    def __call__(self, key, expire=None, timeout=None):
        """
        Create a lock unique to the key

        Parameters
        ----------
        key : str
            Unique key to identify the lock to return
        expire : float, optional
            Maximum amount of time the lock may be held (default infinite)
        timeout : float, optional
            Maximum amount of time to wait to acquire the lock before rasing an
            exception (default infinite)

        Notes
        -----
        Not all ILockFactory implementations will respect the ``expire``
        and/or ``timeout`` options. Please refer to the implementation for
        details.

        """
        raise NotImplementedError


class DummyLockFactory(ILockFactory):
    """ No locking will occur """
    def __call__(self, key, expire=None, timeout=None):
        return noop()


class ProcessLockFactory(ILockFactory):
    """ Generate multiprocessing RLocks """
    def __init__(self, settings):
        super(ProcessLockFactory, self).__init__(settings)
        self._lock = RLock()
        self._locks = defaultdict(RLock)

    def __call__(self, key, expire=None, timeout=None):
        with self._lock:
            return self._locks[key]


class FileLockFactory(ILockFactory):
    """ Generate file-level locks that use ``flock`` """
    def __init__(self, settings):
        super(FileLockFactory, self).__init__(settings)
        self._lockdir = self._settings.get('steward.lock_dir',
                                           '/var/run/steward_locks/')
        if not os.path.exists(self._lockdir):
            os.makedirs(self._lockdir)

    def __call__(self, key, expire=None, timeout=None):
        return file_lock(os.path.join(self._lockdir, key))
