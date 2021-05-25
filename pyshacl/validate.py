# -*- coding: utf-8 -*-
#
import logging
import sys

from functools import wraps
from os import path
from sys import stderr
from typing import Dict, List, Optional, Set, Tuple, Union

import owlrl
import rdflib

from rdflib.util import from_n3

from .extras import check_extra_installed
from .pytypes import GraphLike
from .target import apply_target_types, gather_target_types

if owlrl.json_ld_available:
    import rdflib_jsonld  # noqa: F401

from rdflib import BNode, Literal, URIRef

#from .shape import global_dict_focus_paths
from . import shape
from .consts import (
    RDF_object,
    RDF_predicate,
    RDF_subject,
    RDF_type,
    RDFS_Resource,
    SH_conforms,
    SH_result,
    SH_resultMessage,
    SH_ValidationReport,
)
from .errors import ReportableRuntimeError, ValidationFailure
from .functions import apply_functions, gather_functions, unapply_functions
from .inference import CustomRDFSOWLRLSemantics, CustomRDFSSemantics
from .monkey import apply_patches, rdflib_bool_patch, rdflib_bool_unpatch
from .rdfutil import (
    clone_blank_node,
    clone_graph,
    compare_blank_node,
    compare_node,
    load_from_source,
    mix_datasets,
    mix_graphs,
    order_graph_literal,
)
from .rdfutil.load import add_baked_in
from .rules import apply_rules, gather_rules
from .shapes_graph import ShapesGraph

log_handler = logging.StreamHandler(stderr)
log = logging.getLogger(__name__)
for h in log.handlers:
    log.removeHandler(h)  # pragma:no cover
log.addHandler(log_handler)
log.setLevel(logging.INFO)
log_handler.setLevel(logging.INFO)


