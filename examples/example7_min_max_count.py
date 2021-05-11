from pyshacl import validate

shapes_file = '''
@prefix ex: <http://example.com/ns#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

ex:SuperShape a sh:NodeShape ;
  sh:property [
  sh:path ex:property ;
  sh:minCount 1 ; ] .

ex:ExampleAndShape a sh:NodeShape ;
  sh:targetNode ex:ValidInstance, ex:InvalidInstance ;
  sh:and (
    ex:SuperShape
    [
   	sh:path ex:property ;
   	sh:maxCount 1 ; ] ) .
'''
shapes_file_format = 'turtle'

data_file = '''
@prefix ex: <http://example.com/ns#> .

ex:ValidInstance ex:property "One" .

# Invalid: more than one property
ex:InvalidInstance
  ex:property "One" ;
  ex:property "Two" .
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
