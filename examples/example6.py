from pyshacl import validate


shapes_file = '''
@prefix ex: <http://example.com/ns#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

ex:NewZealandLanguagesShape a sh:NodeShape ;
  sh:targetNode ex:Mountain, ex:Berg ;
  sh:property [
    sh:path ex:prefLabel ;
    sh:languageIn ( "en" "mi" ) ; ] .
'''
shapes_file_format = 'turtle'

data_file = '''
@prefix ex: <http://example.com/ns#> .

ex:Mountain
  ex:prefLabel "Mountain"@en ;
  ex:prefLabel "Hill"@en-NZ ;
  ex:prefLabel "Maunga"@mi .

ex:Berg
  ex:prefLabel "Berg" ;
  ex:prefLabel "Berg"@de ;
  ex:prefLabel ex:BergLabel .
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
