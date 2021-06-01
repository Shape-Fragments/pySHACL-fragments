from pyshacl import validate

shapes_file = '''
@prefix ex: <http://example.com/ns#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

ex:QualifiedValueShapeExampleShape
  a sh:NodeShape ;
  sh:targetNode ex:QualifiedValueShapeExampleValidResource ;
  sh:property [
    sh:path ex:parent ;
    sh:qualifiedValueShape [
      sh:path ex:gender ;
      sh:hasValue ex:female ;
    ] ;
    sh:qualifiedMinCount 1 ;
  ] .
'''
shapes_file_format = 'turtle'

data_file = '''
@prefix ex: <http://example.com/ns#> .

ex:QualifiedValueShapeExampleValidResource
  ex:parent ex:John ;
  ex:parent ex:Jane .

ex:John
  ex:gender ex:male .

ex:Jane
  ex:gender ex:female .
'''
data_file_format = 'turtle'

output_file = '''
@prefix ex: <http://example.com/ns#> .

ex:QualifiedValueShapeExampleValidResource
  ex:parent ex:Jane .

ex:Jane
  ex:gender ex:female .
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
