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

""" Derived from KARL with the addition of the API providing an interface for
    easy overriding in configuration / project packages as well as some changes
    to the API itself.
"""

import os
from subprocess import PIPE
from subprocess import Popen
import sys
import time
from datetime import datetime

from zope.component import getAdapter
from zope.component import getMultiAdapter
from zope.component import queryMultiAdapter
from zope.component import queryUtility
from zope.interface import Interface, Attribute
from zope.interface import providedBy

from repoze.bfg.chameleon_zpt import get_template
from repoze.bfg.url import model_url
from repoze.bfg.security import effective_principals
from repoze.bfg.traversal import quote_path_segment
from repoze.bfg.traversal import find_model
from repoze.bfg.traversal import model_path
from repoze.bfg.location import lineage
from repoze.bfg.interfaces import ISettings
from repoze.bfg.security import authenticated_userid

from repoze.lemonade.content import get_content_type
from opencore.consts import countries
from opencore.utils import find_site
from opencore.utils import get_setting
from opencore.utils import support_attachments
from opencore.utils import get_user_bookmarks
from opencore.utils import find_profiles
from opencore.views.utils import convert_to_script
from opencore.views.utils import get_user_home
from opencore.utilities.image import thumb_url, find_image

from opencore.models.interfaces import ICommunityContent
from opencore.models.interfaces import ICommunity
from opencore.models.interfaces import ICommunityInfo
from opencore.models.interfaces import ICatalogSearch
from opencore.models.interfaces import IGridEntryInfo
from opencore.models.interfaces import ITagQuery
from opencore.models.interfaces import IBlogEntry
from opencore.models.interfaces import IForumTopic
from opencore.models.interfaces import IProfile
from opencore.models.rdbms import RDBMSStore
from opencore.views.adapters import DefaultFooter
from opencore.views.interfaces import IFooter
from opencore.views.interfaces import ISidebar

from repoze.bfg.traversal import find_interface

xhtml = ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" '
         '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">')

class ITemplateAPI(Interface):
    """ A Marker interface for a template API.

        Any implementation is required to provide the constructor
        arguements so they are accessible from within the template.
    """
    context = Attribute(u'The Context object for the view')
    request = Attribute(u'The WebOb Request object for the view')
    page_title = Attribute(u'The title of the view')

