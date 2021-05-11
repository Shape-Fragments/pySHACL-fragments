from pyshacl import validate


shapes_file = '''
@prefix ex: <http://example.com/ns#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

ex:OrConstraintExampleShape a sh:NodeShape ;
  sh:targetNode ex:Bob ;
  sh:or (
    [
   	sh:path ex:firstName ;
   	sh:minCount 1 ; ]
    [
   	sh:path ex:givenName ;
   	sh:minCount 1 ; ] ) .
'''
shapes_file_format = 'turtle'

data_file = '''
@prefix ex: <http://example.com/ns#> .

ex:Bob ex:firstName "Robert" .
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
