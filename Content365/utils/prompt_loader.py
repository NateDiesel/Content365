from importlib import import_module as _im
_m = _im('utils.prompt_loader')
# re-export everything public
for _k in dir(_m):
    if not _k.startswith('_'):
        globals()[_k] = getattr(_m, _k)