class Validator(object):
    @classmethod
    def _load_default_options(cls, options_dict: dict):
        options_dict.setdefault('advanced', False)
        options_dict.setdefault('inference', 'none')
        options_dict.setdefault('inplace', False)
        options_dict.setdefault('use_js', False)
        options_dict.setdefault('abort_on_error', False)
        if 'logger' not in options_dict:
            options_dict['logger'] = logging.getLogger(__name__)

    @classmethod
    def _run_pre_inference(
        cls, target_graph: GraphLike, inference_option: str, logger: Optional[logging.Logger] = None
    ):
        """
        Note, this is the OWL/RDFS pre-inference,
        it is not the Advanced Spec SHACL-Rule inferencing step.
        :param target_graph:
        :type target_graph: rdflib.Graph|rdflib.ConjunctiveGraph|rdflib.Dataset
        :param inference_option:
        :type inference_option: str
        :return:
        :rtype: NoneType
        """
        if logger is None:
            logger = logging.getLogger(__name__)
        try:
            if inference_option == 'rdfs':
                inferencer = owlrl.DeductiveClosure(CustomRDFSSemantics)
            elif inference_option == 'owlrl':
                inferencer = owlrl.DeductiveClosure(owlrl.OWLRL_Semantics)
            elif inference_option == 'both' or inference_option == 'all' or inference_option == 'rdfsowlrl':
                inferencer = owlrl.DeductiveClosure(CustomRDFSOWLRLSemantics)
            else:
                raise ReportableRuntimeError("Don't know how to do '{}' type inferencing.".format(inference_option))
        except Exception as e:  # pragma: no cover
            logger.error("Error during creation of OWL-RL Deductive Closure")
            if isinstance(e, ReportableRuntimeError):
                raise e
            raise ReportableRuntimeError(
                "Error during creation of OWL-RL Deductive Closure\n" "{}".format(str(e.args[0]))
            )
        if isinstance(target_graph, (rdflib.Dataset, rdflib.ConjunctiveGraph)):
            named_graphs = [
                rdflib.Graph(target_graph.store, i, namespace_manager=target_graph.namespace_manager)
                if not isinstance(i, rdflib.Graph)
                else i
                for i in target_graph.store.contexts(None)
            ]
        else:
            named_graphs = [target_graph]
        try:
            for g in named_graphs:
                inferencer.expand(g)
        except Exception as e:  # pragma: no cover
            logger.error("Error while running OWL-RL Deductive Closure")
            raise ReportableRuntimeError("Error while running OWL-RL Deductive Closure\n" "{}".format(str(e.args[0])))

    @classmethod
    def create_validation_report(cls, sg, conforms: bool, results: List[Tuple]):
        v_text = "Validation Report\nConforms: {}\n".format(str(conforms))
        result_len = len(results)
        if not conforms and result_len < 1:
            raise RuntimeError("A Non-Conformant Validation Report must have at least one result.")
        if result_len > 0:
            v_text += "Results ({}):\n".format(str(result_len))
        vg = rdflib.Graph()
        for p, n in sg.graph.namespace_manager.namespaces():
            vg.namespace_manager.bind(p, n)
        vr = BNode()
        vg.add((vr, RDF_type, SH_ValidationReport))
        vg.add((vr, SH_conforms, Literal(conforms)))
        cloned_nodes: Dict[Tuple[GraphLike, str], Union[BNode, URIRef]] = {}
        for result in iter(results):
            _d, _bn, _tr = result
            v_text += _d
            vg.add((vr, SH_result, _bn))
            for tr in iter(_tr):
                s, p, o = tr
                if isinstance(o, tuple):
                    source = o[0]
                    node = o[1]
                    if isinstance(node, Literal):
                        o = node  # No need to clone a literal from the data graph
                    else:
                        _id = str(node)
                        if (source, _id) in cloned_nodes:
                            o = cloned_nodes[(source, _id)]
                        elif isinstance(node, BNode):
                            cloned_nodes[(source, _id)] = o = clone_blank_node(source, node, vg, keepid=True)
                        else:
                            cloned_nodes[(source, _id)] = o = URIRef(_id)
                vg.add((s, p, o))
        return vg, v_text

    def __init__(
        self,
        data_graph: GraphLike,
        *args,
        shacl_graph: Optional[GraphLike] = None,
        ont_graph: Optional[GraphLike] = None,
        options: Optional[dict] = None,
        **kwargs,
    ):
        options = options or {}
        self._load_default_options(options)
        self.options = options  # type: dict
        self.logger = options['logger']  # type: logging.Logger
        self.pre_inferenced = kwargs.pop('pre_inferenced', False)
        self.inplace = options['inplace']
        if not isinstance(data_graph, rdflib.Graph):
            raise RuntimeError("data_graph must be a rdflib Graph object")
        self.data_graph = data_graph
        self._target_graph = None
        self.ont_graph = ont_graph
        self.data_graph_is_multigraph = isinstance(self.data_graph, (rdflib.Dataset, rdflib.ConjunctiveGraph))
        if self.ont_graph is not None and isinstance(self.ont_graph, (rdflib.Dataset, rdflib.ConjunctiveGraph)):
            self.ont_graph.default_union = True

        if shacl_graph is None:
            shacl_graph = clone_graph(data_graph, identifier='shacl')
        assert isinstance(shacl_graph, rdflib.Graph), "shacl_graph must be a rdflib Graph object"
        self.shacl_graph = ShapesGraph(shacl_graph, self.logger)

        if options['use_js']:
            is_js_installed = check_extra_installed('js')
            if is_js_installed:
                self.shacl_graph.enable_js()

    @property
    def target_graph(self):
        return self._target_graph

    def mix_in_ontology(self):
        if not self.data_graph_is_multigraph:
            return mix_graphs(self.data_graph, self.ont_graph, "inplace" if self.inplace else None)
        return mix_datasets(self.data_graph, self.ont_graph, "inplace" if self.inplace else None)

    def run(self):
        if self.target_graph is not None:
            the_target_graph = self.target_graph
        else:
            has_cloned = False
            if self.ont_graph is not None:
                # creates a copy of self.data_graph, doesn't modify it
                the_target_graph = self.mix_in_ontology()
                has_cloned = True
            else:
                the_target_graph = self.data_graph
            inference_option = self.options.get('inference', 'none')
            if inference_option and not self.pre_inferenced and str(inference_option) != "none":
                if not has_cloned and not self.inplace:
                    the_target_graph = clone_graph(the_target_graph)
                self._run_pre_inference(the_target_graph, inference_option, self.logger)
                self.pre_inferenced = True
            self._target_graph = the_target_graph

        shapes = self.shacl_graph.shapes  # This property getter triggers shapes harvest.

        if self.options['advanced']:
            target_types = gather_target_types(self.shacl_graph)
            advanced = {'functions': gather_functions(self.shacl_graph), 'rules': gather_rules(self.shacl_graph)}
            for s in shapes:
                s.set_advanced(True)
            apply_target_types(target_types)
        else:
            advanced = {}
        if isinstance(the_target_graph, (rdflib.Dataset, rdflib.ConjunctiveGraph)):
            named_graphs = [
                rdflib.Graph(the_target_graph.store, i, namespace_manager=the_target_graph.namespace_manager)
                if not isinstance(i, rdflib.Graph)
                else i
                for i in the_target_graph.store.contexts(None)
            ]
        else:
            named_graphs = [the_target_graph]
        reports = []
        non_conformant = False

        dict_focus_paths = {}
        _focus_path_temp = None
        for g in named_graphs:
            if advanced:
                apply_functions(advanced['functions'], g)
                apply_rules(advanced['rules'], g)
            for s in shapes:
                _is_conform, _reports, _focus_path_temp = s.validate(g, return_path=True)
                # Iterate over all focus nodes and update them according to the new shape:
                # If a non-conforming path is received, then delete that focus node from dict
                # If a conforming path is received, then add the path to corresponding focus node in the dict
                if _focus_path_temp is not None:
                    for f in _focus_path_temp:
                        if _focus_path_temp[f] == False:
                            if f in dict_focus_paths:
                                dict_focus_paths.pop(f)
                        else:
                            if f in dict_focus_paths:
                                dict_focus_paths[f].extend(_focus_path_temp[f])
                            else:
                                dict_focus_paths[f] = _focus_path_temp[f]

                non_conformant = non_conformant or (not _is_conform)
                reports.extend(_reports)
            if advanced:
                unapply_functions(advanced['functions'], g)
        v_report, v_text = self.create_validation_report(self.shacl_graph, not non_conformant, reports)

        # Convert all list of paths to sets to avoid duplicate paths
        for f in dict_focus_paths:
            dict_focus_paths[f] = set(dict_focus_paths[f])
        # Keep only target nodes as keys within the dictionary
        dict_focus_paths = keep_only_target_nodes(dict_focus_paths)
        """# Print the conforming subgraph if non-empty
        if len(dict_focus_paths) > 0:
            for f in dict_focus_paths:
                print("Path(s) of conforming focus node ", f, ": ", dict_focus_paths[f])
        else:
            print("EMPTY SUBGRAPH: There are NO conforming focus nodes!")"""

        shape.global_dict_focus_paths.clear()
        return (not non_conformant), v_report, v_text, dict_focus_paths


