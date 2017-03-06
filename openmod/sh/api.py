from geoalchemy2 import shape
from sqlalchemy.exc import IntegrityError
from openmod.sh.schemas import oms as schema

def objects_to_dict(objects):
    """
    objects: list of schema.* objects
    returns: dictionary
    """
    o_dict = {}
    for o in objects:
        o_dict[o.key] = o.value
    return o_dict

def dict_to_tags(dic):
    return [schema.Tag(k, v) for k,v in dic.items()]

def dict_to_sequences(dic):
    return [schema.Sequence(k, v) for k,v in dic.items()]

def wkt_to_geom(wkt):
    if wkt is None or wkt == '':
        return None
    else:
        geom = schema.Geom(wkt.split('(')[0].strip(), 'SRID=4326;' + wkt)
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

def get_query_args(query_args, query_defaults):
    """
    Args:
        query_args (dict): e.g {'children': 'true'}
    """
    all_query_args = query_defaults
    # update api default query parameters by args
    for k,v in query_args.items():
        if k in query_defaults:
            if v != query_defaults[k]:
                all_query_args[k] = v
    return all_query_args

def subset_json(element_dct, query_args):
    """
    Args:
        element_dct (dict): with default element representation
    """
    # remove objects if query arguements are false
    for k in ['geom', 'tags', 'sequences', 'children', 'parents', 'successors', 'predecessors']:
        if query_args.get(k, '') == 'false':
            element_dct.pop(k)
    return element_dct

def expand_element(element, query_args):
    """expand: children, parents, successors or predecessors"""
    expand = query_args['expand']
    expand_list = []
    for e in getattr(element, expand):
        expand_list.append(subset_json(serialize_element(e), query_args))
    return expand_list

def get_elements(query_parameters):
    """
    works for name and type
    """
    query = schema.Element.query
    if 'name' in query_parameters.keys():
        query = query.filter(schema.Element.name.like(query_parameters['name']))
    if 'type' in query_parameters.keys():
        query = query.filter(schema.Element.type.like(query_parameters['type']))
    elements = query.all()
    return elements

def create_element_from_json(json):
    tags = dict_to_tags(json.get('tags', {}))

    sequences = dict_to_sequences(json.get('sequences', {}))
    geom = wkt_to_geom(json.get('geom', ''))

    element = schema.Element(name=json['name'], type=json['type'], tags=tags,
                          sequences=sequences, geom=geom)

    return element

def json_to_db(json):
    try:
        exist = schema.Element.query.filter_by(name=json['name']).one()
        return {"success": False}

    except:
        element = create_element_from_json(json)

        children_dct = {e['name']: create_element_from_json(e)
                        for e in json.get('children', [])}
        element.children = list(children_dct.values())


        for child in json.get('children', []):
            if child.get('predecessors'):
                children_dct[child['name']].predecessors = [
                                    children_dct[ps] for ps in child['predecessors']]
            if child.get('successors'):
                children_dct[child['name']].successors = [
                                    children_dct[ss] for ss in child['successors']]

        schema.DB.session.add(element)
        schema.DB.session.commit()

        return {"success": True, "scenario_db_id": element.id}

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
    element = schema.Element.query.filter_by(id=query_args['id']).first()
    element_dct = serialize_element(element)
    element_dct['api_parameters'] = {'version': '0.0.1',
                                     'type': 'element'}
    all_query_args = get_query_args(query_args, query_defaults)
    element_dct['api_parameters']['query'] = all_query_args
    # Use api parameters query for subsetting
    element_dct = subset_json(element_dct, all_query_args)
    if 'expand' in query_args.keys():
        element_dct[query_args['expand']] = expand_element(element, query_args)
    return element_dct

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
    all_query_args = get_query_args(query_args, query_defaults)
    outer_json['api_parameters']['query'] = all_query_args
    for element in elements:
        json = serialize_element(element)
        json = subset_json(json, all_query_args)
        if 'expand' in query_args.keys():
            json[query_args['expand']] = expand_element(element, query_args)
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

def update_scenario(scenario_json=None, update_json=None):
    """Update scenario takes a scenario and updates values inside this scenario
    based on the update_json file

    Parameters
    ----------
    scenario_json: dict
        Scenario with expanded children (if not given, scenario_json will try
        to get this from database)
    update_json: dict
        Dictionary containing information for update in 'update'-format
    """
    if scenario_json is None:
        scenario_json = provide_elements_api({'name': update_json['scenario'],
                                              'type':'scenario'})

    if update_json['update_type'] == 'input':
        # create elements dict for easier handling
        elements = {e['name']: e for e in scenario_json['children']}
        for u in update_json['update']:
            for name in u['element_names']:
                if elements.get(name):
                    # check for geom update
                    if u.get('geom'):
                        elements[name]['geom'] = u['geom']
                    # check for sequence update
                    if u.get('sequences'):
                        for k,v in u['sequences'].items():
                            elements[name]['sequences'][k] = v
                    # check for geom update
                    if u.get('tags'):
                        for k,v in u['tags'].items():
                            elements[name]['tags'][k] = v
                else:
                    print("The element with name {0} you are trying to update is"
                        " not in the scenario {1}".format(name,
                                                          scenario_json['name']))
        scenario_json['children'] = list(elements.values())

        return scenario_json

    else:
        raise NotImplementedError("Only 'input' update type implemented.")


def delete_element_from_db(element_identifier, by='id'):
    """
    """
    if by == 'id':
        element = schema.Element.query.filter_by(id=element_identifier).first()
    if by == 'name':
        element = schema.Element.query.filter_by(name=element_identifier).first()

    # check if element has more than one parent, if so: raise error
    for child in element.children:
        parents = [parent for parent in child.parents]
        if len(parents) > 1:
            raise ValueError(
                "Deleting element {0} with all its children failed. " \
                "Child {1} does have more than one parent.".format(element.name,
                                                                   child.name))

    schema.DB.session.delete(element)

    schema.DB.session.commit()

def provide_sequence_api(query_args):
    """
    needs at least id as query argument
    """
    sequence = schema.Sequence.query.filter_by(id=query_args['id']).first()
    json = {}
    if sequence:
        json[sequence.key] = sequence.value
    return json

def allowed_file(filename):
    ALLOWED_EXTENSIONS = set(['json'])
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def results_to_db(scenario_name, results_dict):
    """
    """
    # get scenario element by name

    scenario = schema.Element.query.filter(
                    schema.Element.name.like(scenario_name)).first()

    # check if results exist, if so: delete from database
    scenario_results_exist = schema.ResultSequences.query.filter_by(
                                                    scenario_id=scenario.id).all()
    if scenario_results_exist:
        for result in scenario_results_exist:
            schema.DB.session.delete(result)
        schema.DB.session.commit()

    for source, v in results_dict.items():
        predecessor = schema.Element.query.filter(
                                schema.Element.name.like(source.label)).first()
        if not predecessor:
            raise Warning("Missing predeccesor element in db for oemof " \
                          "object {}.".format(source.label))

        for target, seq in v.items():
            successor = schema.Element.query.filter(
                                schema.Element.name.like(target.label)).first()
            result = schema.ResultSequences(scenario=scenario,
                                            predecessor=predecessor,
                                            successor=successor,
                                            type='result',
                                            value=seq)

            schema.DB.session.add(result)
            schema.DB.session.flush()

    schema.DB.session.commit()


