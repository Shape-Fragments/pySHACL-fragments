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

output_file = '''
@prefix ex: <http://example.com/ns#> .

ex:ValidInstance ex:property "One" .
'''


def return_shapes_file():
    return shapes_file


def return_data_file():
    return data_file


def return_output_file():
    return output_file

