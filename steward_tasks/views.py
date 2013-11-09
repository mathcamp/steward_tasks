""" Endpoints for tasks """
from celery.app.control import Inspect
from pyramid.view import view_config

from . import celery


@view_config(route_name='tasks_active', renderer='json')
def do_active(request):
    inspect = Inspect(app=celery)
    return inspect.active()


@view_config(route_name='tasks_registered', renderer='json')
def do_registered(request):
    inspect = Inspect(app=celery)
    return inspect.registered()


@view_config(route_name='tasks_reserved', renderer='json')
def do_reserved(request):
    inspect = Inspect(app=celery)
    return inspect.reserved()


@view_config(route_name='tasks_scheduled', renderer='json')
def do_scheduled(request):
    inspect = Inspect(app=celery)
    return inspect.scheduled()
