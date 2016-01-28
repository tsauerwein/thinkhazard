from pyramid.view import view_config

from ..models import (
    DBSession,
    HazardLevel,
    HazardType,
    )


@view_config(route_name='admin_index', renderer='templates/admin_index.jinja2')
def index(request):
    hazard_types = DBSession.query(HazardType).order_by(HazardType.order)
    hazard_levels = []
    for level in [u'HIG', u'MED', u'LOW', u'VLO']:
        hazard_levels.append(HazardLevel.get(level))
    return {
        'hazard_types': hazard_types,
        'hazard_levels': hazard_levels,
        }
