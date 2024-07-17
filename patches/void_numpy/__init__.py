"""
if you don't need numpy, but numpy is indirectly imported by other packages,
you can replace the real numpy package with this.

this package helps:
- third party libraries that imports numpy but never uses in the whole lifespan
    of runtime.
- matplotlib.cbook.__init__:
    from numpy.exceptions import VisibleDeprecationWarning
"""
