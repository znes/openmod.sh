from geoalchemy2 import shape

from openmod.sh.schemas import oms as osm

def objects_to_dict(objects):
    """
    objects: list of osm.* objects
    returns: dictionary
    """
    o_dict = {}
    for o in objects:
        o_dict[o.key] = o.value
    return o_dict

def dict_to_tags(dic):
    if dic is None:
        return []
    else:
        return [osm.Tag(k, v) for k,v in dic.items()]

def dict_to_sequences(dic):
    if dic is None:
        return []
    else:
        return [osm.Sequence(k, v) for k,v in dic.items()]

def wkt_to_geom(wkt):
    if wkt is None :
        return None
    else:
        geom = osm.Geom(wkt.split('(')[0].strip(), 'SRID=4326;' + wkt)
        return geom

def serialize_element(element):
    serialized = {'name': element.name,
                  'type': element.type}
    if element.geom:
        serialized['geom'] = shape.to_shape(element.geom.geom).wkt
    else:
        serialized['geom'] = None
    serialized['tags'] = objects_to_dict(element.tags)
    serialized['sequences'] = objects_to_dict(element.sequences)
    serialized['children'] = [e.name for e in element.children]
    serialized['parents'] = [e.name for e in element.parents]
    serialized['predecessors'] = [e.name for e in element.predecessors]
    serialized['successors'] = [e.name for e in element.successors]
    return serialized

def subset_json(json, query_defaults, query_args={}):
    """
    Args:
        json (dict): with default element representation
        query_args (dict): e.g {'children': 'true'}
    """

    # update api default query parameters by args
    for k,v in query_args.items():
        if k in query_defaults:
            if v != query_defaults[k]:
                json['api_parameters']['query'][k] = v
    # remove objects if api parameters are false (for args and defaults)
    for k in query_defaults:
        if json['api_parameters']['query'][k] == 'false':
            json.pop(k)
    return json

def expand_element(element, expand):
    """expand: children, parents, successors or predecessors"""
    expand_list = []
    for e in getattr(element, expand):
        expand_list.append(serialize_element(e))
    return expand_list

def get_elements(query_parameters):
    """
    works for name and type
    """
    query = osm.Element.query
    if 'name' in query_parameters.keys():
        query = query.filter(osm.Element.name.like(query_parameters['name']))
    if 'type' in query_parameters.keys():
        query = query.filter(osm.Element.type.like(query_parameters['type']))
    elements = query.all()
    return elements

def create_element_from_json(json):
    tags = dict_to_tags(json['tags'])

    sequences = dict_to_sequences(json.get('sequences'))
    geom = wkt_to_geom(json.get('geom'))

    element = osm.Element(name=json['name'], type=json['type'],tags=tags,
                          sequences=sequences, geom=geom)

    return element

def json_to_db(json):
    element = create_element_from_json(json)

    children_dct = {e['name']: create_element_from_json(e)
                    for e in json['children']}
    element.children = list(children_dct.values())

    for e in children_dct:
        for c in json['children']:
            if c.get('predecessors'):
                children_dct[c['name']].predecessors = [children_dct[p]
                                                        for p in c['predecessors']]
            if c.get('successors'):
                children_dct[c['name']].successors = [children_dct[s]
                                                      for s in c['successors']]


    osm.DB.session.add(element)
    osm.DB.session.commit()

# API for element and elements
def provide_element_api(query_args):
    """
    This is Element API version 0.0.1 for GET

    mandatory query parameters:
      id

    default values for optional query parameters if not provided:
      geom: true,
      tags: true,
      sequences: true,
      children: true,
      parents: true,
      predecessors: true,
      successors: true

    additional optional query parameters:
      expand

    """
    query_defaults = {'geom': 'true',
                      'tags': 'true',
                      'sequences': 'true',
                      'children': 'true',
                      'parents': 'true',
                      'predecessors': 'true',
                      'successors': 'true'}
    element = osm.Element.query.filter_by(id=query_args['id']).first()
    json = serialize_element(element)
    json['api_parameters'] = {'version': '0.0.1',
                              'type': 'element'}
    json['api_parameters']['query'] = query_defaults
    json = subset_json(json, query_defaults, query_args)
    if 'expand' in query_args.keys():
        json[query_args['expand']] = expand_element(element, query_args['expand'])
    return json

def provide_elements_api(query_args):
    """
    This is Elements API version 0.0.1 for GET

    main query parameters, if non of them is provided all elements will be taken into account:
      name
      type

    default values for optional query parameters if not provided:
      geom: true,
      tags: true,
      sequences: true,
      children: true,
      parents: true,
      predecessors: true,
      successors: true

    additional optional query parameters:
      expand

    """
    query_defaults = {'geom': 'true',
                      'tags': 'true',
                      'sequences': 'true',
                      'children': 'true',
                      'parents': 'true',
                      'predecessors': 'true',
                      'successors': 'true'}
    elements = get_elements(query_args)
    outer_json = {}
    outer_json['api_parameters'] = {'version': '0.0.1',
                                     'type': 'elements'}
    outer_json['api_parameters']['query'] = query_defaults
    for k,v in query_args.items():
        if k in query_defaults:
            if v != query_defaults[k]:
                outer_json['api_parameters']['query'][k] = v
    for element in elements:
        json = serialize_element(element)
        json['api_parameters'] = {'version': '0.0.1',
                                  'type': 'element'}
        json['api_parameters']['query'] = query_defaults
        json = subset_json(json, query_defaults, query_args)
        if 'expand' in query_args.keys():
            json[query_args['expand']] = expand_element(element,
                                                        query_args['expand'])
        json.pop('api_parameters')
        outer_json[str(element.id)] = json
    return outer_json

def explicate_hubs(json):
    """Takes elements names of hubs and add explicit hub elements to the
    dataset

    """
    existing_hubs = [h for h in json['children'] if h['type'] == 'hub']
    if existing_hubs:
        raise ValueError("Found explicit hub definition in JSON file!")

    dct = {}
    for child in json['children']:
        for s in child.get('successors', []):
            obj = {'type': 'hub',
                   'name': s,
                   'tags': {'sector': s.split('_')[-1]}
                   }
            dct[s] = dct.get(s, obj)
            dct[s]['predecessors'] = dct[s].get('predecessors', [])
            dct[s]['predecessors'].append(child['name'])
        for p in child.get('predecessors', []):
            obj = {'type': 'hub',
                   'name': p,
                   'tags': {'sector': p.split('_')[-1]}
                   }
            dct[p] = dct.get(p, obj)
            dct[p]['successors'] = dct[p].get('successors', [])
            dct[p]['successors'].append(child['name'])
        # add global hubs (kind of dirty...)
        if child.get('tags'):
            if (child['tags'].get('fuel_type')
                and child['tags'].get('fuel_type')
                        not in child.get('predecessors', [])
                and child['type'] in ['combined_flexible_generator',
                                      'flexible_generator']):
                obj = {'type': 'hub',
                       'name': child['tags']['fuel_type'],
                       'tags': {'balanced': 'false'}}
                dct[obj['name']] = dct.get(obj['name'], obj)
                dct[obj['name']]['successors'] = dct[obj['name']].get('successors', [])
                dct[obj['name']]['successors'].append(child['name'])

    json['children'].extend(dct.values())

    return json

def provide_sequence_api(query_args):
    """
    needs at least id as query argument
    """
    sequence = osm.Sequence.query.filter_by(id=query_args['id']).first()
    json = {}
    if sequence:
        json[sequence.key] = sequence.value
    return json

def allowed_file(filename):
    ALLOWED_EXTENSIONS = set(['json'])
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
