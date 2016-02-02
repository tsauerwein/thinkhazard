# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 by the GFDRR / World Bank
#
# This file is part of ThinkHazard.
#
# ThinkHazard is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# ThinkHazard is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# ThinkHazard.  If not, see <http://www.gnu.org/licenses/>.

import logging
import httplib2
from urllib import urlencode
from urlparse import urlunsplit
import json
import transaction
from datetime import datetime

from ..models import (
    DBSession,
    HazardLevel,
    HazardSet,
    HazardType,
    Layer,
    Output,
    )

from . import settings


logger = logging.getLogger(__name__)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

logger.setLevel(logging.DEBUG)


geonode = settings['geonode']


def clearall():
    logger.info('Cleaning previous data')
    DBSession.query(Output).delete()
    DBSession.query(Layer).delete()
    DBSession.query(HazardSet).delete()
    DBSession.flush()


def harvest(hazard_type=None, force=False, dry_run=False):
    if force:
        try:
            clearall()
            if dry_run:
                transaction.abort()
            else:
                transaction.commit()
        except:
            transaction.abort()
            raise

    params = {}
    if hazard_type is not None:
        params['hazard_type__in'] = hazard_type

    hazard_type_url = urlunsplit((geonode['scheme'],
                                  geonode['netloc'],
                                  'api/layers/',
                                  urlencode(params),
                                  ''))

    logger.info('Retrieving {}'.format(hazard_type_url))
    h = httplib2.Http()
    response, content = h.request(hazard_type_url)
    metadata = json.loads(content)

    objects = sorted(metadata['objects'], key=lambda object: object['title'])

    for object in objects:
        if harvest_layer(object):
            try:
                if dry_run:
                    transaction.abort()
                else:
                    transaction.commit()
            except Exception as e:
                transaction.abort()
                logger.error('{} raise an exception :\n{}'
                             .format(object['title'], e.message))


