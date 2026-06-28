"""
Call Graph generator module for IncidentIQ.
Responsible for analyzing codebase function calls and building a directed graph representing the call dependencies.
"""

import ast
import os
from typing import Set, List, Dict, Any, Optional
import networkx as nx


class CallGraph(nx.DiGraph):
    """
    Custom DiGraph containing functions/methods as nodes and caller->callee as edges.
    """
    def get_affected_functions(self, function_name: str, depth: int = 2) -> Set[str]:
        """
        Returns the set of functions affected by changes in function_name,
        bounded by the specified search depth.
        """
        return get_affected_functions(self, function_name, depth)

    def get_callers(self, function_name: str) -> Set[str]:
        """
        Returns the set of direct caller functions for function_name.
        """
        return get_callers(self, function_name)

    def get_blast_radius(self, function_name: str) -> List[str]:
        """
        Returns a human-readable list of affected services/functions.
        """
        return get_blast_radius(self, function_name)


class DefinitionVisitor(ast.NodeVisitor):
    """
    AST visitor to find all defined functions and class methods.
    """
    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.definitions: List[Dict[str, Any]] = []
        self.current_class: Optional[str] = None
        self.function_depth: int = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        prev_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        is_method = self.current_class is not None and self.function_depth == 0
        node_id = f"{self.current_class}.{node.name}" if is_method else node.name
        self.definitions.append({
            "node_id": node_id,
            "name": node.name,
            "filepath": self.filepath,
            "class_name": self.current_class if is_method else None,
            "ast_node": node
        })
        self.function_depth += 1
        self.generic_visit(node)
        self.function_depth -= 1

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)  # type: ignore


def get_affected_functions(G: nx.DiGraph, function_name: str, depth: int = 2) -> Set[str]:
    """
    Returns the set of functions affected by a change in function_name,
    bounded by the specified call depth.
    Uses nx.descendants() filtered by shortest path length.
    """
    if function_name not in G:
        return set()
    descendants = nx.descendants(G, function_name)
    lengths = nx.single_source_shortest_path_length(G, function_name, cutoff=depth)
    return {d for d in descendants if d in lengths}


def get_callers(G: nx.DiGraph, function_name: str) -> Set[str]:
    """
    Returns the set of functions that call function_name directly.
    """
    if function_name not in G:
        return set()
    return set(G.predecessors(function_name))


def get_blast_radius(G: nx.DiGraph, function_name: str) -> List[str]:
    """
    Returns a human-readable list of affected services/functions.
    """
    affected = get_affected_functions(G, function_name, depth=2)
    blast_radius = []
    for node in sorted(affected):
        attrs = G.nodes[node]
        filepath = attrs.get("filepath", "")
        class_name = attrs.get("class_name")
        name = attrs.get("name", node)
        
        file_base = os.path.basename(filepath) if filepath else "unknown"
        if class_name:
            blast_radius.append(f"{file_base}: {class_name}.{name}")
        else:
            blast_radius.append(f"{file_base}: {name}")
    return blast_radius


def build_call_graph(path: str) -> CallGraph:
    """
    Builds the CallGraph from a directory of Python files.

    Args:
        path (str): Path to the codebase root.

    Returns:
        CallGraph: The compiled call dependency graph.
    """
    G = CallGraph()
    definitions: List[Dict[str, Any]] = []

    # Pass 1: Discover all function and method definitions
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                try:
                    tree = ast.parse(content, filename=filepath)
                    visitor = DefinitionVisitor(filepath)
                    visitor.visit(tree)
                    definitions.extend(visitor.definitions)
                except Exception:
                    pass

    # Add nodes to graph
    for df in definitions:
        G.add_node(
            df["node_id"],
            name=df["name"],
            filepath=df["filepath"],
            class_name=df["class_name"]
        )

    # Pass 2: Discover calls inside function bodies and draw directed edges
    for df in definitions:
        caller_id = df["node_id"]
        ast_node = df["ast_node"]

        # Walk through the body of this definition to locate Calls
        for node in ast.walk(ast_node):
            # Ignore class and nested function definitions to avoid mapping internal calls to caller
            if node is not ast_node and isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            if isinstance(node, ast.Call):
                callee_name = None
                if isinstance(node.func, ast.Name):
                    callee_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    callee_name = node.func.attr

                if callee_name:
                    # Find all target nodes in graph that match this callee name
                    for node_id in G.nodes:
                        if node_id == callee_name or node_id.endswith(f".{callee_name}"):
                            G.add_edge(caller_id, node_id)

    return G
