from types import SimpleNamespace as SN

from sqlalchemy.sql.expression import select

import .oms

Node = aliased(oms.Element,
               select([oms.Element]).where(~oms.Element.children.any()).alias())

class Node(Element):
    __mapper_args__ = {'polymorphic_identity': 'node'}
    id = DB.Column(DB.Integer, primary_key=True)
    element_id = DB.Column(DB.Integer, DB.ForeignKey(Element.element_id))

    lat = DB.Column(DB.Float, nullable=False)
    lon = DB.Column(DB.Float, nullable=False)

    ways = association_proxy('nodes_way', 'way')

    def __init__(self, lat, lon, changeset_id, **kwargs):
        super().__init__(changeset_id=changeset_id, **kwargs)
        self.lat = lat
        self.lon = lon

class Way(Element):
    __mapper_args__ = {'polymorphic_identity': 'way'}
    id = DB.Column(DB.Integer, primary_key=True)
    element_id = DB.Column(DB.Integer, DB.ForeignKey(Element.element_id))
    way_nodes = DB.relationship(Node_Way_Associations,
                                order_by=Node_Way_Associations.position,
                                collection_class=ordering_list('position'))
    nodes = association_proxy('way_nodes', 'node',
                              creator=lambda n: Node_Way_Associations(node=n))

class Relation(Element):
    __mapper_args__ = {'polymorphic_identity': 'relation'}
    id = DB.Column(DB.Integer, primary_key=True)
    element_id = DB.Column(DB.Integer, DB.ForeignKey(Element.element_id))
    elements = association_proxy('element_associations', 'element',
            creator=lambda e: Element_Relation_Associations(element=e))

    def reachable_nodes(self, visited=None):
        """ Recursively enumerates all nodes reachable from this relation.

        Note: does not have set semantics. Nodes may be yielded more than once.
        """

        key = lambda e: e.typename
        typename = sorted(self.elements, key=key)
        groups = {key: list(iterator)
                  for (key, iterator) in groupby(typename, key=key)}
        visited = visited if visited is not None else set()
        visited.add(self)
        return chain(groups.get('node', ()),
                     (n for w in groups.get('way', ())
                        if (w not in visited or visited.add(w))
                        for n in w.nodes),
                     (n for r in groups.get('relation', ())
                        if r not in visited
                        for n in r.reachable_nodes(visited)))

    @property
    def referenced_nodes(self):
        return (x for x in self.element_associations
                  if x.element.typename == 'node')
    @property
    def referenced_ways(self):
        return (x for x in self.element_associations
                  if x.element.typename == 'way')
    @property
    def referenced(self):
        return (x for x in self.element_associations
                  if x.element.typename == 'relation')


Changeset = SN(id=-1, tags={})

