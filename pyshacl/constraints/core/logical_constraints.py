# -*- coding: utf-8 -*-
"""
https://www.w3.org/TR/shacl/#core-components-logical
"""
from typing import Dict, List
from warnings import warn

import rdflib

from pyshacl.constraints.constraint_component import ConstraintComponent
from pyshacl.consts import SH
from pyshacl.errors import ConstraintLoadError, ReportableRuntimeError, ShapeRecursionWarning, ValidationFailure
from pyshacl.pytypes import GraphLike
from pyshacl.rdfutil import stringify_node

SH_not = SH.term('not')
SH_and = SH.term('and')
SH_or = SH.term('or')
SH_xone = SH.term('xone')

SH_NotConstraintComponent = SH.term('NotConstraintComponent')
SH_AndConstraintComponent = SH.term('AndConstraintComponent')
SH_OrConstraintComponent = SH.term('OrConstraintComponent')
SH_XoneConstraintComponent = SH.term('XoneConstraintComponent')


class NotConstraintComponent(ConstraintComponent):
    """
    sh:not specifies the condition that each value node cannot conform to a given shape. This is comparable to negation and the logical "not" operator.
    Link:
    https://www.w3.org/TR/shacl/#NotConstraintComponent
    Textual Definition:
    For each value node v: A failure MUST be reported if the conformance checking of v against the shape $not produces a failure. Otherwise, if v conforms to the shape $not, there is validation result with v as sh:value.
    """

    def __init__(self, shape):
        super(NotConstraintComponent, self).__init__(shape)
        not_list = list(self.shape.objects(SH_not))
        if len(not_list) < 1:
            raise ConstraintLoadError(
                "NotConstraintComponent must have at least one sh:not predicate.",
                "https://www.w3.org/TR/shacl/#NotConstraintComponent",
            )
        if len(not_list) > 1:
            raise ConstraintLoadError(
                "NotConstraintComponent must have at most one sh:not predicate.",
                "https://www.w3.org/TR/shacl/#NotConstraintComponent",
            )
        self.not_list = not_list

    @classmethod
    def constraint_parameters(cls):
        return [SH_not]

    @classmethod
    def constraint_name(cls):
        return "NotConstraintComponent"

    @classmethod
    def shacl_constraint_class(cls):
        return SH_NotConstraintComponent

    def make_generic_messages(self, datagraph: GraphLike, focus_node, value_node) -> List[rdflib.Literal]:
        m = "Node {} conforms to shape {}".format(
            stringify_node(datagraph, value_node), stringify_node(self.shape.sg.graph, self.not_list[0])
        )
        return [rdflib.Literal(m)]

    def evaluate(self, target_graph: GraphLike, focus_value_nodes: Dict, _evaluation_path: List):
        """

        :type focus_value_nodes: dict
        :type target_graph: rdflib.Graph
        :type _evaluation_path list
        """
        reports = []
        non_conformant = False
        shape = self.shape
        potentially_recursive = self.recursion_triggers(_evaluation_path)

        def _evaluate_not_constraint(not_c):
            nonlocal self, shape, target_graph, focus_value_nodes, _evaluation_path
            _reports = []
            _non_conformant = False
            not_shape = shape.get_other_shape(not_c)
            if not not_shape:
                raise ReportableRuntimeError(
                    "Shape pointed to by sh:not does not exist or is not " "a well-formed SHACL Shape."
                )
            if not_shape in potentially_recursive:
                warn(ShapeRecursionWarning(_evaluation_path))
                return _non_conformant, _reports
            for f, value_nodes in focus_value_nodes.items():
                for v in value_nodes:
                    try:
                        _is_conform, _r = not_shape.validate(
                            target_graph, focus=v, _evaluation_path=_evaluation_path[:]
                        )
                    except ValidationFailure as e:
                        raise e
                    if _is_conform:
                        # in this case, we _dont_ want to conform!
                        _non_conformant = True
                        rept = self.make_v_result(target_graph, f, value_node=v)
                        _reports.append(rept)
            return _non_conformant, _reports

        for not_c in self.not_list:
            _nc, _r = _evaluate_not_constraint(not_c)
            non_conformant = non_conformant or _nc
            reports.extend(_r)
        return (not non_conformant), reports


