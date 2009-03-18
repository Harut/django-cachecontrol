Cachecontrol
============

Cachecontrol allows to manage cached values and easily link them to Model signals

Usage
-----

#### root urls.py
    import cachecontrol
    cachecontrol.autodiscover()

#### appname.caches.py file
Method to attach cache to the model is to define keypairs. Each defined keypair
creates model's save and delete signal. func takes chenged model and returns
number of changed vary_on arg and value of this arg. When the signal is called,
it gets varied arg and deletes all caches with this arg.

    from cachecontrol import registry
    from models import MyModel


    caches = [
        #(cache_name, number of vary_on args, [(model, func) keypairs])
        ('cache_of_0_args', 0, [(MyModel, lambda obj: None )]),
        ('cache_of_2_args', 2, [(MyModel, lambda obj: (0, obj.pk) )]),
    ]

    registry.register_list(caches)

#### template
    {% load controlledcache %}
    {% controlledcache 600 cache_of_2_args object.pk page_number %}
    {# controlledcache expire_timeout cache_name [vary_on args|...] #}
       ..............
    {% endcontrolledcache %}

