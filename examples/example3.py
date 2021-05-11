from pyshacl import validate


shapes_file = '''
@prefix ex: <http://example.com/ns#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

ex:MinCountExampleShape a sh:PropertyShape ;
  sh:targetNode ex:Alice, ex:Bob, ex:Jean-Baptiste ;
  sh:path ex:name ;
  sh:minCount 1 .
'''
shapes_file_format = 'turtle'

data_file = '''
@prefix ex: <http://example.com/ns#> .

ex:Alice ex:name "Alice" .
ex:Bob ex:name "Bob"@en .
ex:Jean-Baptiste ex:namee "Jean-Baptiste"@en .
'''
data_file_format = 'turtle'

conforms, v_graph, v_text = validate(data_file, shacl_graph=shapes_file,
                                     data_graph_format=data_file_format,
                                     shacl_graph_format=shapes_file_format,
                                     inference='rdfs', debug=True,
                                     serialize_report_graph=True)
print(conforms)
print(v_graph)
print(v_text)
