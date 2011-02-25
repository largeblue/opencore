import re

from repoze.bfg.chameleon_zpt import render_template_to_response
from repoze.bfg.traversal import model_path
from repoze.bfg.url import model_url

from repoze.folder.interfaces import IFolder
from repoze.lemonade.content import get_content_type
from repoze.lemonade.content import is_content

from opencore.security.policy import NO_INHERIT
from opencore.security.policy import postorder
from opencore.utils import find_catalog

COMMA_WS = re.compile(r'[\s,]+')

def edit_acl_view(context, request):

    acl = original_acl = getattr(context, '__acl__', [])
    if acl and acl[-1] == NO_INHERIT:
        acl = acl[:-1]
        epilog = [NO_INHERIT]
    else:
        epilog = []

    if 'form.move_up' in request.POST:
        index = int(request.POST['index'])
        if index > 0:
            new = acl[:]
            new[index-1], new[index] = new[index], new[index-1]
            acl = new

    elif 'form.move_down' in request.POST:
        index = int(request.POST['index'])
        if index < len(acl) - 1:
            new = acl[:]
            new[index+1], new[index] = new[index], new[index+1]
            acl = new

    elif 'form.remove' in request.POST:
        index = int(request.POST['index'])
        new = acl[:]
        del new[index]
        acl = new

    elif 'form.add' in request.POST:
        verb = request.POST['verb']
        principal = request.POST['principal']
        permissions = tuple(filter(None,
                              COMMA_WS.split(request.POST['permissions'])))
        new = acl[:]
        new.append((verb, principal, permissions))
        acl = new

    elif 'form.inherit' in request.POST:
        no_inherit = request.POST['inherit'] == 'disabled'
        if no_inherit:
            epilog = [NO_INHERIT]
        else:
            epilog = []
   
    acl = acl + epilog

    if acl != original_acl:
        context.__acl__ = acl
        catalog = find_catalog(context)
        if catalog is not None:
            allowed = catalog.get('allowed')
            if allowed is not None:
                for node in postorder(context):
                    allowed.reindex_doc(node.docid, node)
                catalog.invalidate()
    
    parent = context.__parent__
    parent_acl = []
    while parent is not None:
        p_acl = getattr(parent, '__acl__', ())
        stop = False
        for ace in p_acl:
            if ace == NO_INHERIT:
                stop = True
            else:
                parent_acl.append(ace)
        if stop:
            break
        parent = parent.__parent__

    local_acl = []
    inheriting = 'enabled'
    l_acl = getattr(context, '__acl__', ())
    for l_ace in l_acl:
        if l_ace == NO_INHERIT:
            inheriting = 'disabled'
            break
        local_acl.append(l_ace)


    return render_template_to_response('templates/edit_acl.pt',
                                       parent_acl=parent_acl or (),
                                       local_acl=local_acl,
                                       inheriting=inheriting,
                                       security_state=None,
                                       security_states=None,
                                      )

def make_acls(node, request, acls=None, offset=0):
    if acls is None:
        acls = []
    path = model_path(node)
    url = model_url(node, request)
    acl = getattr(node, '__acl__', None)
    folderish = IFolder.providedBy(node)
    name = node.__name__ or '/'
    has_children = False
    if folderish:
        has_children = bool(len(node))
    if (folderish and has_children) or acl is not None:
        acls.append({'offset':offset, 'path':path, 'acl':acl, 'name':name,
                     'url':url})
    if folderish:
        children = list(node.items())
        children.sort()
        for childname, child in children:
            make_acls(child, request, acls, offset+1)
    node._p_deactivate()
    return acls

def acl_tree_view(context, request):
    acls = make_acls(context, request)
    return render_template_to_response(
        'templates/acl_tree.pt',
        acls = acls)