# Returns dictionary with only target nodes as keys (+ remove keys with empty values)
def keep_only_target_nodes(dict):
    temp_dic = {}
    for f in dict:
        temp_dic[f] = []
    for f in dict:
        for path in dict[f]:
            if path[2] in dict:
                temp_dic[f].append(path[2])
    for node in temp_dic:
        for node_to_add in temp_dic[node]:
            dict[node].update(dict.pop(node_to_add))
    # Remove keys with empty values from dictionary
    dict_ret = dict.copy()
    for node in dict:
        if len(dict[node]) < 1:
            dict_ret.pop(node)
    return dict_ret


def assign_baked_in():
    if getattr(sys, 'frozen', False):
        # runs in a pyinstaller bundle
        HERE = sys._MEIPASS
    else:
        HERE = path.dirname(__file__)
    shacl_file = path.join(HERE, "assets", "shacl.pickle")
    add_baked_in("http://www.w3.org/ns/shacl", shacl_file)
    add_baked_in("https://www.w3.org/ns/shacl", shacl_file)
    add_baked_in("http://www.w3.org/ns/shacl.ttl", shacl_file)
    shacl_shacl_file = path.join(HERE, "assets", "shacl-shacl.pickle")
    add_baked_in("http://www.w3.org/ns/shacl-shacl", shacl_shacl_file)
    add_baked_in("https://www.w3.org/ns/shacl-shacl", shacl_shacl_file)
    add_baked_in("http://www.w3.org/ns/shacl-shacl.ttl", shacl_shacl_file)