class TemplateAPI(object):
    _community_info = None
    _recent_items = None
    _identity = None
    _isStaff = None
    _intranets_info = None
    _current_intranet = None
    _home_url = None
    _snippets = None
    _start_time = int(time.time())
    countries = countries
    _form_field_templates = None

    def __init__(self, context, request, page_title=None):
        self.context = context
        self.request = request
        self.userid = authenticated_userid(request)
        self.app_url = app_url = request.application_url
        self.profile_url = app_url + '/profiles/%s' % self.userid
        self.here_url = self.context_url = model_url(context, request)
        self.view_url = model_url(context, request, request.view_name)
        settings = queryUtility(ISettings)
        self.js_devel_mode = settings and getattr(settings,
                                                  'js_devel_mode', None)
        self.static_url = '%s/static/%s' % (app_url, _get_static_rev())

        # this data will be provided for the client javascript
        self.karl_client_data = {}

        # Provide a setting in the INI to fully control the entire URL
        # to the static.  This is when the proxy runs a different port
        # number, or to "pipeline" resources on a different URL path.
        full_static_path = getattr(settings, 'full_static_path', False)
        if full_static_path:
            if '%d' in full_static_path:
                # XXX XXX note self._start_time is needed... and not _start_time
                # XXX XXX since this was a trivial bug, there is chance that
                # XXX XXX this actually never runs! TODO testing???
                full_static_path = full_static_path % self._start_time
            self.static_url = full_static_path
        self.page_title = page_title
        self.system_name = get_setting(context, 'system_name', 'KARL')
        self.user_is_admin = 'group.KarlAdmin' in effective_principals(request)
        self.site = find_site(context)
        self.admin_url = model_url(self.site, request, 'admin.html')
        # XXX XXX XXX This will never work from peoples formish templates
        # XXX XXX XXX (edit_profile and derivates) because, in those form
        # XXX XXX XXX controllers, the api is instantiated from __init__,
        # XXX XXX XXX where request.form is still unset!!! (From all other
        # XXX XXX XXX formcontrollers the api is instantiated from __call__,
        # XXX XXX XXX which is why this works. A chicken-and-egg problem, really.
        if hasattr(request, 'form') and getattr(request.form, 'errors', False):
            # This is a failed form submission request, specify an error message
            self.error_message = u'Please correct the indicated errors.'

        if settings:
            self.kaltura_info = dict(
                enabled =  getattr(settings, 'kaltura_enabled', False) in ('true', 'True'),
                partner_id = getattr(settings, 'kaltura_partner_id', ''),
                sub_partner_id = getattr(settings, 'kaltura_sub_partner_id', ''),
                admin_secret = getattr(settings, 'kaltura_admin_secret', ''),
                user_secret = getattr(settings, 'kaltura_user_secret', ''),
                kcw_uiconf_id = getattr(settings, 'kaltura_kcw_uiconf_id', '1000741'),
                player_uiconf_id = getattr(settings, 'kaltura_player_uiconf_id', ''),
                player_cache_st = getattr(settings, 'kaltura_player_cache_st', ''),
                local_user = self.userid,
            )
            if not getattr(settings, 'kaltura_client_session', False) in ('true', 'True'):
                # Secrets will not be sent to client, instead session is handled on the server.
                self.kaltura_info['session_url'] = app_url + '/' + 'kaltura_create_session.json'
        else:
            self.kaltura_info = dict(
                enabled = False,
                )

        # propagate the head data to the client
        d = self.karl_client_data['kaltura'] = dict(self.kaltura_info)
        # remove secrets if needed
        if 'session_url' in d:
            # server side session management, do not send secrets to client
            del d['user_secret']
            del d['admin_secret']

        # from openideo
        self.formerrors = {}
        self.formdata = request.POST
        self.app_config = settings
        self.rdbstore = RDBMSStore()

    @property
    def site_announcement(self):
        site_announcement = getattr(self.site, 'site_announcement', None)
        if site_announcement:
            site_announcement['profile'] = self.find_profile(
                    site_announcement.get('userid', None))
            if site_announcement['profile']:
                return site_announcement
        return {}

    def topics(self, context):
	topics = get_setting(context, 'topics')
	return sorted(elem.strip() for elem in topics.split('\n') if elem)

    @property
    def snippets(self):
        if self._snippets is None:
            self._snippets = get_template('templates/snippets.pt')
            self._snippets.doctype = xhtml
        return self._snippets

    def has_staff_acl(self, context):
        return getattr(context, 'security_state', 'inherits') == 'public'

    def is_private_in_public_community(self, context):
        """Return true if the object is private, yet located in a
        public community.
        """
        if self.community_info is None:
            return False

        community = self.community_info.context
        if context is community:
            return False
        if getattr(community, 'security_state', 'inherits') == 'public':
            return getattr(context, 'security_state', 'inherits') == 'private'
        return False

    @property
    def user_is_staff(self):
        gn = 'group.KarlStaff'
        if self._identity is None:
            self._identity = self.request.environ.get('repoze.who.identity')
            if self._identity:
                self._isStaff = gn in self._identity.get('groups', [])
        return self._isStaff

    def __getitem__(self, key):
        if key == 'form_field_templates':
            # Allow this, for ZPT's sake!
            return self.form_field_templates
        raise ValueError, "ZPT attempted to fetch %s" % key

    @property
    def community_info(self):
        if self._community_info is None:
            community = find_interface(self.context, ICommunity)
            if community is not None:
                self._community_info = getMultiAdapter(
                    (community, self.request), ICommunityInfo)
        return self._community_info

    @property
    def recent_items(self):
        if self._recent_items is None:
            community = find_interface(self.context, ICommunity)
            if community is not None:
                community_path = model_path(community)
                search = getAdapter(self.context, ICatalogSearch)
                principals = effective_principals(self.request)
                self._recent_items = []
                num, docids, resolver = search(
                    limit=10,
                    path={'query': community_path},
                    allowed={'query': principals, 'operator': 'or'},
                    sort_index='modified_date',
                    reverse=True,
                    interfaces=[ICommunityContent],
                    )
                models = filter(None, map(resolver, docids))
                for model in models:
                    adapted = getMultiAdapter((model, self.request),
                                              IGridEntryInfo)
                    self._recent_items.append(adapted)

        return self._recent_items

    community_layout_fn = 'opencore.views:templates/community_layout.pt'
    @property
    def community_layout(self):
        macro_template = get_template(self.community_layout_fn)
        return macro_template

    anonymous_layout_fn = 'opencore.views:templates/anonymous_layout.pt'
    @property
    def anonymous_layout(self):
        macro_template = get_template(self.anonymous_layout_fn)
        return macro_template

    generic_layout_fn = 'opencore.views:templates/generic_layout.pt'
    @property
    def generic_layout(self):
        macro_template = get_template(self.generic_layout_fn)
        return macro_template

    formfields_fn = 'opencore.views:templates/formfields.pt'
    @property
    def formfields(self):
        macro_template = get_template(self.formfields_fn)
        return macro_template

    lightbox_layout_fn = 'opencore.views:templates/lightbox_layout.pt'
    @property
    def lightbox_layout(self):
        macro_template = get_template(self.lightbox_layout_fn)
        return macro_template

    @property
    def form_field_templates(self):
        if self._form_field_templates is None:
            # calculate and cache value
            if hasattr(self.request, 'form'):
                self._form_field_templates =  [field.widget.template for field in self.request.form.allfields]
            else:
                self._form_field_templates = []
        return self._form_field_templates

    _status_message = None
    def get_status_message(self):
        if self._status_message:
            return self._status_message
        return self.request.params.get("status_message", None)

    def set_status_message(self, value):
        self._status_message = value

    status_message = property(get_status_message, set_status_message)

    _error_message = None
    def get_error_message(self):
        if self._error_message:
            return self._error_message
        return self.request.params.get("error_message", None)

    def set_error_message(self, value):
        self._error_message = value

    error_message = property(get_error_message, set_error_message)

    @property
    def people_url(self):
        # Get a setting for what part is appended the the app_url for
        # this installation's people directory application.
        people_path = get_setting(self.context, 'people_path', 'people')
        return self.app_url + "/" + people_path

    @property
    def communities_name(self):
        from opencore.utils import find_site
        return find_site(self.context).communities_name

    @property
    def tag_users(self):
        """Data for the tagbox display"""
        tagquery = getMultiAdapter((self.context, self.request), ITagQuery)
        return tagquery.tagusers

    def actions_to_menu(self, actions):
        """A helper used by the snippets rendering the actions menu.

        This method converts the flat list of action tuples,
        passed in as input parameters, into a structured list.

        From this input::

            (
                ('Manage Members', 'manage.html'),
                ('Add Folder', 'add_folder.html'),
                ('Add File', 'add_file.html'),
                ('Add Forum', 'add_forum.html'),
            )

        it will generate a submenu structure::

            (
                ('Manage Members', 'manage.html'),
                ('Add', '#', (
                        ('Folder', 'add_folder.html'),
                        ('File', 'add_file.html'),
                        ('Forum', 'add_forum.html'),
                    )
            )

        but if there are only 2 or less groupable items, the menu
        stays flat and a submenu is not created.

        At the moment, there is no information marking the Add
        items. Therefore the following heuristics is applied:

        - if a title starts with Add, it is considered as Add item

        - the rest of the title is considered the content type.


        XXX p.s. according to this heuristics, the following will
        also be detected as an Add item::

           ('Add Existing', 'add_existing.html')

        Which won't be a problem if there is no more then 3 Add
        items altogether.
        """
        result = []
        lookahead = []
        def process_lookahead(result=result, lookahead=lookahead):
            if len(lookahead) > 2:
                # Convert to submenu
                # take part after "Add " as title.
                result.append(('Add', '#',
                    [(item[0][4:], item[1]) for item in lookahead]))
            else:
                # add to menu as flat
                result.extend(lookahead)
            # We processed it
            del lookahead[:]

        for action in actions:
            # Is this a menu action?
            is_menu_action = action[0].startswith('Add ')
            # pad them out to make sure template does not fail
            action = action + ((), )
            if is_menu_action:
                lookahead.append(action)
            else:
                # process lookahead
                process_lookahead()
                result.append(action)
        process_lookahead()
        return result

    def render_sidebar(self):
        """Render the sidebar appropriate for the context."""
        for ancestor in lineage(self.context):
            r = queryMultiAdapter((ancestor, self.request), ISidebar)
            if r is not None:
                return r(self)
        # no sidebar exists for this context.
        return ''

    def render_footer(self):
        """Render the footer appropriate for the context."""
        for ancestor in lineage(self.context):
            r = queryMultiAdapter((ancestor, self.request), IFooter,)
            if r is not None:
                return r(self)

        # no footer exists for this context, use the default.
        return DefaultFooter(self.context, self.request)(self)

    @property
    def home_url(self):
        if self._home_url is None:
            target, extra_path = get_user_home(self.context, self.request)
            self._home_url = model_url(target, self.request, *extra_path)
        return self._home_url

    @property
    def settings(self):
        return SettingsReader(self.context)

    @property
    def support_attachments(self):
        return support_attachments(self.context)

    @property
    def logo_url(self):
        logo_path = get_setting(self.context, 'logo_path', 'images/logo.gif')
        return '%s/%s' % (self.static_url, logo_path)

    def render_karl_client_data(self, update_dict=None):
        """
        How to provide data to the client? There are 3 ways:

        1. specify the data via the template api

           api.karl_client_data['my_widget'] = {...my_data...}

           The code will be injected to all pages automatically.
           Be careful not to overwrite api.karl_client_data, only update
           one or more fields of the dictionary.


        2. Pass the data directly to the template

           render_template_to_response(...
                ...
                karl_client_data = {'my_widget': {...my_data...}},
                ...)

            The passed dictionary will update the one specified via the template api.


        3. Legacy way: head_data


           from karl.views.utils import convert_to_script

           render_template_to_response(...
                ...
                head_data = convert_to_script({'my_widget': {...my_data...}),
                ...)

           Data inserted this way is supported in order to not break old code, but for
           new code please prefer to use the methods described in point 1. or 2.

        """
        d = dict(self.karl_client_data)
        if update_dict:
            d.update(update_dict)
        return convert_to_script(d, var_name='karl_client_data')

    def supported_comment_interfaces(self):
        return (IBlogEntry, ICommunity, IForumTopic, IProfile)

    def view_count(self, context):
        return self.rdbstore.view_count(path=model_path(context,''))[0][0]

    def like_count(self, context):
        count = 0
        if 'likes' in context.__dict__:
            count = context.likes.count()
        return count

    # openideo additions below
    def get_user_bookmarks(self, filter_challenge=True):
        if self.userid is None:
            return []
        return get_user_bookmarks(self.context, self.userid, filter_challenge)

    def render_form_widget(self, widget_id, id, label, choices=[], compulsory=False, default=None, description=None, disabled=False, alt=False):
        if default is None:
            default = self.formdata.get(id, '')
        error = self.formerrors.get(id, '')
        if isinstance(error, (list, tuple)):
            error = '\n'.join(error)
        from repoze.bfg.chameleon_zpt import get_template
        #template = template_cache.get('form_widgets', createfunc=get_form_widgets)
        template = get_template('templates/form_widgets.pt')
        if isinstance(default, (list, tuple)):
            default_list = default
        else:
            default_list = [default]
        return template.render_macro(widget_id, global_scope=True,
                                     parameters=dict(name=id,
                                                     label=label,
                                                     description=description,
                                                     choices=choices,
                                                     compulsory=compulsory,
                                                     default_value=default,
                                                     default_list=default_list,
                                                     error=error,
                                                     disabled=disabled,
                                                     alt=alt,
                                                     api=self,))

    def model_path(self, obj):
        return model_path(obj)

    def find_model(self, path):
        return find_model(self.context, path)

    def get_url(self, ob):
        """ Returns the model url for `ob`
        """
        return model_url(ob, self.request).replace('https://', 'http://')

    def find_profile(self, uid):
        profiles = find_profiles(self.context)
        return profiles.get(uid, None)


    def find_image_url(self, ob, search='photo', default='/img/default_user.png', size=None):
        if ob is None:
            return default
        photo = find_image(ob, search)
        if photo is not None:
	    if isinstance(photo, (unicode, str)):
		# external reference thumbnail_url
            	return photo
            if size:
                return thumb_url(photo, self.request, size)
            else:
                return model_url(photo, self.request, 'dl')
        else:
            if default.startswith('/'): # absolute local url
                default = self.static_url + default
            return default

    def get_interfaces(self, ob):
        return [i.__name__ for i in providedBy(ob)]

    def time_ago(self, time):
        """ time difference
        """
        now = datetime.now()
        delta = (now - time)

        if( delta.days == 1 ) :
            return '%d day' % delta.days
        elif( delta.days > 0 ) :
            return '%d days' % delta.days
        elif ( (delta.seconds/3600) > 1 ) :
            return '%d hours' % (delta.seconds/3600)
        elif ( (delta.seconds/60) > 1 ) :
            return '%d mins' % (delta.seconds/60)
        else :
            return 'Moments'

    def format_date(self, d, with_break=False, time_less=False):
        if with_break and not time_less:
            return d.strftime('%B %d, %Y<br /> %I:%M%p')
        elif not time_less:
            return d.strftime('%B %d, %Y, %I:%M%p')
        else:
            return d.strftime('%B %d, %Y')

    def thumb_url(self, image, size=(200, 200)):
        return thumb_url(image, self.request, size)

