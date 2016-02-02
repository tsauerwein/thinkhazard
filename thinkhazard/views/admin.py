from pyramid.view import view_config
from pyramid.httpexceptions import (
    HTTPFound,
    HTTPNotFound,
    )

from ..models import (
    DBSession,
    HazardCategory,
    HazardCategoryTechnicalRecommendationAssociation as HcTr,
    HazardLevel,
    HazardType,
    )


@view_config(route_name='admin_index',
             renderer='templates/admin/index.jinja2')
def index(request):
    hazard_types = DBSession.query(HazardType).order_by(HazardType.order)
    hazard_levels = []
    for level in [u'HIG', u'MED', u'LOW', u'VLO']:
        hazard_levels.append(HazardLevel.get(level))
    return {
        'hazard_types': hazard_types,
        'hazard_levels': hazard_levels,
        }


@view_config(route_name='admin_hazardcategory',
             renderer='templates/admin/hazardcategory.jinja2')
def hazardcategory(request):
    hazard_type = request.matchdict['hazard_type']
    hazard_level = request.matchdict['hazard_level']

    if request.method == 'GET':
        hazard_category = DBSession.query(HazardCategory) \
            .join(HazardType) \
            .join(HazardLevel) \
            .filter(HazardType.mnemonic == hazard_type) \
            .filter(HazardLevel.mnemonic == hazard_level) \
            .one()
        if hazard_category is None:
            raise HTTPNotFound()

        associations = DBSession.query(HcTr) \
            .filter(HcTr.hazardcategory_id == hazard_category.id) \
            .order_by(HcTr.order) \
            .all()

        return {
            'action': request.route_url('admin_hazardcategory',
                                        hazard_type=hazard_type,
                                        hazard_level=hazard_level),
            'hazard_category': hazard_category,
            'associations': associations
            }

    if request.method == 'POST':
        hazard_category = DBSession.query(HazardCategory) \
            .get(request.POST.get('id'))
        if hazard_category is None:
            raise HTTPNotFound()

        hazard_category.general_recommendation = \
            request.POST.get('general_recommendation')

        associations = request.POST.getall('associations[]')
        order = 0
        for association_id in associations:
            order += 1
            association = DBSession.query(HcTr).get(association_id)
            association.order = order
        return HTTPFound(request.route_url('admin_hazardcategory',
                                           hazard_type=hazard_type,
                                           hazard_level=hazard_level))