def with_metashacl_shacl_graph_cache(f):
    # noinspection PyPep8Naming
    EMPTY = object()

    @wraps(f)
    def wrapped(*args, **kwargs):
        graph_cache = getattr(wrapped, "graph_cache", None)
        assert graph_cache is not None
        if graph_cache is EMPTY:
            import pickle

            if getattr(sys, 'frozen', False):
                # runs in a pyinstaller bundle
                here_dir = sys._MEIPASS
            else:
                here_dir = path.dirname(__file__)
            pickle_file = path.join(here_dir, "assets", "shacl-shacl.pickle")
            with open(pickle_file, 'rb') as shacl_pickle:
                u = pickle.Unpickler(shacl_pickle, fix_imports=False)
                shacl_shacl_store, identifier = u.load()
            shacl_shacl_graph = rdflib.Graph(store=shacl_shacl_store, identifier=identifier)
            setattr(wrapped, "graph_cache", shacl_shacl_graph)
        return f(*args, **kwargs)

    setattr(wrapped, "graph_cache", EMPTY)
    return wrapped


@with_metashacl_shacl_graph_cache
def meta_validate(shacl_graph: Union[GraphLike, str], inference: Optional[str] = 'rdfs', **kwargs):
    shacl_shacl_graph = meta_validate.graph_cache
    shacl_graph = load_from_source(shacl_graph, rdf_format=kwargs.pop('shacl_graph_format', None), multigraph=True)
    _ = kwargs.pop('meta_shacl', None)
    return validate(shacl_graph, shacl_graph=shacl_shacl_graph, inference=inference, **kwargs)


