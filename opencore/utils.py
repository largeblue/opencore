import calendar
import copy

from zope.component import queryAdapter
from zope.component import queryMultiAdapter
from zope.component import queryUtility

from repoze.bfg.interfaces import ISettings
from repoze.bfg.traversal import find_root
from repoze.bfg.traversal import find_interface
from repoze.lemonade.content import get_content_type

from opencore.models.interfaces import ICatalogSearch
from opencore.models.interfaces import ICommunity
from opencore.models.interfaces import ISite
from opencore.models.interfaces import IAttachmentPolicy
from opencore.views.interfaces import IFolderAddables
from opencore.views.interfaces import ILayoutProvider

def find_site(context):
    site = find_interface(context, ISite)
    if site is None:
        # for unittesting convenience
        site = find_root(context)
    return site

def find_users(context):
    return getattr(find_site(context), 'users', None)

def find_catalog(context):
    return getattr(find_site(context), 'catalog', None)

def find_events(context):
    return getattr(find_site(context), 'events', None)

def find_tags(context):
    return getattr(find_site(context), 'tags', None)

def find_profiles(context):
    return find_site(context).get('profiles')

def find_community(context):
    return find_interface(context, ICommunity)

def find_communities(context):
    site = find_site(context)
    return site.get(site.communities_name)


def get_setting(context, setting_name, default=None):
    # Grab a setting from ISettings.  (context is ignored.)
    settings = queryUtility(ISettings)
    return getattr(settings, setting_name, default)

def get_content_type_name(resource):
    content_iface = get_content_type(resource)
    return content_iface.getTaggedValue('name')

# def debugsearch(context, **kw):
#     searcher = ICatalogSearch(context)
#     kw['use_cache'] = False
#     num, docids, resolver = searcher(**kw)
#     L = []
#     for docid in docids:
#         L.append(resolver(docid))
#     return num, L

def get_session(context, request):
    site = find_site(context)
    session = site.sessions.get(request.environ['repoze.browserid'])
    return session

_MAX_32BIT_INT = int((1<<31) - 1)

def docid_to_hex(docid):
    return '%08X' % (_MAX_32BIT_INT + docid)

def hex_to_docid(hex):
    return int('%s' % hex, 16) - _MAX_32BIT_INT

def asbool(s):
    s = str(s).strip()
    return s.lower() in ('t', 'true', 'y', 'yes', 'on', '1')

def coarse_datetime_repr(date):
    """Convert a datetime to an integer with 100 second granularity.

    The granularity reduces the number of index entries in the
    catalog.
    """
    timetime = calendar.timegm(date.timetuple())
    return int(timetime) // 100

def support_attachments(context):
    """Return true if the given object should support attachments"""
    adapter = queryAdapter(context, IAttachmentPolicy)
    if adapter:
        return adapter.support()
    else:
        # support attachments by default
        return True

class PersistentBBB(object):
    """ A descriptor which fixes up old persistent instances with a
    default value as a 'write on read' operation.  This is usually not
    useful if the default value isn't mutable, and arguably 'write on
    read' behavior is evil.  Note that this descriptor returns the
    value after *replacing itself* on the instance with the value."""
    def __init__(self, name, val):
        self.name = name
        self.val = val

    def __get__(self, inst, cls):
        setattr(inst, self.name, copy.deepcopy(self.val))
        return getattr(inst, self.name)

def get_layout_provider(context, request):
    from opencore.views.adapters import DefaultLayoutProvider
    return queryMultiAdapter((context, request), ILayoutProvider,
                             default=DefaultLayoutProvider(context,request))

def get_folder_addables(context, request):
    from opencore.views.adapters import DefaultFolderAddables
    return queryMultiAdapter((context, request), IFolderAddables,
                             default=DefaultFolderAddables(context,request))

def find_tempfolder(context):
    root = find_root(context)
    if not 'TEMP' in root:
        root['TEMP'] = TempFolder()
    return root['TEMP']

def get_user_bookmarks(context, userid, filter_community=True):
    search = ICatalogSearch(context)
    num, docids, resolver = search(bookmarks=[userid])
    listings = [ l for l in [resolver(docid) for docid in docids] \
                        if userid in l.get('bookmarks', []) ] # thanks catalog!

    if filter_community:
        community = find_community(context)
        listings = [l for l in listings if community == find_community(l) ]

    return listings

def debugsearch(context, **kw):
    searcher = ICatalogSearch(context)
    kw['use_cache'] = False
    num, docids, resolver = searcher(**kw)
    L = []
    for docid in docids:
        L.append(resolver(docid))
    return num, L

