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
import os
from urlparse import urlunsplit
from httplib2 import Http
import transaction

from ..models import (
    DBSession,
    Layer,
    )

from . import load_settings, layer_path


logger = logging.getLogger(__name__)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

logger.setLevel(logging.DEBUG)


def clearall():
    logger.info('Reset all layer to not downloaded state.')
    DBSession.query(Layer).update({
        Layer.downloaded: False
    })
    DBSession.flush()


def download(title=None, force=False, dry_run=False):
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

    geonode_ids = DBSession.query(Layer.geonode_id)

    if not force:
        geonode_ids = geonode_ids.filter(Layer.downloaded.is_(False))

    if title is not None:
        geonode_ids = geonode_ids.filter(Layer.title == title)

    for geonode_id in geonode_ids:
        try:
            download_layer(geonode_id)
            if dry_run:
                transaction.abort()
            else:
                transaction.commit()
        except Exception as e:
            transaction.abort()
            logger.error('{} raise an exception :\n{}'
                         .format(geonode_id, e.message))


def download_layer(geonode_id):
    layer = DBSession.query(Layer).get(geonode_id)
    if layer is None:
        raise Exception('Layer {} does not exist.'.format(geonode_id))

    logger.info('Downloading layer {}'.format(layer.name()))

    dir_path = os.path.dirname(layer_path(layer))
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    settings = load_settings()
    geonode = settings['geonode']
    if os.path.isfile(layer_path(layer)):
        layer.downloaded = True
    else:
        h = Http()
        url = urlunsplit((geonode['scheme'],
                          geonode['netloc'],
                          layer.download_url,
                          '',
                          ''))
        logger.info('Retrieving {}'.format(url))
        response, content = h.request(url)

        try:
            with open(layer_path(layer), 'wb') as f:
                f.write(content)
                layer.downloaded = True
        except EnvironmentError:
            logger.error('Writing data from layer {} failed'.format(
                layer.name()))

    DBSession.flush()