def validate(
    data_graph: Union[GraphLike, str, bytes],
    *args,
    shacl_graph: Optional[Union[GraphLike, str, bytes]] = None,
    ont_graph: Optional[Union[GraphLike, str, bytes]] = None,
    advanced: Optional[bool] = False,
    inference: Optional[str] = None,
    inplace: Optional[bool] = False,
    abort_on_error: Optional[bool] = False,
    **kwargs,
):
    """
    :param data_graph: rdflib.Graph or file path or web url of the data to validate
    :type data_graph: rdflib.Graph | str | bytes
    :param args:
    :type args: list
    :param shacl_graph: rdflib.Graph or file path or web url of the SHACL Shapes graph to use to
    validate the data graph
    :type shacl_graph: rdflib.Graph | str | bytes
    :param ont_graph: rdflib.Graph or file path or web url of an extra ontology document to mix into the data graph
    :type ont_graph: rdflib.Graph | str | bytes
    :param advanced: Enable advanced SHACL features, default=False
    :type advanced: bool | None
    :param inference: One of "rdfs", "owlrl", "both", "none", or None
    :type inference: str | None
    :param inplace: If this is enabled, do not clone the datagraph, manipulate it inplace
    :type inplace: bool
    :param abort_on_error:
    :type abort_on_error: bool | None
    :param kwargs:
    :return:
    """

    if kwargs.get('debug', False):
        log_handler.setLevel(logging.DEBUG)
        log.setLevel(logging.DEBUG)
    apply_patches()
    assign_baked_in()
    do_check_dash_result = kwargs.pop('check_dash_result', False)  # type: bool
    do_check_sht_result = kwargs.pop('check_sht_result', False)  # type: bool
    if kwargs.get('meta_shacl', False):
        to_meta_val = shacl_graph or data_graph
        conforms, v_r, v_t = meta_validate(to_meta_val, inference=inference, **kwargs)
        if not conforms:
            msg = "Shacl File does not validate against the Shacl Shapes Shacl file.\n{}".format(v_t)
            log.error(msg)
            raise ReportableRuntimeError(msg)
    do_owl_imports = kwargs.pop('do_owl_imports', False)
    data_graph_format = kwargs.pop('data_graph_format', None)
    # force no owl imports on data_graph
    data_graph = load_from_source(data_graph, rdf_format=data_graph_format, multigraph=True, do_owl_imports=False)
    ont_graph_format = kwargs.pop('ont_graph_format', None)
    if ont_graph is not None:
        ont_graph = load_from_source(
            ont_graph, rdf_format=ont_graph_format, multigraph=True, do_owl_imports=do_owl_imports
        )
    shacl_graph_format = kwargs.pop('shacl_graph_format', None)
    if shacl_graph is not None:
        rdflib_bool_patch()
        shacl_graph = load_from_source(
            shacl_graph, rdf_format=shacl_graph_format, multigraph=True, do_owl_imports=do_owl_imports
        )
        rdflib_bool_unpatch()
    use_js = kwargs.pop('js', None)
    validator = None
    try:
        validator = Validator(
            data_graph,
            shacl_graph=shacl_graph,
            ont_graph=ont_graph,
            options={
                'inference': inference,
                'inplace': inplace,
                'abort_on_error': abort_on_error,
                'advanced': advanced,
                'use_js': use_js,
                'logger': log,
            },
        )
        conforms, report_graph, report_text, dict_paths = validator.run()
    except ValidationFailure as e:
        conforms = False
        report_graph = e
        report_text = "Validation Failure - {}".format(e.message)
    if do_check_dash_result and validator is not None:
        passes = check_dash_result(validator, report_graph, shacl_graph or data_graph)
        return passes, report_graph, report_text
    if do_check_sht_result:
        (sht_graph, sht_result_node) = kwargs.pop('sht_validate', (False, None))
        if not sht_result_node:
            raise RuntimeError("Cannot check SHT result if SHT graph and result node are not given.")
        passes = check_sht_result(report_graph, sht_graph or shacl_graph or data_graph, sht_result_node)
        return passes, report_graph, report_text
    do_serialize_report_graph = kwargs.pop('serialize_report_graph', False)
    if do_serialize_report_graph and isinstance(report_graph, rdflib.Graph):
        if not (isinstance(do_serialize_report_graph, str)):
            do_serialize_report_graph = 'turtle'
        report_graph = report_graph.serialize(None, encoding='utf-8', format=do_serialize_report_graph)
    return conforms, report_graph, report_text, dict_paths


