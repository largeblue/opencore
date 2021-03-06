# Copyright (C) 2008-2009 Open Society Institute
#               Thomas Moroz: tmoroz.org
#               2010-2011 Large Blue
#               Fergus Doyle: fergus.doyle@largeblue.com
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License Version 2 as published
# by the Free Software Foundation.  You may not use, modify or distribute
# this program under any other version of the GNU General Public License.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import sqlalchemy as sa
from sqlalchemy import orm
import sqlalchemy.pool as pool
from opencore.models import rdbms

def init_rdbms(engine):
    """Call me before using any RDBMSStore class in the model."""
    sm = orm.sessionmaker(autocommit=True, bind=engine)
    rdbms.sqlEngine = engine
    rdbms.sqlSession = orm.scoped_session(sm)
    sqlEngine = engine
    sqlSession = orm.scoped_session(sm)
    assert(sqlEngine)
    assert(sqlSession)