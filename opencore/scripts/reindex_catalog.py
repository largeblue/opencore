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

""" Reindex the catalog  """

from opencore.scripting import get_default_config
from opencore.scripting import open_root
from opencore.models.catalog import reindex_catalog
from optparse import OptionParser
import re

def main():
    parser = OptionParser(description=__doc__)
    parser.add_option('-C', '--config', dest='config', default=None,
        help="Specify a paster config file. Defaults to $CWD/etc/karl.ini")
    parser.add_option('-d', '--dry-run', dest='dry_run',
        action="store_true", default=False,
        help="Don't commit the transactions")
    parser.add_option('-i', '--interval', dest='commit_interval',
        action="store", default=200,
        help="Commit every N transactions")
    parser.add_option('-p', '--path', dest='path',
        action="store", default=None, metavar='EXPR',
        help="Reindex only objects whose path matches a regular expression")
    parser.add_option('-n', '--index', dest='indexes',
        action="append", help="Reindex only the given index (can be repeated)")

    options, args = parser.parse_args()
    if args:
        parser.error("Too many parameters: %s" % repr(args))

    commit_interval = int(options.commit_interval)
    if options.path:
        path_re = re.compile(options.path)
    else:
        path_re = None

    config = options.config
    if config is None:
        config = get_default_config()
    root, closer = open_root(config)

    def output(msg):
        print msg

    kw = {}
    if options.indexes:
        kw['indexes'] = options.indexes

    reindex_catalog(root, path_re=path_re, commit_interval=commit_interval,
                    dry_run=options.dry_run, output=output, **kw)

if __name__ == '__main__':
    main()