def clean_validation_reports(actual_graph, actual_report, expected_graph, expected_report):
    # remove rdfs-added stuff
    # remove resultMessage if expected_report does not include result_message
    # expected_graph.remove((expected_report, RDF_type, RDFS_Resource))
    # actual_graph.remove((actual_report, RDF_type, RDFS_Resource))
    expected_graph.remove((None, RDF_type, RDFS_Resource))
    actual_graph.remove((None, RDF_type, RDFS_Resource))
    expected_results = list(expected_graph.objects(expected_report, SH_result))
    actual_results = list(actual_graph.objects(actual_report, SH_result))
    er_has_messages = None
    for er in expected_results:
        expected_graph.remove((er, RDF_type, RDFS_Resource))
        er_has_messages = list(expected_graph.objects(er, SH_resultMessage))
        # sourceShapes = list(expected_graph.objects(er, SH_sourceShape))
        # for s in sourceShapes:
        #     expected_graph.remove((s, RDF_type, RDFS_Resource))
        # resultPaths = list(expected_graph.objects(er, SH_resultPath))
        # for r in resultPaths:
        #     expected_graph.remove((r, RDF_type, RDFS_Resource))
        # sourceConstraints = list(expected_graph.objects(er, SH_sourceConstraint))
        # for s in sourceConstraints:
        #     expected_graph.remove((s, RDF_type, RDFS_Resource))
    if er_has_messages and len(er_has_messages) > 0:
        # keep messages in actual
        pass
    else:
        for ar in actual_results:
            actual_graph.remove((ar, SH_resultMessage, None))
    return True


def compare_validation_reports(report_graph: GraphLike, expected_graph: GraphLike, expected_result):
    expected_conforms = expected_graph.objects(expected_result, SH_conforms)
    expected_conforms = set(expected_conforms)
    if len(expected_conforms) < 1:  # pragma: no cover
        raise ReportableRuntimeError(
            "Cannot check the expected result, the given expectedResult does not have an sh:conforms."
        )
    expected_conforms = next(iter(expected_conforms))
    expected_result_nodes = expected_graph.objects(expected_result, SH_result)
    expected_result_nodes = set(expected_result_nodes)
    expected_result_node_count = len(expected_result_nodes)

    validation_reports = report_graph.subjects(RDF_type, SH_ValidationReport)
    validation_reports = set(validation_reports)
    if len(validation_reports) < 1:  # pragma: no cover
        raise ReportableRuntimeError(
            "Cannot check the validation report, the report graph does not contain a ValidationReport"
        )
    validation_report = next(iter(validation_reports))
    clean_validation_reports(report_graph, validation_report, expected_graph, expected_result)
    eq = compare_blank_node(report_graph, validation_report, expected_graph, expected_result)
    if eq != 0:
        return False
    report_conforms = report_graph.objects(validation_report, SH_conforms)
    report_conforms = set(report_conforms)
    if len(report_conforms) < 1:  # pragma: no cover
        raise ReportableRuntimeError(
            "Cannot check the validation report, the report graph does not have an sh:conforms."
        )
    report_conforms = next(iter(report_conforms))

    if bool(expected_conforms.value) != bool(report_conforms.value):
        # TODO:coverage: write a test for this
        log.error("Expected Result Conforms value is different from Validation Report's Conforms value.")
        return False

    report_result_nodes = report_graph.objects(validation_report, SH_result)
    report_result_nodes = set(report_result_nodes)
    report_result_node_count = len(report_result_nodes)

    if expected_result_node_count != report_result_node_count:
        # TODO:coverage: write a test for this
        log.error(
            "Number of expected result's sh:result entries is different from Validation Report's sh:result entries.\n"
            "Expected {}, got {}.".format(expected_result_node_count, report_result_node_count)
        )
        return False
    return True


