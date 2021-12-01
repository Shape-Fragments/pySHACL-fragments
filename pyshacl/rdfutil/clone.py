# -*- coding: utf-8 -*-
#
from typing import Optional, Union

import rdflib

from rdflib.collection import Collection

from .consts import RDF_first
from .pytypes import ConjunctiveLike, GraphLike


def clone_dataset(source_ds, target_ds=None):
    if target_ds and not isinstance(target_ds, (rdflib.Dataset, rdflib.ConjunctiveGraph)):
        raise RuntimeError("when cloning a dataset, the target_ds must be a conjunctiveGraph or rdflib Dataset.")
    default_union = source_ds.default_union
    if target_ds is None:
        target_ds = rdflib.Dataset(default_union=default_union)
    named_graphs = [
        rdflib.Graph(source_ds.store, i, namespace_manager=source_ds.namespace_manager)
        if not isinstance(i, rdflib.Graph)
        else i
        for i in source_ds.store.contexts(None)
    ]
    cloned_graphs = [
        clone_graph(ng, rdflib.Graph(target_ds.store, ng.identifier, namespace_manager=target_ds.namespace_manager))
        for ng in named_graphs
    ]
    default_context_id = target_ds.default_context.identifier
    for g in cloned_graphs:
        if g.identifier == default_context_id:
            target_ds.store.remove_graph(target_ds.default_context)
            target_ds.default_context = g
        target_ds.add_graph(g)
    return target_ds


def clone_graph(source_graph, target_graph=None, identifier=None):
    """
    Make a clone of the source_graph by directly copying triples from source_graph to target_graph
    :param source_graph:
    :type source_graph: rdflib.Graph
    :param target_graph:
    :type target_graph: rdflib.Graph|None
    :param identifier:
    :type identifier: str | None
    :return: The cloned graph
    :rtype: rdflib.Graph
    """
    if isinstance(source_graph, (rdflib.Dataset, rdflib.ConjunctiveGraph)):
        return clone_dataset(source_graph, target_ds=target_graph)
    if target_graph is None:
        g = rdflib.Graph(identifier=identifier)
        for p, n in source_graph.namespace_manager.namespaces():
            g.namespace_manager.bind(p, n, override=True, replace=True)
    else:
        g = target_graph
        for p, n in source_graph.namespace_manager.namespaces():
            g.namespace_manager.bind(p, n, override=False, replace=False)
    for t in iter(source_graph):
        g.add(t)
    return g


def mix_datasets(
    base_ds: ConjunctiveLike, extra_ds: GraphLike, target_ds: Optional[Union[ConjunctiveLike, str]] = None
):
    """
    Make a clone of base_ds (dataset) and add in the triples from extra_ds (dataset)
    :param base_ds:
    :type base_ds: rdflib.Dataset
    :param extra_ds:
    :type extra_ds: rdflib.Dataset
    :param target_ds:
    :type target_ds: rdflib.Dataset|str|NoneType
    :return: The cloned Dataset with mixed in triples from extra_ds
    :rtype: rdflib.Dataset
    """
    default_union = base_ds.default_union
    base_named_graphs = list(base_ds.contexts())
    if target_ds is None:
        target_ds = rdflib.Dataset(default_union=default_union)
    elif isinstance(target_ds, rdflib.ConjunctiveGraph):
        raise RuntimeError("Cannot mix new graphs into a ConjunctiveGraph, use Dataset instead.")
    elif target_ds == "inplace":
        pass  # do nothing here
    elif not isinstance(target_ds, rdflib.Dataset):
        raise RuntimeError("Cannot mix datasets if target_ds passed in is not a Dataset itself.")
    if isinstance(extra_ds, (rdflib.Dataset, rdflib.ConjunctiveGraph)):
        mixin_graphs = list(extra_ds.contexts())
    else:
        mixin_graphs = [extra_ds]
    if target_ds == "inplace":
        target_ds = base_ds
        for mg in mixin_graphs:
            mod_named_graphs = {g.identifier: mix_graphs(g, mg, target_graph="inplace") for g in base_named_graphs}
    elif isinstance(target_ds, str):
        raise RuntimeError("target_ds cannot be a string (unless it is 'inplace')")
    else:

        mixed_graphs = {}
        for mg in mixin_graphs:
            mod_named_graphs = {
                g.identifier: mix_graphs(
                    g, mg, target_graph=rdflib.Graph(store=target_ds.store, identifier=g.identifier)
                )
                for g in base_named_graphs
            }
            mixed_graphs.update(mod_named_graphs)
        default_context_id = target_ds.default_context.identifier
        for i, m in mixed_graphs.items():
            if i == default_context_id:
                target_ds.store.remove_graph(target_ds.default_context)
                target_ds.default_context = m
            target_ds.add_graph(m)
    return target_ds


