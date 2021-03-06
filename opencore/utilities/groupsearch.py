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

from zope.interface import directlyProvides
from zope.interface import implements

from repoze.bfg.security import effective_principals
from repoze.bfg.traversal import model_path

from opencore.models.interfaces import ICatalogSearch
from opencore.models.interfaces import IGroupSearchFactory
from opencore.models.interfaces import IGroupSearch
from opencore.models.interfaces import IPeople
from opencore.models.interfaces import IPosts
from opencore.models.interfaces import IFiles
from opencore.models.interfaces import IPages
from opencore.models.interfaces import IOthers

from opencore.views.batch import get_catalog_batch_grid

def groupsearchfactory(unwrapped):
    directlyProvides(unwrapped, IGroupSearchFactory)
    return unwrapped

@groupsearchfactory
def people_group_search(context, request, term):
    search = GroupSearch(context, request, [IPeople], term)
    return search

@groupsearchfactory
def pages_group_search(context, request, term):
    search = GroupSearch(context, request, [IPages], term)
    return search

@groupsearchfactory
def posts_group_search(context, request, term):
    search = GroupSearch(context, request, [IPosts], term)
    return search

@groupsearchfactory
def files_group_search(context, request, term):
    search = GroupSearch(context, request, [IFiles], term)
    return search

@groupsearchfactory
def others_group_search(context, request, term):
    search = GroupSearch(context, request, [IOthers], term)
    return search

class GroupSearch:
    implements(IGroupSearch)
    def __init__(self, context, request, interfaces, term, limit=5):
        self.context = context
        self.request = request
        self.interfaces = interfaces
        self.term = term
        self.limit = limit

    def __call__(self):
        criteria = self._makeCriteria()
        criteria['limit'] = self.limit
        searcher = ICatalogSearch(self.context)
        num, docids, resolver = searcher(**criteria)
        return num, docids, resolver

    def get_batch(self):
        return get_catalog_batch_grid(
            self.context, self.request, **self._makeCriteria())

    def _makeCriteria(self):
        principals = effective_principals(self.request)
        # this is always assumed to be a global search; it does no
        # path filtering
        criteria = {}
        criteria['sort_index'] = 'texts'
        criteria['texts'] = self.term
        criteria['interfaces'] = {'query':self.interfaces, 'operator':'or'}
        criteria['allowed'] = {'query':principals, 'operator':'or'}
        return criteria
    

