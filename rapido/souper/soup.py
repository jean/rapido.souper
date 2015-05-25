from zope.interface import implements, alsoProvides, Interface
from zope.component import getMultiAdapter, provideUtility, provideAdapter
from souper.interfaces import ICatalogFactory
from souper.soup import get_soup, Record, NodeAttributeIndexer
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.text import CatalogTextIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex
try:
    from souper.plone.interfaces import ISoupRoot
    from souper.plone.locator import StorageLocator
except:
    from .interfaces import ISoupRoot
    from .locator import StorageLocator
    provideAdapter(StorageLocator, adapts=[Interface])

from rapido.core.interfaces import IStorage, IRapidoApplication

from .catalog import CatalogFactory
from .interfaces import IRecord


class SoupStorage(object):
    implements(IStorage)

    def __init__(self, context):
        self.context = context
        self.id = context.id
        self.root = self.context.root
        provideUtility(CatalogFactory(), ICatalogFactory, name=self.id)

    def initialize(self):
        """ setup the storage
        """
        alsoProvides(self.root, ISoupRoot)
        locator = StorageLocator(self.root)
        locator.storage(self.id)
        self._soup = get_soup(self.id, self.root)

    @property
    def soup(self):
        if not hasattr(self, '_soup'):
            self._soup = get_soup(self.id, self.root)
        return self._soup

    def create(self):
        """ return a new document
        """
        record = Record()
        rid = self.soup.add(record)
        return getMultiAdapter(
            (self.soup.get(rid), IRapidoApplication(self.context)),
            IRecord)

    def get(self, uid=None):
        """ return an existing document
        """
        record = self.soup.get(uid)
        if not record:
            return None
        return getMultiAdapter(
            (record, IRapidoApplication(self.context)),
            IRecord)

    def save(self, doc):
        """ save a document
        """
        # the soup record stores item immediately
        pass

    def delete(self, doc):
        """ delete a document
        """
        del self.soup[doc.context]

    def search(self, query, sort_index=None, limit=None, sort_type=None,
            reverse=False, names=None, with_size=False):
        """ search for documents
        """
        records = self.soup.lazy(query, sort_index=sort_index, limit=limit,
            sort_type=sort_type, reverse=reverse, names=names,
            with_size=with_size)
        db = IRapidoApplication(self.context)
        for record in records:
            yield getMultiAdapter((record(), db), IRecord)

    def documents(self):
        for key in self.soup.data.keys():
            yield self.get(key)

    def rebuild(self):
        self.soup.rebuild()

    def reindex(self, doc=None):
        if doc:
            self.soup.reindex(records=[doc.context])
        else:
            self.soup.reindex()

    def create_index(self, fieldname, indextype):
        catalog = self.soup.catalog
        field_indexer = NodeAttributeIndexer(fieldname)
        if indextype == 'field':
            catalog[fieldname] = CatalogFieldIndex(field_indexer)
        elif indextype == 'keyword':
            catalog[fieldname] = CatalogKeywordIndex(field_indexer)
        elif indextype == 'text':
            catalog[fieldname] = CatalogTextIndex(field_indexer)