class SettingsReader:
    """Convenience for reading settings in templates"""
    def __init__(self, context):
        self._context = context

    def __getattr__(self, name):
        return get_setting(self._context, name)

_static_rev = None

def _get_static_rev():
    global _static_rev
    if _static_rev is None:
        # If Karl is installed via an egg, we can try to get the Karl version
        # number from the egg and use that.
        _static_rev = _get_egg_rev()

    if _static_rev is None:
        # Development builds will use a checked out SVN copy.  See if we can
        # get the SVN revision number.
        _static_rev = _get_svn_rev()

    if _static_rev is None:
        # Fallback to just using a timestamp.  This is guaranteed not to fail
        # but will create different revisions for each process, resulting in
        # some extra static resource downloads
        _static_rev = 'r%d' % int(time.time())

    return _static_rev

def _get_svn_rev():
    module = sys.modules[__name__]
    path = os.path.dirname(os.path.abspath(module.__file__))
    try:
        proc = Popen(['svn', 'info', path], stdout=PIPE, stderr=PIPE,
                     close_fds=True)
        output = proc.stdout.readlines()
        proc.stdout.close()
        proc.stderr.close() # Ignore
        for line in output:
            if line.startswith('Revision:'):
                rev = int(line.split(':')[1])
                return 'r%d' % rev
    except OSError:
        pass

def _get_egg_rev():
    # Find folder that this module is contained in
    module = sys.modules[__name__]
    path = os.path.dirname(os.path.abspath(module.__file__))

    # Walk up the tree until we find the parent folder of an EGG-INFO folder.
    while path != '/':
        egg_info = os.path.join(path, 'EGG-INFO')
        if os.path.exists(egg_info):
            rev = os.path.split(path)[1]
            return 'r%d' % hash(rev)
        path = os.path.dirname(path)

def get_template_api(context, request):
    name = get_setting(request, 'package')
    factory = queryUtility(ITemplateAPI, name=name, default=TemplateAPI)
    return factory(context, request)


def handle_request_api(event):
    """ Subscriber for assigning the correct TemplateAPI implementation
    """
    request = event.request
    context = request.context

    if not hasattr(context, '__parent__'):
        # The object is not in the model graph
        return

    request.api = get_template_api(context, request)