class AndConstraintComponent(ConstraintComponent):
    """
    sh:and specifies the condition that each value node conforms to all provided shapes. This is comparable to conjunction and the logical "and" operator.
    Link:
    https://www.w3.org/TR/shacl/#AndConstraintComponent
    Textual Definition:
    For each value node v: A failure MUST be produced if the conformance checking of v against any of the members of $and produces a failure. Otherwise, if v does not conform to each member of $and, there is a validation result with v as sh:value.
    """

    def __init__(self, shape):
        super(AndConstraintComponent, self).__init__(shape)
        and_list = list(self.shape.objects(SH_and))
        if len(and_list) < 1:
            raise ConstraintLoadError(
                "AndConstraintComponent must have at least one sh:and predicate.",
                "https://www.w3.org/TR/shacl/#AndConstraintComponent",
            )
        self.and_list = and_list

    @classmethod
    def constraint_parameters(cls):
        return [SH_and]

    @classmethod
    def constraint_name(cls):
        return "AndConstraintComponent"

    @classmethod
    def shacl_constraint_class(cls):
        return SH_AndConstraintComponent

    def make_generic_messages(self, datagraph: GraphLike, focus_node, value_node) -> List[rdflib.Literal]:
        and_list = " , ".join(
            stringify_node(self.shape.sg.graph, a_c) for a in self.and_list for a_c in self.shape.sg.graph.items(a)
        )
        m = "Node {} does not conforms to all shapes in {}".format(stringify_node(datagraph, value_node), and_list)
        return [rdflib.Literal(m)]

    def evaluate(self, target_graph: GraphLike, focus_value_nodes: Dict, _evaluation_path: List):
        """

        :type focus_value_nodes: dict
        :type target_graph: rdflib.Graph
        :type _evaluation_path: list
        """
        reports = []
        non_conformant = False
        shape = self.shape
        subgraphs = {fn: set() for fn in focus_value_nodes}

        def _evaluate_and_constraint(and_c):
            nonlocal self, shape, target_graph, focus_value_nodes, _evaluation_path
            _reports = []
            _non_conformant = False
            _subgraphs = {}
            sg = shape.sg.graph
            and_list = set(sg.items(and_c))
            if len(and_list) < 1:
                raise ReportableRuntimeError("The list associated with sh:and is not a " "valid RDF list.")
            and_shapes = set()
            for a in and_list:
                and_shape = shape.get_other_shape(a)
                if not and_shape:
                    raise ReportableRuntimeError(
                        "Shape pointed to by sh:and does not exist or " "is not a well-formed SHACL Shape."
                    )
                and_shapes.add(and_shape)
            for f, value_nodes in focus_value_nodes.items():
                for v in value_nodes:
                    passed_all = True
                    v_subgraph = set()
                    for and_shape in and_shapes:
                        try:
                            _is_conform, _r, _sg = and_shape.validate(
                                target_graph, focus=v, _evaluation_path=_evaluation_path[:]
                            )
                            # in v_subgraph, build the union of v's neighborhoods for all shapes in and_list
                            # we will add it this to f's neighborhood
                            for fn in _sg:
                                v_subgraph.update(_sg[fn])
                        except ValidationFailure as e:
                            raise e
                        passed_all = passed_all and _is_conform
                    if not passed_all:
                        _non_conformant = True
                        rept = self.make_v_result(target_graph, f, value_node=v)
                        _reports.append(rept)
                    else:
                        # v conforms to all shapes in and_list, so the neighborhood of this value node (v_subgraph)
                        # should be added to the neighborhood of the focus node (_subgraphs[f])
                        if f in _subgraphs:
                            _subgraphs[f].update(v_subgraph)
                        else:
                            _subgraphs[f] = v_subgraph

            return _non_conformant, _reports, _subgraphs

        for and_c in self.and_list:
            _nc, _r, _sg = _evaluate_and_constraint(and_c)
            non_conformant = non_conformant or _nc
            reports.extend(_r)
            # _sg has a key for each focus node that satisfies the current and_c (note that it should match *all*)
            # so if a focus node is not present, it should be removed from subgraphs
            # if a focus node *is* present, the constraint's neighborhood (_sg[fn]) should be added to subgraphs[fn]
            to_delete = set()
            for fn in subgraphs:
                if fn not in _sg:
                    to_delete.add(fn)
                else:
                    subgraphs[fn].update(_sg[fn])
        return (not non_conformant), reports, subgraphs


