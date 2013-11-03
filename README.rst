Steward Tasks
=============
This is an extension that adds support for Celery tasks to Steward

Setup
=====
Add the required configuration options to the config.ini file for the server.
Also add steward_tasks to the includes either programmatically::

    config.include('steward_tasks')

or in the config.ini file::

    pyramid.includes =
        steward_tasks

You will need to include steward_tasks before all other extensions, and before
``pyramid_jinja2``

Usage
=====
Steward_tasks is a command, separate from the webserver. The commands mirror
Celery's commands. To start a task worker (which executes tasks), run
``steward-taskworker config.ini``. To start celerybeat, which will run the
periodic, scheduled tasks, run ``steward-taskbeat config.ini``. The recommended
way of running tasks in the background is using supervisord.

Adding Tasks
============
Inside your extension, create a ``tasks.py`` file with the following::

    from steward_tasks import celery, StewardTask

    @celery.task(base=StewardTask)
    def say_hello(name):
        return "Hello %s!" % name

Then add ``yourextension.tasks`` to the ``CELERY_IMPORTS`` section of the
celery.yaml file (see the Configuration section below)

Configuring inside Extensions
=============================
Steward_tasks loads extensions much like pyramid. It imports every module in
`pyramid_includes` and runs the ``include_tasks`` function if present. The
function should accept a ``steward_tasks.TaskConfigurator`` as the only
argument.

You can use this to add mixins (providing more methods to the tasks), schedule
periodic tasks, or mutate the celery configuration. For example, to schedule a
periodic callback::

    def include_tasks(config):
        config.add_scheduled_task('constant_greeting', {
            'task': 'yourextension.tasks.say_hello',
            'schedule': timedelta(minutes=1),
            'args': ['Monty'],
        })


Configuration
=============
::

    # YAML file for configuring logging (required; see logging.dictConfig)
    tasks.log_config = <path-to-yaml-file>

    # YAML file with the celery configuration (required)
    tasks.celery_conf = <path-to-yaml-file>

    # Dotted path to a lock factory implementation. (See steward_tasks.locks)
    tasks.lock_factory = none
