"""
Move a piece of content to another folder.  Constraints:

- ** DO NOT SEND ALERT EMAILS DURING THIS PROCESS !! **

- All blog entries/comments, not a subset

- Retain the docid, owner, and create/modified dates

- If the owner can't be found, assign to the System User

- Put a <p><em>This ${content type} was originally authored in the
"Information Program Staff Community" community.</em></p> in the top
of the body text.
"""

from opencore.utils import find_catalog
from opencore.utils import find_community
from opencore.utils import find_users
from opencore.views.utils import make_unique_name
from optparse import OptionParser
from openhcd.scripting import get_default_config
from openhcd.scripting import open_root
from repoze.bfg.traversal import model_path
from repoze.bfg.traversal import find_model
from repoze.folder.interfaces import IFolder
from repoze.lemonade.content import get_content_type
from repoze.workflow import get_workflow

import logging
import sys
import transaction

log = logging.getLogger(__name__)
logging.basicConfig()


def postorder(startnode):

    def visit(node):
        if IFolder.providedBy(node):
            for child in node.values():
                for result in visit(child):
                    yield result
        yield node
        if hasattr(node, '_p_deactivate'):
            # attempt to not run out of memory
            node._p_deactivate()
    return visit(startnode)

def move_content(root, src, dst, wf_state):
    try:
        context = find_model(root, src)
    except KeyError:
        print >>sys.stderr, "Source content not found: %s" % src
        sys.exit(-1)

    try:
        dest_folder = find_model(root, dst)
    except KeyError:
        print >>sys.stderr, "Destination folder not found: %s" % dst
        sys.exit(-1)

    src_community = find_community(context)

    catalog = find_catalog(root)
    assert catalog is not None
    users = find_users(root)
    assert users is not None

    if src_community is not None:
        move_header = ('<p><em>This was originally authored '
                       'in the "%s" community.</em></p>' %
                       src_community.title)
    else:
        move_header = ''

    src_folder = context.__parent__
    name = context.__name__

    log.info("Moving %s", model_path(context))
    for obj in postorder(context):
        if hasattr(obj, 'docid'):
            docid = obj.docid
            catalog.document_map.remove_docid(docid)
            catalog.unindex_doc(docid)
    del src_folder[name]

    if (context.creator != 'admin'
            and users.get_by_id(context.creator) is None):
        # give the entry to the system admin
        log.warning(
            "User %s not found; reassigning to admin", context.creator)
        context.creator = 'admin'

    if name in dest_folder:
        name = make_unique_name(dest_folder, context.title)

    dest_folder[name] = context
    for obj in postorder(context):
        if hasattr(obj, 'docid'):
            docid = obj.docid
            catalog.document_map.add(model_path(obj), docid)
            catalog.index_doc(docid, obj)

    if wf_state is not None:
        wf = get_workflow(get_content_type(context), 'security', context)
        wf.transition_to_state(context, None, wf_state)

    if hasattr(context, 'text'):
        context.text = "%s\n%s" % (move_header, context.text)

def main(argv=sys.argv):
    logging.basicConfig()
    log.setLevel(logging.INFO)

    parser = OptionParser(
        description="Move content to another folder",
        usage="%prog [options] content_path dest_folder",
        )
    parser.add_option('-C', '--config', dest='config', default=None,
        help="Specify a paster config file. Defaults to $CWD/etc/karl.ini")
    parser.add_option('-d', '--dry-run', dest='dry_run',
        action="store_true", default=False,
        help="Don't commit the transaction")
    parser.add_option('-S', '--security-state', dest='security_state',
                      default=None,
                      help="Force workflow transition to given state.  By "
                      "default no transition is performed.")
    options, args = parser.parse_args()

    if len(args) != 2:
        parser.error("Source content and destination folder are required")

    config = options.config
    if not config:
        config = get_default_config()
    root, closer = open_root(config)

    try:
        move_content(root, args[0], args[1], options.security_state)

    except:
        transaction.abort()
        raise

    else:
        if options.dry_run:
            log.info("Aborting transaction.")
            transaction.abort()
        else:
            log.info("Committing transaction.")
            transaction.commit()


if __name__ == '__main__':
    main()