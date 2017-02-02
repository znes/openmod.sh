
JSON API
==============================


A JSON object representing an element always has a 'type' and a 'name' key. 
If an element has 'children', all these elementes i.e. children - objects are 
stored under the key 'children' with their objects in an array. The array then 
contains all elements. Children of children (as well as parents of children) 
will only be  stored  in a array with their name (i.e. a reference to the 
object) and not the object itself. 

On a first level the following protected keys exits: 
 
* name 
* type 
* children 

On a second level there are the following protected keys: 

* name                 <string> 
* type                 <string>
* predecessor  	       <array>
* successor 	       <array>	   	
* tags                 <object>
* parents              <array>
* children             <array>  

Example
---------------

.. code:: python

	{
	 "name": "test-scenario",  
	 "type": "scenario",  
	 "tags": {...}, 
	 "children": [
	   {"name": "component1", 
	    "type": "powerplant", 
	    "parents": ["test_scenario"], 
	    "children": [], 
	    "predecessor": [],
	    "successor": [], 
	    "tags": {...},
		},
	 ], 
	}
	

 



