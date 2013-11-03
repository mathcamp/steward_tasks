""" Steward tool for running tasks """
import os
import re

import importlib
import logging.config
import yaml
from ConfigParser import ConfigParser
from celery import Celery, Task
from celery.datastructures import ExceptionInfo
from celery.states import SUCCESS, FAILURE
from pyramid.path import DottedNameResolver

from . import locks


# pylint: disable=C0103

class ImportWarningClass(object):

    """ Dummy class that raises exceptions if called before replaced """
    def __call__(self, *_, **__):
        raise ValueError("You must include 'steward_tasks' before all other "
                         "Steward extensions and before 'pyramid_jinja2'")

    def __getattribute__(self, name):
        return self

lock = ImportWarningClass()
celery = ImportWarningClass()


def read_config(conf_file):
    """ Read conf file and return a :class:`TaskConfigurator` """
    if isinstance(conf_file, dict):
        settings = conf_file
    else:
        here = os.path.dirname(os.path.abspath(conf_file))
        config = ConfigParser({'here': here})
        config.read(conf_file)
        section = None
        for section in config.sections():
            if section.startswith('app:'):
                section = section
                break
        if section is None:
            raise ValueError("Could not find 'app:' section in config file!")

        settings = dict(config.items(section))

    # configure celery
    celery_conf_file = settings['tasks.celery_conf']
    with open(celery_conf_file, 'r') as infile:
        celery_settings = yaml.safe_load(infile)

    return TaskConfigurator(settings, celery_settings)


class BaseStewardTask(Task):  # pylint: disable=W0223

    """ Base class for Steward tasks """
    abstract = True
    config = None
    callbacks = []

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        for callback in self.callbacks:
            callback(self, status, retval, task_id, args, kwargs, einfo)

    def __call__(self, *args, **kwargs):
        einfo = None
        status = SUCCESS
        try:
            retval = super(BaseStewardTask, self).__call__(*args, **kwargs)
            self.after_return(status, retval, 0, args, kwargs, einfo)
            return retval
        except Exception as e:
            retval = e
            import sys
            status = FAILURE
            einfo = ExceptionInfo(sys.exc_info())
            self.after_return(status, retval, 0, args, kwargs, einfo)
            raise


class StewardTask(BaseStewardTask):  # pylint: disable=W0223

    """
    Dummy class that will be replaced by a class with additional mixed-in
    methods

    """


class Registry(object):

    """ Simple container object for getting/setting attributes """
    def __init__(self, settings):
        self.settings = settings


class TaskConfigurator(object):
    """
    Config object that wraps all configuration data

    Loosely mirrors the pyramid Configurator object

    Parameters
    ----------
    settings : dict
        Settings from the config.ini file
    celery_settings : dict
        Settings from the celery.yaml file

    Attributes
    ----------
    settings : dict
    celery_settings : dict
    mixins : list
        List of objects that will be mixed-in to the base StewardTask object.
        This is similar to pyramid's ``config.add_request_method``.
    event_handlers : list
        List of entries for event handlers (contains 'pattern', 'callback', and
        'priority')
    registry : object
        Mostly-empty object that exists to get/set attributes onto.

    """

    def __init__(self, settings, celery_settings):
        self.settings = settings
        self.celery_settings = celery_settings
        self.mixins = []
        self.event_handlers = []
        self._name_resolver = DottedNameResolver(__package__)
        self.registry = Registry(settings)

    def add_event_handler(self, pattern, callback, priority=100):
        """
        Add a method that will be called when a matching event is published

        Parameters
        ----------
        pattern : str
            A regex that will match event names
        callback : callable
            Called when an event is published that matches the pattern. The
            arguments are callback(current_task, event_payload). If the pattern
            regex contains any groups, those are passed in as args. Should
            return None. If the callback returns True, no further event
            handlers will be run.
        priority : int, optional
            Determines the ordering of the event_handler. Higher runs sooner.
            (default 100)

        """
        index = 0
        regex = re.compile('^' + pattern)
        while index < len(self.event_handlers):
            h_priority = self.event_handlers[index]['priority']
            if priority > h_priority:
                break
            index += 1
        self.event_handlers.insert(index, {
            'pattern': regex,
            'callback': callback,
            'priority': priority,
        })

    def add_scheduled_task(self, name, config_dict):
        """
        Add a task for periodic execution

        Parameters
        ----------
        name : str
            Unique name of the periodic task
        config_dict : dict
            Same format as the Celery CELERYBEAT_SCHEDULE entries

        """
        self.celery_settings.setdefault('CELERYBEAT_SCHEDULE', {})
        self.celery_settings['CELERYBEAT_SCHEDULE'][name] = config_dict

    def finish(self):
        """ Called after all global celery objects have been created """
        for handler in self.event_handlers:
            handler['callback'] = self._name_resolver.maybe_resolve(
                handler['callback'])


def includeme(config):
    """ Configure the app """
    settings = config.get_settings()
    init_celery(settings)


def init_celery(conf_file):
    """ Initialize the global celery app objects """
    # pylint: disable=W0603
    global celery
    global StewardTask  # pylint: disable=W0601
    global lock

    config = read_config(conf_file)

    # configure logging
    log_config = config.settings['tasks.log_config']
    with open(log_config, 'r') as infile:
        logging.config.dictConfig(yaml.safe_load(infile))

    includes = config.settings['pyramid.includes'].split()
    for package in includes:
        mod = importlib.import_module(package)
        if hasattr(mod, 'include_tasks'):
            mod.include_tasks(config)

    StewardTask = type('StewardTask', tuple(config.mixins + [
                       BaseStewardTask]), {'abstract': True, 'config': config})

    factory_name = config.settings.get('tasks.lock_factory', 'none')
    if factory_name == 'none':
        factory_name = 'steward_tasks.locks.DummyLockFactory'
    elif factory_name == 'proc':
        factory_name = 'steward_tasks.locks.ProcessLockFactory'
    elif factory_name == 'file':
        factory_name = 'steward_tasks.locks.FileLockFactory'
    name_resolver = DottedNameResolver(__package__)
    factory = name_resolver.resolve(factory_name)(config.settings)
    lock = locks.LockAnnotation(factory)

    celery = Celery('steward_tasks', config_source=config.celery_settings)

    config.finish()


def worker():
    """ Start running Steward tasks """
    import sys
    if len(sys.argv) < 2:
        print "usage: steward-tasks config_uri [celery opts]"
        sys.exit(1)

    init_celery(sys.argv.pop(1))

    celery.worker_main()


def beat():
    """ Start running celerybeat """
    import sys
    from celery.utils.imports import instantiate
    if len(sys.argv) < 2:
        print "usage: steward-tasks config_uri [celery opts]"
        sys.exit(1)

    init_celery(sys.argv.pop(1))

    try:
        instantiate(
            'celery.bin.celerybeat:BeatCommand',
            app=celery).execute_from_commandline(sys.argv)
    except ImportError:
        instantiate(
            'celery.bin.beat:beat',
            app=celery).execute_from_commandline(sys.argv)
