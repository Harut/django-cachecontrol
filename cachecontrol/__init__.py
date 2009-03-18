# -*- coding: utf-8 -*-
from datetime import datetime

from django.db.models import signals
from django.core.cache import cache
from django.utils.functional import curry

def glue_cache(name, args):
    '''
    Returns cache name by value and args.
    '''
    x = u':'.join([name] + map(lambda x: str(x), args))
    #print "  ", args, [x]
    return x

def cache_tags(name, args):
    '''
    Returns all tags to cache key by value and args.
    The first tag is key's timestamp
    '''
    tags = [glue_cache('cc_time_tag', [name] + args)]
    for i, arg in enumerate(args):
        tag = glue_cache('cc_time_tag', [name, 'arg', i, arg])
        tags.append(tag)
    return tags

def view_set_cache(name, expire_time=None, args=[], cache_func=lambda: None):
    '''
    Returns cache value if exists
    Otherwise calls cache_funcs, sets cache value to it and returns it.
    '''
    value = get_cache(name, args)
    if value is None:
        value = cache_func()
        set_cache(name, value, expire_time, args)
    return value

def clear_cache(name, args):
    '''
    Clears cache and all of it's tags (if number of args > 1)
    '''
    if len(args) > 1:
        tags = cache_tags(name, args)
        for tag in tags:
            cache.delete(tag)
    name = glue_cache(name, args)
    cache.delete(name)

def set_cache(name, value, expire_time, args):
    '''
    Sets cache value according cache name and "vary_on" args.
    Sets tag timestamps if they are not set (if number of args > 1)
    Sets cache key timestamp (if number of args > 1)
    '''
#    print "Setting cache %s" % name
    if len(args) > 1:
        time = datetime.now()
        tags = cache_tags(name, args)
        cache.set(tags[0], time, expire_time)
        for tag in tags[1:]:
            # KADAVR!
            if not cache.get(tag):
                cache.set(tag, time, expire_time)
    cache_key = glue_cache(name, args)
    cache.set(cache_key, value, expire_time)

def get_cache(name, args):
    '''
    Gets cache value according cache name and "vary_on" args
    If one of cache tags is timed out or lost, returns None
    '''
#    print "Getting cache %s" % name
    cache_key = glue_cache(name, args)
    result = cache.get(cache_key)
    
    if len(args) > 1 and result is not None:
#        print "   There are few arguments on cache %s" % name
        tags = cache_tags(name, args)
        time = cache.get(tags[0])
        if time:
            for tag in tags[1:]:
                c = cache.get(tag)

                if not c or c > time:
                    result = None
                    break
#                else:
#                    print "   Tag %s is OK: %s %s" % (tag, c, type(c))
        else:
            result = None
    return result

class AlreadyRegistered(Exception):
    pass
class DeprecatedName(Exception):
    pass

def _clear_cached(name, args_func, *args, **kwargs):
    '''
    Model's save and delete callback
    '''
    obj = kwargs['instance']
    if registry._registry[name] == 0:
        cache.delete(name)
    elif registry._registry[name] == 1:
        number, value = args_func(obj)
        cache.delete(glue_cache(name, [value]))
    else:
        number, value = args_func(obj)
        tag = glue_cache('cc_time_tag', [name, 'arg', number, value])
        cache.delete(tag)

class CacheRegistry(object):
    '''
    Stores all registered caches
    '''
    def __init__(self):
        self._registry = {}

    def register(self, name, num_args, model_pairs):
        #name = str(name)
        if name in self._registry:
            raise AlreadyRegistered(u'name %s already registered.' % name)
        if ':' in name or '|' in name:
            raise DeprecatedName(u'name of cache can not consist "|" or ":"')
        
        self._registry[name] = num_args
        
        for Model, args_func in model_pairs:
            signals.post_save.connect(curry(_clear_cached, name, args_func), sender=Model, weak=False)
            signals.pre_delete.connect(curry(_clear_cached, name, args_func), sender=Model, weak=False)
        print "registered cache %s" %name
        
    def register_list(self, list):
        map(lambda x: self.register(*x), list)
        
registry = CacheRegistry()

def autodiscover():
    """
    Auto-discover INSTALLED_APPS cachecontrol.py modules and fail silently when 
    not present.
    """
    import imp
    from django.conf import settings
    for app in settings.INSTALLED_APPS:
        try:
            imp.find_module("caches", __import__(app, {}, {}, [app.split(".")[-1]]).__path__)
        except ImportError:
            # there is no app admin.py, skip it
            continue
        __import__("%s.caches" % app)
