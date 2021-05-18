from pyshacl import validate


shapes_file = '''
@prefix ex: <http://example.com/ns#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

ex:PatternExampleShape
  a sh:NodeShape ;
  sh:targetNode ex:Bob, ex:Alice, ex:Carol ;
  sh:property [
    sh:path ex:bCode ;
    sh:pattern "^B" ;	# starts with 'B'
    sh:flags "i" ;   	# Ignore case
  ] .
'''
shapes_file_format = 'turtle'

data_file = '''
@prefix ex: <http://example.com/ns#> .

ex:Bob ex:bCode "b101" .
ex:Alice ex:bCode "B102" .
ex:Carol ex:bCode "C103" .
'''
data_file_format = 'turtle'

output_file = '''
@prefix ex: <http://example.com/ns#> .

ex:Bob ex:bCode "b101" .
ex:Alice ex:bCode "B102" .
'''


def return_shapes_file():
    return shapes_file


def return_data_file():
    return data_file


def return_output_file():
    return output_file


