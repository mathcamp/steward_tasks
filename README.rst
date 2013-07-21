Steward Tasks
=============
This is an extension for adding cron-style tasks to Steward.

Setup
=====
Add the required configuration options to the config.ini file for the server. Also add steward_tasks to the includes either programmatically::

    config.include('steward_tasks')

or in the config.ini file::
    pyramid.includes =
        steward_tasks

Usage
=====
Steward_tasks is a command, separate from the webserver. To run it, just type
``steward-tasks config.ini``. This will begin running any tasks. The
recommended way of running tasks in the background is using supervisord.

Adding Tasks
============
Steward_tasks loads extensions much like pyramid. It imports every module in
`pyramid_includes` and runs the ``include_tasks`` function if present. The
function should accept a ``ConfigParser.ConfigParser`` and
``steward_tasks.tasks.TaskList`` as arguments.

To add a task, write a function that you would like to be run periodically.
Then, inside of the ``include_tasks`` block, add it to the tasklist::

    def say_hi():
        print "hello!"

    def include_tasks(config, tasklist):
        tasklist.add(say_hi, '* * * * *')

The schedule may be formatted in multiple ways. Full documentation can be found
on the ``steward_tasks.tasks.Task`` object.

Configuration
=============
::

    # Url for the steward server
    tasks.url = http://localhost:1337

    # Secret token to authorize with the server
    tasks.token = S9A73Xk4TtKTlWzNs55Bk7A+ct/spUgymkuppnKs1/8=

    # YAML file for configuring logging (see logging.dictConfig)
    tasks.log_config = /etc/steward/tasks.yaml

    # How many threads to use for running tasks (default 10)
    tasks.pool_size = 10
