from rdflib import Graph, URIRef
from pyshacl import Shape
from rdflib.term import _XSD_PFX, _RDF_PFX

_EX_PFX = "http://example.com/ex#"

shapes_graph = '''\
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.com/ex#> .
ex:PersonShape
	a sh:NodeShape ;
	sh:targetClass ex:Person ;
	sh:property [
		sh:path ex:ssn ;
		sh:maxCount 1 ;
		sh:datatype xsd:string ;
	] ;
	sh:property [
		sh:path ex:worksFor ;
		sh:class ex:Company ;
		sh:nodeKind sh:IRI ;
	] ;
	sh:closed true ;
	sh:ignoredProperties ( rdf:type ) .
'''

data_graph = '''\
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.com/ex#> .
ex:Alice
	a ex:Person ;
	ex:ssn "987-65-432A" .

ex:Bob
	a ex:Person ;
	ex:ssn "123-45-6789" ;
	ex:ssn "124-35-6789" .

ex:Calvin
	a ex:Person ;
	ex:birthDate "1971-07-07"^^xsd:date ;
	ex:worksFor ex:UntypedCompany .
'''

if __name__ == '__main__':
    sg = Graph().parse(data=shapes_graph, format="turtle")
    dg = Graph().parse(data=data_graph, format="turtle")

    URI_focus = URIRef(_EX_PFX + "Bob") # ex:Bob or URIRef("http://example.com/ex#Bob")
    URI_path = URIRef(_EX_PFX + "ssn")
    # URI_path = URIRef(_RDF_PFX + "type") # rdf:type

    value_nodes = Shape.value_nodes_from_path(sg, URI_focus, URI_path, dg)
    print(value_nodes)

    # print(URI)
    # print(isinstance(URI, URIRef))
