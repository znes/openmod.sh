
API
==============================


We provide different API's that might be used. At the moment all API's are based
on JSON objects.
A JSON object representing an element always has a 'type' and a 'name' key.

There are the following protected keys:

* name                 <string>
* type                 <string>
* predecessors         <array>
* successors           <array>
* tags                 <object>
* parents              <array>
* children             <array>


element API
-------------------------------
If an element has 'children', all these elementes i.e. children - objects are
stored under the key 'children' with their name (i.e. a reference to the object)
and not the object itself.

The API can be accessed via:
http://host:port/API/element?id=X


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


If you do not want just a reference to a child, parent, successor or
predecessor, you can submit an additional query parameter 'expand'. Then the
values of the desired key will not be an array of strings containing just the
names, but it will be an array of the objects itself.

