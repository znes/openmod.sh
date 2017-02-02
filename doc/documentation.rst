
API's
==============================


We provide different API's that might be used. At the moment all API's are based
on JSON objects.
A JSON object representing an element always has a 'type' and a 'name' key.

There are the following protected keys:

* name                 <string>
* type                 <string>
* predecessor  	       <array>
* successor 	       <array>
* tags                 <object>
* parents              <array>
* children             <array>


LAPI
-------------------------------
LAPI stand for lean API. If an element has 'children', all these elementes i.e.
children - objects are  stored under the key 'children' with their name
(i.e. a reference to the  object) and not the object itself.


.. code:: python

	{
  "children": [
    "load1",
    "bus3",
    "bus1",
    "bus2",
    "gen1",
    "line2",
    "line3",
    "line1"
  ],
  "element_id": 2,
  "name": "pypsa-test",
  "parents": [],
  "predecessors": [],
  "successors": [],
  "tags": {
    "model": "pypsa",
    "name": "pypsa-test",
    "type": "scenario"
  },
  "type": "scenario"
}




XAPI
------------------------------
XAPI stand for extended API. The difference to the LAPI interface is the handling
of children elements. In contrast to the LAPI, the values of the children key
will not be an array of strings containing the names of the children. Instead,
it will be an array of objects, containing the objects of the children with all
their information.


