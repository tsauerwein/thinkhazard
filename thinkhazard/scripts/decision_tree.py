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

import sys
import argparse
from sqlalchemy import engine_from_config

from ..models import DBSession

from ..processing import load_settings
from ..processing.decisiontree import apply_decision_tree


def main(argv=sys.argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--dry-run', dest='dry_run',
        action='store_const', const=True, default=False,
        help='Perform a trial run that does not commit changes')
    args = parser.parse_args(argv[1:])

    settings = load_settings()
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)

    apply_decision_tree(dry_run=args.dry_run)
