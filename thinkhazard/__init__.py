import os
import ConfigParser

from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from papyrus.renderers import GeoJSON

from .models import (
    DBSession,
    Base,
    )


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """

    load_local_settings(settings)

    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine

    config = Configurator(settings=settings)

    config.include('pyramid_jinja2')
    config.include('papyrus')

    config.add_static_view('static', 'static', cache_max_age=3600,
                           cachebust=True)
    config.add_static_view('lib', settings.get('node_modules'),
                           cache_max_age=86000, cachebust=True)

    config.add_route('index', '/')
    config.add_route('about', '/about')
    config.add_route('faq', '/faq')
    config.add_route('report',
                     '/report/{divisioncode:\d+}/{hazardtype:([A-Z]{2})}')
    config.add_route('report_json',
                     '/report/{divisioncode:\d+}/{hazardtype:([A-Z]{2})}.json')
    config.add_route('report_overview', '/report/{divisioncode:\d+}')
    config.add_route('report_overview_slash', '/report/{divisioncode:\d+}/')
    config.add_route('report_overview_json', '/report/{divisioncode:\d+}.json')
    config.add_route('administrativedivision', '/administrativedivision')
    config.add_route('hazardsets', '/hazardsets')

    config.add_renderer('geojson', GeoJSON())

    config.scan(ignore=['thinkhazard.tests'])
    return config.make_wsgi_app()


def load_local_settings(settings):
    """ Load local/user-specific settings.
    """
    local_settings_path = os.environ.get(
        'LOCAL_SETTINGS_PATH', settings.get('local_settings_path'))
    if local_settings_path and os.path.exists(local_settings_path):
        config = ConfigParser.ConfigParser()
        config.read(local_settings_path)
        settings.update(config.items('app:main'))
