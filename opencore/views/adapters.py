from zope.component import getUtility
from zope.interface import implements

from repoze.bfg.chameleon_zpt import render_template
from repoze.bfg.chameleon_zpt import get_template
from repoze.bfg.url import model_url
from repoze.lemonade.listitem import get_listitems

from opencore.models.interfaces import IToolFactory
from opencore.utils import find_interface
from opencore.utils import find_profiles
from opencore.views.interfaces import IFooter
from opencore.views.interfaces import IToolAddables
from opencore.views.interfaces import IFolderAddables
from opencore.views.interfaces import ILayoutProvider
from opencore.views.interfaces import IBylineInfo
from opencore.utilities.interfaces import IAppDates
from opencore.models.interfaces import IForum



class DefaultToolAddables(object):
    implements(IToolAddables)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """ What tools can go in a community?
        """
        tools = get_listitems(IToolFactory)
        return [tool for tool in tools if tool['name'] not in
                self.exclude_tools]

    @property
    def exclude_tools(self):
        # Find out if we are adding this community from somewhere
        # inside the "intranets" side
        #intranets = find_interface(self.context, IIntranets)
        #site = ISite.providedBy(self.context)
        #if intranets or site:
        #    return ['wiki', 'blog']

        return ['intranets', 'forums']

class DefaultFolderAddables(object):
    implements(IFolderAddables)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """ Based on markers, override what can be added to a folder """

        # This is the default for all, meaning community, folders
        _addlist = [
            ('Add Folder', 'add_folder.html'),
            ('Add File', 'add_file.html'),
            ]

        # Intranet folders by default get Add Page
        intranets = find_interface(self.context, IIntranets)
        if intranets:
            _addlist.append(
                ('Add Event', 'add_calendarevent.html'),
                )
            _addlist.append(
                ('Add Page', 'add_page.html'),
                )

        # Override all addables in certain markers
        if IReferencesFolder.providedBy(self.context):
            _addlist = [('Add Reference Manual',
                         'add_referencemanual.html')]
        elif IReferenceManual.providedBy(self.context):
            _addlist = [
                ('Add Section', 'add_referencesection.html'),
                ('Add File', 'add_file.html'),
                ('Add Page', 'add_page.html'),
                ]
        elif IReferenceSection.providedBy(self.context):
            _addlist = [
                ('Add Section', 'add_referencesection.html'),
                ('Add File', 'add_file.html'),
                ('Add Page', 'add_page.html'),
                ]
        elif INetworkEventsMarker.providedBy(self.context):
            _addlist = [
                ('Add Event', 'add_calendarevent.html'),
                ]
        elif INetworkNewsMarker.providedBy(self.context):
            _addlist = [
                ('Add News Item', 'add_newsitem.html'),
                ]
        return _addlist

class DefaultFooter(object):
    implements(IFooter)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, api):
        return render_template(
            'templates/footer.pt',
            api=api,
            )

class DefaultLayoutProvider(object):
    """ Site policy on which o-wrap to choose from for a context"""
    implements(ILayoutProvider)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def community_layout(self):
        return get_template('opencore.views:templates/community_layout.pt')

    @property
    def generic_layout(self):
        return get_template('opencore.views:templates/generic_layout.pt')

    def __call__(self, default=None):
        # The layouts are by identifier, e.g. layout='community'

        # A series of tests, in order of precedence.
        layout = None
        if default is not None:
            layout = getattr(self, default+'_layout')
        if find_interface(self.context, IForum):
            layout = getattr(self, 'generic_layout')
        else:
            layout = self.generic_layout
        return layout    
            
    '''def __call__(self, default=None):
        # The layouts are by identifier, e.g. layout='community'

        # A series of tests, in order of precedence.
        layout = None
        if default is not None:
            layout = getattr(self, default+'_layout')
        intranet = find_interface(self.context, IIntranet)

        # Group a series of intranet-oriented decisions
        if intranet:
            # First, when under an intranet, OSI wants forums to get
            # the generic layout.
            if find_interface(self.context, IForum):
                layout = getattr(self, 'generic_layout')

            # Now for an intranet.  Everything gets the two-column
            # view except the intranet home page, which gets the 3
            # column treatment.
            else:
                layout = getattr(self, 'intranet_layout')

        elif find_interface(self.context, IIntranets):
            if find_interface(self.context, IForum):
                layout = self.generic_layout
            elif ICalendarEvent.providedBy(self.context):
                layout = self.generic_layout
            elif INetworkNewsMarker.providedBy(self.context):
                layout = self.generic_layout
            elif find_interface(self.context, IReferencesFolder):
                layout = self.generic_layout
            elif INetworkEventsMarker.providedBy(self.context):
                layout = self.generic_layout

        elif not find_interface(self.context, ICommunity):
            # If we're not in a community or an intranet we need to use the
            # generic layout.
            layout = self.generic_layout

        return layout'''

class BylineInfo(object):
    """ Adapter to grab resource info for the byline in ZPT """
    implements(IBylineInfo)
    _author_url = None
    _author_name = None
    _posted_date = None

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.profile = find_profiles(context).get(context.creator)

    @property
    def author_url(self):
        if self._author_url is None:
            self._author_url = model_url(self.profile, self.request)
        return self._author_url


    @property
    def author_name(self):
        if self._author_name is None:
            if self.profile:
                self._author_name = self.profile.title
            else:
                self._author_name = None
        return self._author_name

    @property
    def posted_date(self):
        if self._posted_date is None:
            kd = getUtility(IAppDates)
            self._posted_date = kd(self.context.created, 'longform')
        return self._posted_date