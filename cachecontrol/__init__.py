# -*- coding: utf-8 -*-
from datetime import datetime

from django.db.models import signals
from django.core.cache import cache
from django.utils.functional import curry

def glue_cache(name, args):
    x = str(':'.join([name] + map(lambda x: str(x), args)))
    #print "  ", args, [x]
    return x

def cache_tags(name, args):
    tags = [glue_cache('cc_time_tag', [name] + args)]
    for i, arg in enumerate(args):
        tag = glue_cache('cc_time_tag', [name, 'arg', i, arg])
        tags.append(tag)
    return tags

def view_set_cache(name, expire_time=None, args=[], cache_func=lambda: None):
    value = get_cache(name, args)
    if value is None:
        value = cache_func()
        set_cache(name, value, expire_time, args)
    return value

def clear_cache(name, args):
#    print "Clearing cache %s" % name
    if len(args) > 1:
        tags = cache_tags(name, args)
        for tag in tags:
#            print "   Deleted key %s" % tag
            #cache.set(tag, datetime.now())
            cache.delete(tag)
    name = glue_cache(name, args)
    cache.delete(name)

def set_cache(name, value, expire_time, args):
  #  print "Setting cache %s" % name
    if len(args) > 1:
        time = datetime.now()
        tags = cache_tags(name, args)
        for tag in tags:
            cache.set(tag, time, expire_time)
    cache_key = glue_cache(name, args)
 #   print "   Cache key is %s" % cache_key
    cache.set(cache_key, value, expire_time)

def get_cache(name, args):
#    print "Getting cache %s" % name
    cache_key = glue_cache(name, args)
#    print "   Cache key is %s" % cache_key
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
                
#    print u"   Cache result is: %s" % unicode(result)[:20]
    return result

class AlreadyRegistered(Exception):
    pass
class DeprecatedName(Exception):
    pass

def _clear_cached(name, args_func, *args, **kwargs):
    obj = kwargs['instance']
    args_ = args_func(obj)
    
    clear_cache(name, args_)

class CacheRegistry(object):

    def __init__(self):
        self._registry = {}

    def register(self, name, model_pairs):
        name = str(name)
        if name in self._registry:
            raise AlreadyRegistered(u'name %s already registered.' % name)
        if ':' in name or '|' in name:
            raise DeprecatedName(u'name of cache can not consist "|" or ":"')
        
        self._registry[name] = model_pairs
        
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
