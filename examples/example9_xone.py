from pyshacl import validate

shapes_file = '''
@prefix ex: <http://example.com/ns#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

ex:XoneConstraintExampleShape a sh:NodeShape ;
  sh:targetClass ex:Person ;
  sh:xone (
    [
   	sh:property [
   	  sh:path ex:fullName ;
   	  sh:minCount 1 ; ] ; ]
    [
   	sh:property [
   	  sh:path ex:firstName ;
   	  sh:minCount 1 ; ] ;
   	sh:property [
   	  sh:path ex:lastName ;
   	  sh:minCount 1 ; ] ; ] ) .
'''

shapes_file_format = 'turtle'

data_file = '''
@prefix ex: <http://example.com/ns#> .

ex:Bob a ex:Person ;
  ex:firstName "Robert" ;
  ex:lastName "Coin" .

ex:Carla a ex:Person ;
  ex:fullName "Carla Miller" .

ex:Dory a ex:Person ;
  ex:firstName "Dory" ;
  ex:lastName "Dunce" ;
  ex:fullName "Dory Dunce" .
'''
data_file_format = 'turtle'

output_file = '''
@prefix ex: <http://example.com/ns#> .

'''


def return_shapes_file():
    return shapes_file


def return_data_file():
    return data_file


def return_output_file():
    return output_file


if __name__ == '__main__':
    conforms, v_graph, v_text, dict_paths = validate(data_file, shacl_graph=shapes_file,
                                                     data_graph_format=data_file_format,
                                                     shacl_graph_format=shapes_file_format,
                                                     inference='rdfs', debug=True,
                                                     serialize_report_graph=True)
    print(conforms)
    print(v_graph)
    print(v_text)