def mix_graphs(base_graph: GraphLike, extra_graph: GraphLike, target_graph: Optional[Union[GraphLike, str]] = None):
    """
    Make a clone of base_graph and add in the triples from extra_graph
    :param base_graph:
    :type base_graph: rdflib.Graph
    :param extra_graph:
    :type extra_graph: rdflib.Graph
    :param target_graph:
    :type target_graph: rdflib.Graph|str|NoneType
    :return: The cloned graph with mixed in triples from extra_graph
    :rtype: rdflib.Graph
    """
    if isinstance(base_graph, (rdflib.ConjunctiveGraph, rdflib.Dataset)) and isinstance(
        target_graph, (rdflib.ConjunctiveGraph, rdflib.Dataset)
    ):
        return mix_datasets(base_graph, extra_graph, target_ds=target_graph)
    if target_graph is None:
        g = clone_graph(base_graph, target_graph=None, identifier=base_graph.identifier)
    elif target_graph == "inplace":
        # Special case, don't clone the basegraph, just put extra straight in
        g = base_graph
    elif isinstance(target_graph, str):
        raise RuntimeError("target_graph cannot be a string (unless it is 'inplace')")
    else:
        g = clone_graph(base_graph, target_graph=target_graph)
    g = clone_graph(extra_graph, target_graph=g)
    return g


def clone_list(graph, lnode, target_graph, keepid=False, recursion=0):
    if keepid:
        cloned_node = rdflib.BNode(str(lnode))
    else:
        cloned_node = rdflib.BNode()
    new_list = Collection(target_graph, cloned_node)
    for item in iter(graph.items(lnode)):
        cloned_item = clone_node(graph, item, target_graph, recursion=recursion + 1)
        new_list.append(cloned_item)
    return cloned_node


def clone_blank_node(graph, bnode, target_graph, keepid=False, recursion=0):
    if not isinstance(graph, rdflib.Graph):
        raise RuntimeError("clone_blank_node must take an rdflib.Graph as first parameter")
    if not isinstance(bnode, rdflib.BNode):
        raise RuntimeError("clone_blank_node must take an rdflib.BNode as second parameter")
    if keepid:
        cloned_bnode = rdflib.BNode(str(bnode))
    else:
        cloned_bnode = rdflib.BNode()
    if recursion >= 10:
        return cloned_bnode  # Cannot clone this deep

    predicates = set(graph.predicates(bnode))
    if len(predicates) < 1:
        return cloned_bnode
    if RDF_first in predicates:
        # don't increase recursion here, we're not actually going any deeper in the graph, just sideways
        return clone_list(graph, bnode, target_graph, keepid=keepid, recursion=recursion)
    for p in predicates:
        cloned_p = clone_node(graph, p, target_graph, recursion=recursion + 1)
        objs = list(graph.objects(bnode, p))
        if len(objs) < 1:
            continue
        for o in objs:
            cloned_o = clone_node(graph, o, target_graph, recursion=recursion + 1)
            target_graph.add((cloned_bnode, cloned_p, cloned_o))
    return cloned_bnode


def clone_literal(graph, node, target_graph):
    lex_val_string = str(node)
    lang = node.language
    datatype = node.datatype
    new_literal = rdflib.Literal(lex_val_string, lang, datatype)
    return new_literal


def clone_node(graph, node, target_graph, recursion=0):
    if isinstance(node, rdflib.Literal):
        new_node = clone_literal(graph, node, target_graph)
    elif isinstance(node, rdflib.BNode):
        new_node = clone_blank_node(graph, node, target_graph, recursion=recursion + 1)
    elif isinstance(node, rdflib.URIRef):
        new_node = rdflib.URIRef(str(node))
    else:
        new_node = rdflib.term.Identifier(str(node))
    return new_node
