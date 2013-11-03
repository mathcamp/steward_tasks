""" Task objects """
import logging

from . import celery, StewardTask


LOG = logging.getLogger(__name__)


@celery.task(base=StewardTask)
def pub(name, data=None):
    """
    Publish an event and run all handlers for it

    Parameters
    ----------
    name : str
        The name of the event
    data : dict, optional
        The payload dict for the event

    """
    data = data or {}
    for handler in pub.config.event_handlers:
        pattern = handler['pattern']
        callback = handler['callback']
        match = pattern.match(name)
        if match:
            try:
                if pattern.groups:
                    retval = callback(pub, data, *match.groups())
                else:
                    retval = callback(pub, data)
                if retval is True:
                    LOG.info("Sending event %s has been blocked by "
                             "event handler %s", name, callback.__name__)
                    return
            except:
                LOG.exception("Error running event handler!")


@celery.task(base=StewardTask)
def config_settings():
    """ Retrieve the config.ini settings """
    return config_settings.config.settings
