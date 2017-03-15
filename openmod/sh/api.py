from contextlib import contextmanager

from geoalchemy2 import shape
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
import networkx as nx

import oemof.db as db

from openmod.sh.schemas import oms as schema


@contextmanager
def db_session():
    """ Provide a session context to communicate with the database.
    """
    engine = db.engine(schema.configsection)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

def objects_to_dict(objects):
    """
    objects: list of schema.* objects
    returns: dictionary
    """
    o_dict = {}
    for o in objects:
        o_dict[o.key] = o.value
    return o_dict

def get_label(element):
    value = [t.value  for t in element.tags if t.key == 'label']
    if value :
        return value[0]
    else:
        return element.name

def get_tag_value(tags, tag_key):
    value = [t.value for t in tags if t.key == tag_key]
    if value:
        return value[0]
    else:
        return False

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
    for k in [ 'geom', 'tags', 'sequences', 'children', 'parents',
               'successors', 'predecessors']:
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

def get_elements(query_parameters, session):
    """
    works for name and type
    """
    query = session.query(schema.Element)
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
    with db_session() as session:
        try:
            exist = (session
                      .query(schema.Element)
                      .filter_by(name=json['name'])
                      .one())
            return {"success": False}

        except:
            element = create_element_from_json(json)

            children_dct = {e['name']: create_element_from_json(e)
                            for e in json.get('children', [])}
            element.children = list(children_dct.values())


            for child in json.get('children', []):
                if child.get('predecessors'):
                    children_dct[child['name']].predecessors = [
                                        children_dct[ps]
                                        for ps in child['predecessors']]
                if child.get('successors'):
                    children_dct[child['name']].successors = [
                                        children_dct[ss]
                                        for ss in child['successors']]

            session.add(element)
            session.flush()
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
      hubs_explicitly: true

    additional optional query parameters:
      expand

    """
    query_defaults = {'geom': 'true',
                      'tags': 'true',
                      'sequences': 'true',
                      'children': 'true',
                      'parents': 'true',
                      'predecessors': 'true',
                      'successors': 'true',
                      'hubs_explicitly':'true'}
    with db_session() as session:
        query = session.query
        element = query(schema.Element).filter_by(id=query_args['id']).first()
        element_dct = serialize_element(element)
        element_dct['api_parameters'] = {'version': '0.0.1',
                                        'type': 'element'}
        all_query_args = get_query_args(query_args, query_defaults)
        element_dct['api_parameters']['query'] = all_query_args
        # Use api parameters query for subsetting
        element_dct = subset_json(element_dct, all_query_args)
        if 'expand' in query_args.keys():
            element_dct[query_args['expand']] = expand_element(
                element, query_args)
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

    with db_session() as session:
        elements = get_elements(query_args, session)
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

def create_transmission(json):
    """
    """
    transmission_partners = {}
    for child in json['children']:
        if child['type'] == 'transmission':
            ss = child['successors']
            child['name'] = child['name']
            child['successors'] = [ss[0]]
            child['predecessors']= [ss[1]]

            # create 'partner' transmission object with inversed pre/successor
            obj = child.copy()
            obj['name'] = obj['name'] + '_add'
            obj['successors'] = child['predecessors']
            obj['predecessors'] = child['successors']
            transmission_partners[obj['name']] = obj
    json['children'].extend(transmission_partners.values())
    return json

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
                            elements[name]['sequences'] = elements[name].get('sequences', {})
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
    with db_session() as session:
        if by == 'id':
            element = session.query(schema.Element).filter_by(
                    id=element_identifier).first()
        if by == 'name':
            element = session.query(schema.Element).filter_by(
                    name=element_identifier).first()

        # check if element has more than one parent, if so: raise error
        for child in element.children:
            parents = [parent for parent in child.parents]
            if len(parents) > 1:
                raise ValueError(
                    "Deleting element {0} with all its children failed. " \
                    "Child {1} does have more than one parent.".format(
                      element.name,
                      child.name))

        session.delete(element)


def provide_sequence_api(query_args):
    """
    needs at least id as query argument
    """
    with db_session() as session:
        q = session.query
        sequence = q(schema.Sequence).filter_by(id=query_args['id']).first()
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
    with db_session() as session:
        scenario = session.query(schema.Element).filter(
                        schema.Element.name.like(scenario_name)).first()

        # check if results exist, if so: delete from database
        scenario_results_exist = (session
            .query(schema.ResultSequences)
            .filter_by(scenario_id=scenario.id)
            .all())
        if scenario_results_exist:
            for result in scenario_results_exist:
                session.delete(result)
            session.flush()

        transmission_dct = {}
        transmission_lookup = {}
        for source, v in results_dict.items():
            predecessor = (session
                .query(schema.Element)
                .filter(schema.Element.name.like(source.label))
                .first())
            if not predecessor:
                raise Warning("Missing predeccesor element in db for oemof " \
                              "object {}.".format(source.label))

            for target, seq in v.items():
                successor = (session
                    .query(schema.Element)
                    .filter(schema.Element.name.like(target.label))
                    .first())
                result = schema.ResultSequences(scenario=scenario,
                                                predecessor=predecessor,
                                                successor=successor,
                                                type='result',
                                                value=seq)

                session.add(result)
                session.flush()
                if (getattr(source, 'type', '') == 'transmission'
                        and getattr(target, 'sector', '') == 'electricity'):
                    transmission_dct[(predecessor, successor)] = seq
                if (getattr(source, 'sector', '') == 'electricity'
                        and (getattr(target, 'type', '') == 'transmission'
                                or getattr(target, 'slack', '') == 'true')):
                    transmission_lookup[successor] = predecessor
                if (getattr(source, 'slack', '') == 'true'
                        and getattr(target, 'sector', '') == 'electricity'):
                    transmission_dct[(predecessor, successor)] = seq
                    slack_source = (predecessor, successor)
                if (getattr(source, 'sector', '') == 'electricity'
                        and (getattr(target, 'type', '') == 'sink'
                                and getattr(target, 'slack', '') == 'true')):
                    transmission_dct[(predecessor, successor)] = seq
                    slack_sink = (predecessor, successor)

        # Take slack source hub as hub for slack source and sink
        new_slack_hub = transmission_lookup[slack_source[0]]
        transmission_dct[(new_slack_hub, slack_source[1])] = transmission_dct.pop(slack_source)
        transmission_dct[(slack_sink[0], new_slack_hub)] = transmission_dct.pop(slack_sink)
        slack_source = (new_slack_hub, slack_source[1])
        slack_sink = (slack_sink[0], new_slack_hub)

        timesteps = len(seq)
        # replace source keys (transmission objects) with hub objects
        for old_key, new_key in transmission_lookup.items():
            for k in transmission_dct.keys():
                if k[0] == old_key:
                    transmission_dct[(new_key, k[1])] = transmission_dct.pop(k)
                if k[1] == old_key:
                    transmission_dct[(k[0], new_key)] = transmission_dct.pop(k)
        # right now only works for bidirectional transmissions between all nodes
        # calculate net export for each hub
        edges = list(transmission_dct.keys())
        hubs = list(set([e[0] for e in edges] + [e[1] for e in edges]))

        # slack hub is definde as connected to type sink/source
        try:
            slack_hub = set([slack_source[1], slack_sink[0]])
            if len(slack_hub) == 2:
                raise Exception("Slack sink and source are at different hubs")
            slack_hub = list(slack_hub)[0]
        except:
            raise Exception("Slack sink or slack source is not defined")

        hub_net_exports = {}
        for hub in hubs:
            exports = [
                seq
                for key,seq in transmission_dct.items()
                if key[0] == hub]
            imports = [
                seq
                for key,seq in transmission_dct.items()
                if key[1] == hub]
            ex = [sum(x) for x in zip(*exports)]
            im = [sum(x) for x in zip(*imports)]
            if ex == []:
                ex = [0 for i in range(timesteps)]
            if im == []:
                im = [0 for i in range(timesteps)]
            net_ex = [e - i for e,i in zip(ex, im)]
            hub_net_exports[hub] = [e - i for e,i in zip(ex, im)]

        # create directed graph
        graph = nx.complete_graph(len(hubs), create_using=nx.DiGraph())

        for edge in graph.edges():
            graph.edge[edge[0]][edge[1]]['weight'] = 1


        import_export_dct = {
            (hubs[pre], hubs[suc]): []
            for pre, suc in graph.edges()}
        for i in range(timesteps):
            supply = [round(hub_net_exports[hub][i]) for hub in hubs]
            slack_supply = supply.pop(hubs.index(slack_hub))
            slack_supply = -sum(supply)
            supply.insert(hubs.index(slack_hub), slack_supply)

            # add node to graph with negative (!) supply for each supply node
            for j in range(len(hubs)):
                graph.node[j]['demand'] = -supply[j]
                graph.node[j]['hub'] = hubs[j]

            flow_cost, flow_dct = nx.network_simplex(graph)

            for pre, suc_dct in flow_dct.items():
                for suc, value in suc_dct.items():
                    import_export_dct[(hubs[pre], hubs[suc])].append(value)

        for edge, seq in import_export_dct.items():
            result = schema.ResultSequences(scenario=scenario,
                                            predecessor=edge[0],
                                            successor=edge[1],
                                            type='result',
                                            value=seq)

            session.add(result)
            session.flush()

def get_flow_result(scenario_identifier, predecessor_name, successor_name,
                    by='id'):

    with db_session() as session:
        if by == 'name':
          scenario = (session
              .query(schema.Element)
              .filter(schema.Element.name.like(scenario_identifier))
              .first())
          scenario_id = scenario.id

        else:
            scenario_id = scenario_identifier

            predecessor = (session
                           .query(schema.Element)
                           .filter(schema.Element.name.like(predecessor_name))
                           .first())
            successor = (session
                         .query(schema.Element)
                         .filter(schema.Element.name.like(successor_name))
                         .first())
            flow_result = (session
                           .query(schema.ResultSequences)
                           .filter_by(scenario_id=scenario_id,
                                      predecessor_id=predecessor.id,
                                      successor_id=successor.id)
                       .first())
            flow_result = flow_result.value

    return flow_result

def get_flow_results(scenario_identifier, by='id'):
    """
    Returns
    -------

    If results exist:

    flow_results : dict

    If results do not exist:

    False
    """
    with db_session() as session:
        if by == 'name':
          scenario = (session
              .query(schema.Element)
              .filter(schema.Element.name.like(scenario_identifier))
              .first())
          scenario_id = scenario.id

        else:
            scenario_id = scenario_identifier

        flow_results = (session
                       .query(schema.ResultSequences)
                       .filter_by(scenario_id=scenario_id)
                   .all())

        if flow_results:
            flow_results = {f.predecessor.name: {f.successor.name: {'type': f.type,
                                                                    'value': f.value}}
                                for f in flow_results}
            return flow_results

        else:
            return False

def get_co2_results(scenario_identifier, multi_hub_name, by='id', aggregated=True):
    """ CAUTION: Though this function tries to be kind of generic but was
        developed for the city of KIEL. The co2-balance might therefore not be
        transferable to other projects!!!
    """
    with db_session() as session:
        if by == 'name':
          scenario = (session
              .query(schema.Element)
              .filter(schema.Element.name.like(scenario_identifier))
              .first())
          scenario_id = scenario.id

        else:
            scenario_id = scenario_identifier


        scenario_results = (session
            .query(schema.ResultSequences)
            .filter_by(scenario_id=scenario_id)
            .all())

        if scenario_results:
            # find hubs with close to name 'mult_hub'
            hubs = session.query(schema.Element).filter(
                        schema.Element.name.contains(multi_hub_name),
                        schema.Element.type == 'hub').all()
            # only se
            electricity_hub = [h for h in hubs
                               if get_tag_value(h.tags, 'sector') ==
                                   'electricity'][0]

            # get the hub results for the electrcity hub
            hub_results = get_hub_results(scenario_identifier=scenario_id,
                                          hub_name=electricity_hub.name,
                                          by='id',
                                          aggregated=False)

            electricity_production = hub_results[electricity_hub.name]['production']
            summed_production = [sum(p)
                                 for p in zip(*electricity_production.values())]

            co2_dict = {'import': {},
                        'export': {},
                        'electricity': {},
                        'heat': {}}

            for r in scenario_results:
                # if a flow is connected to the co2 bus, and its predecessor
                # i.e. component is also connected to a multi hub of the name
                # multi hub (r.predecessor.succesors equal to buses that
                # the component is connected to)
                if get_tag_value(r.successor.tags, tag_key='sector') == 'co2' \
                        and [ss.name for ss in r.predecessor.successors
                                     if multi_hub_name in ss.name]:
                    # if its a flexible generator there is only one more output
                    # which is either heat or electricity
                    # (we skip slack component here because they are treated
                    # differently below)
                    if r.predecessor.type == 'flexible_generator' \
                        and not get_tag_value(r.predecessor.tags, 'slack'):
                        # heat components
                        if 'heat' in [get_tag_value(ss.tags, 'sector')
                                      for ss in r.predecessor.successors]:
                            co2_dict['heat'][get_label(r.predecessor)] = r.value
                        # electricity components
                        if 'electricity' in [get_tag_value(ss.tags, 'sector')
                                            for ss in r.predecessor.successors]:
                            co2_dict['electricity'][get_label(r.predecessor)] = r.value

                    # Now we look at flexible generators that are slacks
                    # at the momonent only electricity slack are from interest
                    if r.predecessor.type == 'flexible_generator' \
                        and get_tag_value(r.predecessor.tags, 'slack'):
                        # electricity slack
                        # the net import is between two hubs the 'slack hub'
                        # and the importing hub
                        import_slack_hub = r.predecessor.predecessors[0]
                        net_import = hub_results[electricity_hub.name]['import'][import_slack_hub.name]

                        # the abs import is between the transformer and the
                        # import hub

                        import_slack_transformer = r.predecessor

                        abs_import = get_flow_result(
                                        scenario_identifier=scenario_id,
                                        predecessor_name=import_slack_transformer.name,
                                        successor_name=electricity_hub.name,
                                        by='id')

                        # calculate share and multiply with absolut co2-value
                        import_share = []
                        for i in range(len(net_import)):
                            # avoid float division erro
                            if abs_import[i] != 0:
                                import_share.append(net_import[i] / abs_import[i] * r.value[i])
                            else:
                                import_share.append(0)

                        if 'electricity' in [get_tag_value(ss.tags, 'sector')
                                             for ss in r.predecessor.successors]:
                            co2_dict['import'][get_label(r.predecessor)] = import_share

                    # combined flexbile generators have two other outputs than
                    # co2 where the co2-emissions need to be assigned to
                    # we weight by the energy efficiencies for heat and power
                    if r.predecessor.type == 'combined_flexible_generator':
                        total_efficiency = float(get_tag_value(r.predecessor.tags,
                                                         'thermal_efficiency')) \
                                         + float(get_tag_value(r.predecessor.tags,
                                                         'electrical_efficiency'))
                        heat_share = (float(
                                        get_tag_value(r.predecessor.tags,
                                                      'thermal_efficiency')) /
                                      total_efficiency)
                        el_share = (float(
                                        get_tag_value(r.predecessor.tags,
                                                      'electrical_efficiency')) /
                                      total_efficiency)
                        # weight with 'heat_share' and add to heat result
                        co2_dict['heat'][get_label(r.predecessor)] = [
                                               v * heat_share for v in r.value]
                        # weight with 'el_share' and add to electricity result
                        co2_dict['electricity'][get_label(r.predecessor)] = [
                                                v * el_share for v in r.value]

            # We also need to check the export slacks
            # in the case of electricity we need to weight this with the
            # average emission factor of the production at the bus
            total_co2_production = [
                sum(c) for c in zip(*co2_dict['electricity'].values())]
            emission_factor = []
            emission_export_absolut = []
            for i in range(len(summed_production)):
                emission_factor.append(total_co2_production[i] /
                                            summed_production[i])

                emission_export_absolut.append(
                    emission_factor[i] *
                        hub_results[electricity_hub.name]['export'][import_slack_hub.name][i])

            co2_dict['export'][import_slack_hub.name] = emission_export_absolut

            #import pdb; pdb.set_trace()
            if aggregated == True:
                for k,v in co2_dict.items():
                    co2_dict[k] = sum([sum(c) for c in zip(*co2_dict[k].values())])
                emission_factor = sum(emission_factor) / 8760


            return co2_dict, emission_factor


        else:
            return False

def get_hub_results(scenario_identifier, hub_name, by='id', aggregated=True):
    """ Get the results from the dabase for a given scenario and a given hub.

    Parameters
    ----------
    scenario_identifier : str
        Used to get the scenario from the database
    hub_name : string
        Name of the hub (Element) for which results have to be returned
    by : str
        Used to configure how the scenario is queried. If 'id', the
        scneario_identifier  should be the scenario id, if by='name, it
        should be the scenario name.
    aggregated : boolean
        If True results are summed for the complete timehorizon

    Returns
    -------

    If results exist:

    hub_results : dict

    If results do not exist:

    False


    """
    with db_session() as session:
        if by == 'name':
          scenario = (session
              .query(schema.Element)
              .filter(schema.Element.name.like(scenario_identifier))
              .first())
          scenario_id = scenario.id

        else:
            scenario_id = scenario_identifier

        # check if results exist, if so: delete from database
        scenario_results = (session
            .query(schema.ResultSequences)
            .filter_by(scenario_id=scenario_id)
            .all())

        if scenario_results:
            hub_results = {hub_name: {'demand': {},
                                      'production': {},
                                      'import':{},
                                      'export': {}}}

            # add production and demand to dictionary
            for r in scenario_results:
                if r.successor.name == hub_name:
                    if r.predecessor.type != 'transmission' \
                        and not get_tag_value(r.predecessor.tags, 'slack'):
                        label = get_label(r.predecessor)
                        if (r.predecessor.type == 'hub' or
                            r.predecessor.type == 'source'):
                            hub_results[hub_name]['import'][label] = r.value
                        else:
                            hub_results[hub_name]['production'][label] = r.value
                if r.predecessor.name == hub_name:
                    if r.successor.type not in ['transmission', 'source']:
                        label = get_label(r.successor)
                        if (r.successor.type == 'hub'
                                or r.successor.type == 'sink'):
                            hub_results[hub_name]['export'][label] = r.value
                        else:
                            hub_results[hub_name]['demand'][label] = r.value

            # fix storage: collect all storage keys from production and demand
            # and make them a set, substract demand from production and update
            # production and demand with net values
            storage_net = {}
            keys = ([k for k in hub_results[hub_name]['production'].keys()] +
                    [k for k in hub_results[hub_name]['demand'].keys()])

            storages = set([k for k in keys if keys.count(k) > 1])
            for storage in storages:
                storage_net = [p-d for p,d in
                               zip(hub_results[hub_name]['production'][storage],
                                   hub_results[hub_name]['demand'][storage])]
                hub_results[hub_name]['production'][storage] = \
                    [p if p > 0 else p-p for p in storage_net]
                hub_results[hub_name]['demand'][storage] = \
                    [p if p < 0 else p+p for p in storage_net]

            if aggregated:
                for k in hub_results[hub_name]:
                    for kk in hub_results[hub_name][k]:
                        hub_results[hub_name][k][kk] = \
                            sum(hub_results[hub_name][k][kk])

            return hub_results

        else:
            return False

