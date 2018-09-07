# -*- coding: utf-8 -*-
import rdflib

from rdflib.namespace import Namespace
from rdflib import RDFS, RDF, OWL

SH = Namespace('http://www.w3.org/ns/shacl#')

# Classes
RDFS_Class = RDFS.term('Class')
SH_NodeShape = SH.term('NodeShape')
SH_PropertyShape = SH.term('PropertyShape')
SH_ValidationResult = SH.term('ValidationResult')
SH_ValidationReport = SH.term('ValidationReport')
SH_Violation = SH.term('Violation')
SH_Info = SH.term('Info')
SH_Warning = SH.term('Warning')
SH_IRI = SH.term('IRI')
SH_BlankNode = SH.term('BlankNode')
SH_Literal = SH.term('Literal')
SH_BlankNodeOrIRI = SH.term('BlankNodeOrIRI')
SH_BlankNodeORLiteral = SH.term('BlankNodeOrLiteral')
SH_IRIOrLiteral = SH.term('IRIOrLiteral')

# predicates
RDF_type = RDF.term('type')
RDFS_subClassOf = RDFS.term('subClassOf')
SH_path = SH.term('path')
SH_deactivated = SH.term('deactivated')
SH_message = SH.term('message')
SH_name = SH.term('name')
SH_description = SH.term('description')
SH_property = SH.term('property')
SH_node = SH.term('node')
SH_targetClass = SH.term('targetClass')
SH_targetNode = SH.term('targetNode')
SH_targetObjectsOf = SH.term('targetObjectsOf')
SH_targetSubjectsOf = SH.term('targetSubjectsOf')
SH_focusNode = SH.term('focusNode')
SH_resultSeverity = SH.term('resultSeverity')
SH_resultPath = SH.term('resultPath')
SH_resultMessage = SH.term('resultMessage')
SH_sourceConstraintComponent = SH.term('sourceConstraintComponent')
SH_sourceShape = SH.term('sourceShape')
SH_severity = SH.term('severity')
SH_value = SH.term('value')
SH_conforms = SH.term('conforms')
SH_result = SH.term('result')
SH_inversePath = SH.term('inversePath')