def harvest_layer(object, dry_run=False):
    title = object['title']

    hazardset_id = object['hazard_set']
    if not hazardset_id:
        logger.info('{} - hazard_set is empty'.format(title))
        return False

    hazard_type = object['hazard_type']
    if not hazard_type:
        logger.warning('{} - hazard_type is empty'.format(title))
        return False
    hazardtype = hazardtype_from_geonode(hazard_type)
    if hazardtype is None:
        logger.warning('{} - hazard_type not supported: {}'
                       .format(title, hazard_type))
        return False

    type_settings = settings['hazard_types'][hazardtype.mnemonic]
    preprocessed = 'values' in type_settings

    local = 'GLOBAL' not in hazardset_id

    mask = False
    if preprocessed is True:
        hazardlevel = None
        hazard_unit = None
        if object['hazard_period']:
            logger.info('{} - Has a return period'.format(title))
            return False
        hazard_period = None
    else:
        hazard_period = int(object['hazard_period'])
        hazardlevel = None
        for level in (u'LOW', u'MED', u'HIG'):
            return_periods = type_settings['return_periods'][level]
            if isinstance(return_periods, list):
                if (hazard_period >= return_periods[0] and
                        hazard_period <= return_periods[1]):
                    hazardlevel = HazardLevel.get(level)
                    break
            else:
                if hazard_period == return_periods:
                    hazardlevel = HazardLevel.get(level)

        if ('mask_return_period' in type_settings and
                hazard_period == type_settings['mask_return_period']):
            mask = True

        if hazardlevel is None and not mask:
            logger.info('{} - No corresponding hazard_level'.format(title))
            return False

        hazard_unit = object['hazard_unit']
        if hazard_unit == '':
            logger.info('{} -  hazard_unit is empty'.format(title))
            return False

    if object['srid'] != 'EPSG:4326':
        logger.info('{} - srid is different from "EPSG:4326"'
                    .format(title))
        return False

    data_update_date = parse_date(object['data_update_date'])
    if not data_update_date:
        logger.warning('{} - data_update_date is empty'.format(title))
        # We use a very old date for good comparison in decision tree
        data_update_date = datetime.fromtimestamp(0)

    metadata_update_date = parse_date(object['metadata_update_date'])
    if not metadata_update_date:
        logger.warning('{} - metadata_update_date is empty'.format(title))
        # We use a very old date for good comparison in decision tree
        metadata_update_date = datetime.fromtimestamp(0)

    calculation_method_quality = object['calculation_method_quality']
    if not calculation_method_quality:
        logger.warning('{} - calculation_method_quality is empty'
                       .format(title))
        return False
    calculation_method_quality = int(float(calculation_method_quality))

    scientific_quality = object['scientific_quality']
    if not scientific_quality:
        logger.warning('{} - scientific_quality is empty'.format(title))
        return False
    scientific_quality = int(float(scientific_quality))

    download_url = object['download_url']
    if not download_url:
        logger.warning('{} - download_url is empty'.format(title))
        return False

    hazardset = DBSession.query(HazardSet).get(hazardset_id)

    # Test if another layer exists for same hazardlevel (or mask)
    layer = DBSession.query(Layer) \
        .filter(Layer.geonode_id != object['id']) \
        .filter(Layer.hazardset_id == hazardset_id)
    if hazardlevel is not None:
        layer = layer.filter(Layer.hazardlevel_id == hazardlevel.id)
    if mask:
        layer = layer.filter(Layer.mask.is_(True))
    layer = layer.first()
    if layer is not None:
        if hazard_period > layer.return_period:
            logger.info('{} - Superseded by shorter return period {}'
                        .format(title, layer.return_period))
            return False
        logger.info('{} - Supersede longer return period {}'
                    .format(title, layer.return_period))
        DBSession.delete(layer)
        hazardset.complete = False
        hazardset.processed = False

    # Create hazardset before layer
    if hazardset is None:
        logger.info('{} - Create new hazardset {}'
                    .format(title, hazardset_id))
        hazardset = HazardSet()
        hazardset.id = hazardset_id
        hazardset.hazardtype = hazardtype
        DBSession.add(hazardset)

    # get distribution_url and owner_organization from last updated layer
    if object['distribution_url']:
        hazardset.distribution_url = object['distribution_url']
    if object['owner__organization']:
        hazardset.owner_organization = object['owner__organization']

    layer = DBSession.query(Layer).get(object['id'])
    if layer is None:
        logger.info('{} - Create new Layer {}'.format(title, title))
        layer = Layer()
        layer.geonode_id = object['id']
        DBSession.add(layer)
        hazardset.complete = False
        hazardset.processed = False

    else:
        # If data has changed
        if (layer.data_lastupdated_date != data_update_date or
                layer.download_url != download_url):
            logger.info('{} - Invalidate downloaded'.format(title))
            layer.downloaded = False
            hazardset.completed = False
            hazardset.processed = False

        # Some hazardset fields are calculated during completing
        if (layer.calculation_method_quality != calculation_method_quality or
                layer.scientific_quality != scientific_quality or
                layer.data_lastupdated_date != data_update_date or
                layer.metadata_lastupdated_date != metadata_update_date):
            logger.info('{} - Invalidate completed'.format(title))
            hazardset.completed = False

        # Some fields invalidate outputs
        if (layer.hazardunit != hazard_unit):
            logger.info('{} - Invalidate processed'.format(title))
            hazardset.processed = False

    layer.hazardset = hazardset
    layer.hazardlevel = hazardlevel
    layer.mask = mask
    layer.return_period = hazard_period
    layer.hazardunit = hazard_unit
    layer.data_lastupdated_date = data_update_date
    layer.metadata_lastupdated_date = metadata_update_date
    layer.download_url = download_url

    # TODO: retrieve quality attributes
    layer.calculation_method_quality = calculation_method_quality
    layer.scientific_quality = scientific_quality
    layer.local = local

    DBSession.flush()
    return True


def hazardtype_from_geonode(geonode_name):
    for mnemonic, type_settings in settings['hazard_types'].iteritems():
        if type_settings['hazard_type'] == geonode_name:
            return HazardType.get(unicode(mnemonic))
    return None


def parse_date(str):
    if str is None or len(str) == 0:
        return None
    if '.' in str:
        return datetime.strptime(str, '%Y-%m-%dT%H:%M:%S.%f')
    else:
        return datetime.strptime(str, '%Y-%m-%dT%H:%M:%S')
