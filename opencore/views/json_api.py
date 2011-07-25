"""
JSON API view
"""


from repoze.bfg.view import bfg_view

class json_view(object):
    """
        Provides a JSON/JSONP API decorator that set up correct json and jsonp views.
        Initially, this chains json and jsonp views.
        Shortly, will use api-key based authorisation and accept-header-based self-documentation
    """

    def __init__(self, name='', request_type=None, for_=None, permission=None,
                 route_name=None, request_method=None, request_param=None,
                 containment=None, attr=None, renderer=None, wrapper=None,
                 xhr=False, accept=None, header=None, path_info=None,
                 custom_predicates=(), context=None):
        # set up json view
        self.json = bfg_view(name=name + '.json', request_type=request_type, for_=for_, permission=permission,
                 route_name=route_name, request_method=request_method, request_param=request_param,
                containment=containment, attr=attr, renderer='json', wrapper=wrapper,
                 xhr=xhr, accept=accept, header=header, path_info=path_info,
                 custom_predicates=custom_predicates, context=context)
        # set up jsonp view
        self.jsonp = bfg_view(name=name + '.jsonp', request_type=request_type, for_=for_, permission=permission,
                 route_name=route_name, request_method=request_method, request_param=request_param,
                 containment=containment, attr=attr, renderer='jsonp', wrapper=wrapper,
                 xhr=xhr, accept=accept, header=header, path_info=path_info,
                 custom_predicates=custom_predicates, context=context)

    def __call__(self, wrapped):
        return self.jsonp(self.json(wrapped))