def compare_inferencing_reports(data_graph: GraphLike, expected_graph: GraphLike, expected_results: Union[List, Set]):
    all_good = True
    for expected_result in expected_results:
        expected_object = set(expected_graph.objects(expected_result, RDF_object))
        if len(expected_object) < 1:
            raise ReportableRuntimeError(
                "Cannot check the expected result, the given expectedResult does not have an rdf:object."
            )
        expected_object = next(iter(expected_object))
        expected_subject = set(expected_graph.objects(expected_result, RDF_subject))
        if len(expected_subject) < 1:
            raise ReportableRuntimeError(
                "Cannot check the expected result, the given expectedResult does not have an rdf:subject."
            )
        expected_subject = next(iter(expected_subject))
        expected_predicate = set(expected_graph.objects(expected_result, RDF_predicate))
        if len(expected_predicate) < 1:
            raise ReportableRuntimeError(
                "Cannot check the expected result, the given expectedResult does not have an rdf:predicate."
            )
        expected_predicate = next(iter(expected_predicate))
        if isinstance(expected_object, Literal):
            found_objs = set(data_graph.objects(expected_subject, expected_predicate))
            if len(found_objs) < 1:
                all_good = False
                print("Found no sub/pred matching {} {}".format(expected_subject, expected_predicate))
                continue
            found = False
            for o in found_objs:
                if isinstance(o, Literal):
                    found = 0 == order_graph_literal(expected_graph, expected_object, data_graph, o)
                    if found:
                        break
            if not found:
                print(
                    "Found no sub/pred/obj matching {} {} {}".format(
                        expected_subject, expected_predicate, expected_object
                    )
                )
            all_good = all_good and found
            continue

        elif isinstance(expected_object, BNode):
            found_objs = set(data_graph.objects(expected_subject, expected_predicate))
            if len(found_objs) < 1:
                all_good = False
                print("Found no sub/pred matching {} {}".format(expected_subject, expected_predicate))
                continue
            found = False
            for o in found_objs:
                if isinstance(o, BNode):
                    found = 0 == compare_blank_node(expected_graph, expected_object, data_graph, o)
                    if found:
                        break
            if not found:
                print(
                    "Found no sub/pred/obj matching {} {} {}".format(
                        expected_subject, expected_predicate, expected_object
                    )
                )
            all_good = all_good and found
            continue
        else:
            found_triples = set(data_graph.triples((expected_subject, expected_predicate, expected_object)))
            if len(found_triples) < 1:
                all_good = False

    return all_good