class OrConstraintComponent(ConstraintComponent):
    """
    sh:or specifies the condition that each value node conforms to at least one of the provided shapes. This is comparable to disjunction and the logical "or" operator.
    Link:
    https://www.w3.org/TR/shacl/#OrConstraintComponent
    Textual Definition:
    For each value node v: A failure MUST be produced if the conformance checking of v against any of the members produces a failure. Otherwise, if v conforms to none of the members of $or there is a validation result with v as sh:value.
    """

    def __init__(self, shape):
        super(OrConstraintComponent, self).__init__(shape)
        or_list = list(self.shape.objects(SH_or))
        if len(or_list) < 1:
            raise ConstraintLoadError(
                "OrConstraintComponent must have at least one sh:or predicate.",
                "https://www.w3.org/TR/shacl/#OrConstraintComponent",
            )
        self.or_list = or_list

    @classmethod
    def constraint_parameters(cls):
        return [SH_or]

    @classmethod
    def constraint_name(cls):
        return "OrConstraintComponent"

    @classmethod
    def shacl_constraint_class(cls):
        return SH_OrConstraintComponent

    def make_generic_messages(self, datagraph: GraphLike, focus_node, value_node) -> List[rdflib.Literal]:
        or_list = " , ".join(
            stringify_node(self.shape.sg.graph, o_c) for o in self.or_list for o_c in self.shape.sg.graph.items(o)
        )
        m = "Node {} does not conform to one or more shapes in {}".format(
            stringify_node(datagraph, value_node), or_list
        )
        return [rdflib.Literal(m)]

    def evaluate(self, target_graph: GraphLike, focus_value_nodes: Dict, _evaluation_path: List):
        """
        :type target_graph: rdflib.Graph
        :type focus_value_nodes: dict
        :type _evaluation_path: list
        """
        reports = []
        non_conformant = False
        shape = self.shape
        subgraphs = {fn: set() for fn in focus_value_nodes}

        def _evaluate_or_constraint(or_c):
            nonlocal self, shape, target_graph, focus_value_nodes, _evaluation_path
            _reports = []
            _non_conformant = False
            _subgraphs = {}
            sg = shape.sg.graph
            or_list = set(sg.items(or_c))
            if len(or_list) < 1:
                raise ReportableRuntimeError("The list associated with sh:or " "is not a valid RDF list.")
            or_shapes = set()
            for o in or_list:
                or_shape = shape.get_other_shape(o)
                if not or_shape:
                    raise ReportableRuntimeError(
                        "Shape pointed to by sh:or does not exist or " "is not a well-formed SHACL Shape."
                    )
                or_shapes.add(or_shape)
            for f, value_nodes in focus_value_nodes.items():
                for v in value_nodes:
                    passed_any = False
                    for or_shape in or_shapes:
                        try:
                            _is_conform, _r, _sg = or_shape.validate(
                                target_graph, focus=v, _evaluation_path=_evaluation_path[:]
                            )
                            # if f conforms to a shape in or_list, return the neighborhood for f and that shape
                            # if fn conforms to multiple shapes in or_list, make the union of those neighborhoods
                            # (recall that fn conforming to a shape means fn is a key in that shape's _sg)
                            for fn in _sg:
                                if fn in _subgraphs:
                                    _subgraphs[f].update(_sg[fn])
                                else:
                                    _subgraphs[f] = _sg[fn]
                        except ValidationFailure as e:
                            raise e
                        passed_any = passed_any or _is_conform
                    if not passed_any:
                        _non_conformant = True
                        rept = self.make_v_result(target_graph, f, value_node=v)
                        _reports.append(rept)
            return _non_conformant, _reports, _subgraphs

        for or_c in self.or_list:
            _nc, _r, _sg = _evaluate_or_constraint(or_c)
            non_conformant = non_conformant or _nc
            reports.extend(_r)
            # _sg will have a key for each focus node that satisfies the current or_c (note that it should match *all*)
            # so if a focus node is not present, it should be removed from subgraphs
            # if a focus node *is* present, the constraint's neighborhood (_sg[fn]) should be added to subgraphs[fn]
            to_delete = set()
            for fn in subgraphs:
                if fn not in _sg:
                    to_delete.add(fn)
                else:
                    subgraphs[fn].update(_sg[fn])
        return (not non_conformant), reports, subgraphs


