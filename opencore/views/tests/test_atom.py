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

import datetime
from zope.interface import directlyProvides

import unittest
from repoze.bfg import testing

from opencore import testing as oitesting
from opencore.views.tests.test_community import DummyTagQuery

class CommunityAtomViewTests(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _register(self):
        from zope.interface import Interface
        from opencore.models.interfaces import ITagQuery
        testing.registerAdapter(DummyTagQuery, (Interface, Interface),
                                ITagQuery)

        from opencore.views.interfaces import IAtomEntry
        testing.registerAdapter(DummyAtomEntry, (Interface, Interface),
                                IAtomEntry)

    def _callFUT(self, context, request):
        from opencore.views.atom import community_atom_view
        self._register()
        return community_atom_view(context, request)

    def test_it(self):
        from zope.interface import Interface
        from opencore.models.interfaces import ICommunity
        import datetime
        context = testing.DummyModel(title='thetitle')
        directlyProvides(context, ICommunity)
        context.member_names = context.moderator_names = set()
        context.title = "Community"
        foo = testing.DummyModel()
        foo.modified = datetime.datetime(2009, 9, 2, 10, 28, 0)
        request = testing.DummyRequest()
        testing.registerDummyRenderer(
            'opencore.views:templates/atomfeed.pt')
        from opencore.models.interfaces import ICatalogSearch
        from opencore.models.adapters import CatalogSearch
        catalog = oitesting.DummyCatalog({1:'/foo'})
        testing.registerModels({'/foo':foo})
        context.catalog = catalog
        testing.registerAdapter(CatalogSearch, (Interface), ICatalogSearch)
        self._callFUT(context, request)

class DummyAtomEntry(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    title = "Entry Title"
    uri = "http://example.com/entry"
    published = datetime.datetime(1975, 07, 07, 07, 55)
    updated = datetime.datetime(2009, 04, 15, 16, 11)
    author = {"name": "Chris", "uri": "http://example.com/profiles/chris/"}
    content = "Some text."
