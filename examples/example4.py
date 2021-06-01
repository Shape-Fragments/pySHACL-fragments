from rdflib import Graph
from rdflib.compare import isomorphic

from pyshacl import validate

shapes_file = '''
@prefix ex: <http://example.com/ns#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

ex:NumericRangeExampleShape a sh:NodeShape ;
  sh:targetNode ex:Bob, ex:Alice, ex:Ted ;
  sh:property [
    sh:path ex:age ;
    sh:minInclusive 0 ;
    sh:maxInclusive 150 ; ] .
'''
shapes_file_format = 'turtle'

data_file = '''
@prefix ex: <http://example.com/ns#> .

ex:Bob ex:age 23 .
ex:Alice ex:age 220 .
ex:Ted ex:age "twenty one" .
'''
data_file_format = 'turtle'

output_file = '''
@prefix ex: <http://example.com/ns#> .

ex:Bob ex:age 23 .
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
    predicted_output = Graph()
    for focus in dict_paths:
        for triple in dict_paths[focus]:
            predicted_output.add(triple)

    for s, p, o in predicted_output:
        print(s, p, o)

    correct_output = Graph().parse(format="turtle", data=output_file)
    print("RESULT:", isomorphic(correct_output, predicted_output))