class XoneConstraintComponent(ConstraintComponent):
    """
    sh:or specifies the condition that each value node conforms to at least one of the provided shapes. This is comparable to disjunction and the logical "or" operator.
    Link:
    https://www.w3.org/TR/shacl/#XoneConstraintComponent
    Textual Definition:
    For each value node v: A failure MUST be produced if the conformance checking of v against any of the members produces a failure. Otherwise, if v conforms to none of the members of $or there is a validation result with v as sh:value.
    """

    def __init__(self, shape):
        super(XoneConstraintComponent, self).__init__(shape)
        xone_nodes = list(self.shape.objects(SH_xone))
        if len(xone_nodes) < 1:
            raise ConstraintLoadError(
                "XoneConstraintComponent must have at least one sh:xone predicate.",
                "https://www.w3.org/TR/shacl/#XoneConstraintComponent",
            )
        self.xone_nodes = xone_nodes

    @classmethod
    def constraint_parameters(cls):
        return [SH_xone]

    @classmethod
    def constraint_name(cls):
        return "XoneConstraintComponent"

    @classmethod
    def shacl_constraint_class(cls):
        return SH_XoneConstraintComponent

    def make_generic_messages(self, datagraph: GraphLike, focus_node, value_node) -> List[rdflib.Literal]:
        xone_list = " , ".join(
            stringify_node(self.shape.sg.graph, a_c) for a in self.xone_nodes for a_c in self.shape.sg.graph.items(a)
        )
        m = "Node {} does not conform to exactly one shape in {}".format(
            stringify_node(datagraph, value_node), xone_list
        )
        return [rdflib.Literal(m)]

    def evaluate(self, target_graph: GraphLike, focus_value_nodes: Dict, _evaluation_path: List):
        """

        :type focus_value_nodes: dict
        :type target_graph: rdflib.Graph
        :type _evaluation_path list
        """
        reports = []
        non_conformant = False
        shape = self.shape

        def _evaluate_xone_constraint(xone_c):
            nonlocal self, shape, target_graph, focus_value_nodes, _evaluation_path
            _reports = []
            _non_conformant = False
            sg = shape.sg.graph
            xone_list = list(sg.items(xone_c))
            if len(xone_list) < 1:
                raise ReportableRuntimeError("The list associated with sh:xone is not " "a valid RDF list.")
            xone_shapes = list()
            for x in xone_list:
                xone_shape = shape.get_other_shape(x)
                if not xone_shape:
                    raise ReportableRuntimeError(
                        "Shape pointed to by sh:xone does not exist " "or is not a well-formed SHACL Shape."
                    )
                xone_shapes.append(xone_shape)
            for f, value_nodes in focus_value_nodes.items():
                for v in value_nodes:
                    passed_count = 0
                    for xone_shape in xone_shapes:
                        try:
                            _is_conform, _r = xone_shape.validate(
                                target_graph, focus=v, _evaluation_path=_evaluation_path[:]
                            )
                        except ValidationFailure as e:
                            raise e
                        if _is_conform:
                            passed_count += 1
                    if not (passed_count == 1):
                        _non_conformant = True
                        rept = self.make_v_result(target_graph, f, value_node=v)
                        _reports.append(rept)
            return _non_conformant, _reports

        for xone_c in self.xone_nodes:
            _nc, _r = _evaluate_xone_constraint(xone_c)
            non_conformant = non_conformant or _nc
            reports.extend(_r)
        return (not non_conformant), reports
