""" Endpoints for tasks """
from celery.app.control import Inspect
from pyramid.view import view_config

from . import celery


@view_config(route_name='tasks_active', renderer='json')
def do_active(request):
    """ Get all active tasks by worker """
    inspect = Inspect(app=celery)
    return inspect.active()


@view_config(route_name='tasks_registered', renderer='json')
def do_registered(request):
    """ Get a list of all registered tasks """
    inspect = Inspect(app=celery)
    return inspect.registered()


@view_config(route_name='tasks_reserved', renderer='json')
def do_reserved(request):
    """ Get all tasks that have been reserved but are not executing """
    inspect = Inspect(app=celery)
    return inspect.reserved()


@view_config(route_name='tasks_scheduled', renderer='json')
def do_scheduled(request):
    """ Get a list of all tasks waiting to be scheduled """
    inspect = Inspect(app=celery)
    return inspect.scheduled()