def check_dash_result(validator: Validator, report_graph: GraphLike, expected_result_graph: GraphLike):
    DASH = rdflib.namespace.Namespace('http://datashapes.org/dash#')
    DASH_GraphValidationTestCase = DASH.term('GraphValidationTestCase')
    DASH_InferencingTestCase = DASH.term('InferencingTestCase')
    DASH_FunctionTestCase = DASH.term('FunctionTestCase')
    DASH_expectedResult = DASH.term('expectedResult')
    DASH_expression = DASH.term('expression')
    was_default_union = None
    if isinstance(expected_result_graph, (rdflib.ConjunctiveGraph, rdflib.Dataset)):
        was_default_union = expected_result_graph.default_union
        expected_result_graph.default_union = True  # Force default-union to make all of this a bit easier
    gv_test_cases = expected_result_graph.subjects(RDF_type, DASH_GraphValidationTestCase)
    gv_test_cases = set(gv_test_cases)
    inf_test_cases = expected_result_graph.subjects(RDF_type, DASH_InferencingTestCase)
    inf_test_cases = set(inf_test_cases)
    fn_test_cases = expected_result_graph.subjects(RDF_type, DASH_FunctionTestCase)
    fn_test_cases = set(fn_test_cases)
    if len(gv_test_cases) > 0:
        test_case = next(iter(gv_test_cases))
        expected_results = expected_result_graph.objects(test_case, DASH_expectedResult)
        expected_results = set(expected_results)
        if len(expected_results) < 1:  # pragma: no cover
            raise ReportableRuntimeError(
                "Cannot check the expected result, the given GraphValidationTestCase does not have an expectedResult."
            )
        expected_result = next(iter(expected_results))
        gv_res: Union[bool, None] = compare_validation_reports(report_graph, expected_result_graph, expected_result)
    else:
        gv_res = None
    if len(inf_test_cases) > 0:
        data_graph = validator.target_graph
        if isinstance(data_graph, (rdflib.ConjunctiveGraph, rdflib.Dataset)):
            named_graphs = list(data_graph.contexts())
        else:
            named_graphs = [data_graph]
        inf_res: Union[bool, None] = True
        for test_case in inf_test_cases:
            expected_results = expected_result_graph.objects(test_case, DASH_expectedResult)
            expected_results = set(expected_results)
            if len(expected_results) < 1:  # pragma: no cover
                raise ReportableRuntimeError(
                    "Cannot check the expected result, the given InferencingTestCase does not have an expectedResult."
                )
            found = False
            for g in named_graphs:
                found = found or compare_inferencing_reports(g, expected_result_graph, expected_results)
            inf_res = inf_res and found
    else:
        inf_res = None
    if len(fn_test_cases) > 0:
        data_graph = validator.target_graph
        fns = gather_functions(validator.shacl_graph)
        apply_functions(fns, data_graph)
        fn_res: Union[bool, None] = True
        for test_case in fn_test_cases:
            expected_results = set(expected_result_graph.objects(test_case, DASH_expectedResult))
            if len(expected_results) < 1:  # pragma: no cover
                raise ReportableRuntimeError(
                    "Cannot check the expected result, the given FunctionTestCase does not have an expectedResult."
                )
            expected_result = next(iter(expected_results))
            expressions = set(expected_result_graph.objects(test_case, DASH_expression))
            if len(expressions) < 1:
                raise ReportableRuntimeError(
                    "Cannot check the expected result, the given FunctionTestCase does not have an expression."
                )
            expression = next(iter(expressions))
            expression = str(expression).strip()
            parts = [e.strip() for e in expression.split("(", 1)]
            if len(parts) < 1:
                expression = parts[0]
                eargs: List[Union[str, URIRef]] = []
            else:
                expression, sargs = parts
                sargs = sargs.rstrip(")")
                if len(sargs) < 1:
                    eargs = []
                else:
                    eargs = [a.strip() for a in sargs.split(',')]
                eargs = [
                    from_n3(e, None, expected_result_graph.store, expected_result_graph.namespace_manager)
                    for e in eargs
                ]
            find_uri = from_n3(expression, None, expected_result_graph.store, expected_result_graph.namespace_manager)
            try:
                fn, options = validator.shacl_graph.get_shacl_function(find_uri)
            except KeyError:
                raise ReportableRuntimeError(
                    "Cannot execute function {}.\nCannot find it in the ShapesGraph object.".format(find_uri)
                )
            result = fn(data_graph, *eargs)
            fn_res = fn_res and 0 == compare_node(expected_result_graph, expected_result, data_graph, result)

    else:
        fn_res = None
    if was_default_union is not None:
        expected_result_graph.default_union = was_default_union
    if gv_res is None and inf_res is None and fn_res is None:  # pragma: no cover
        raise ReportableRuntimeError(
            "Cannot check the expected result, the given expected result graph does not have a GraphValidationTestCase or InferencingTestCase."
        )
    return (gv_res or gv_res is None) and (inf_res or inf_res is None) and (fn_res or fn_res is None)


def check_sht_result(report_graph: GraphLike, sht_graph: GraphLike, sht_result_node: Union[URIRef, BNode]):
    SHT = rdflib.namespace.Namespace('http://www.w3.org/ns/shacl-test#')
    types = set(sht_graph.objects(sht_result_node, RDF_type))
    expected_failure = sht_result_node == SHT.Failure
    if expected_failure and isinstance(report_graph, ValidationFailure):
        return True
    elif isinstance(report_graph, ValidationFailure):
        # TODO:coverage: write a test for this
        log.error("Validation Report indicates a Validation Failure, but the SHT entry does not expect a failure.")
        return False
    elif expected_failure:
        # TODO:coverage: write a test for this
        log.error(
            "SHT expects a Validation Failure, but the Validation Report does not indicate a Validation Failure."
        )
        return False
    if SH_ValidationReport not in types:
        raise ReportableRuntimeError("SHT expected result must have type sh:ValidationReport")
    return compare_validation_reports(report_graph, sht_graph, sht_result_node)
