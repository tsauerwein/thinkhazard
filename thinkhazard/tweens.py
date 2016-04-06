# -*- coding: utf-8 -*-
#
# Copyright (C) 2015- by the GFDRR / World Bank
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

import pytz
from pyramid.httpexceptions import HTTPNotModified

from .models import Publication


def notmodified_tween_factory(handler, registry):

    if registry.settings['appname'] == 'public':
        gmt = pytz.timezone('GMT')
        publication_date = gmt.localize(Publication.last().date)

        def notmodified_tween(request):
            if (request.if_modified_since is not None and
                    request.if_modified_since >=
                    publication_date.replace(microsecond=0)):
                return HTTPNotModified()

            response = handler(request)

            response.last_modified = publication_date

            return response

        return notmodified_tween

    return handler