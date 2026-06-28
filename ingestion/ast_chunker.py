"""
AST Chunker module for IncidentIQ.
Responsible for parsing Python codebase files into Abstract Syntax Trees (AST) and extracting logical code chunks (classes, methods, functions).
"""

import ast
import os
from typing import List, Optional
from langchain_core.documents import Document


class CodebaseASTParser(ast.NodeVisitor):
    """
    AST Visitor to extract classes, functions, and methods as logical chunks.
    """
    def __init__(self, source_code: str, filepath: str) -> None:
        self.source_code = source_code
        self.filepath = filepath
        self.documents: List[Document] = []
        self.current_class: Optional[str] = None
        self.inside_function_depth: int = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        source = ast.get_source_segment(self.source_code, node)
        docstring = ast.get_docstring(node) or ""
        
        doc = Document(
            page_content=source if source is not None else "",
            metadata={
                "type": "class",
                "name": node.name,
                "filepath": self.filepath,
                "line_start": node.lineno,
                "line_end": getattr(node, "end_lineno", node.lineno),
                "docstring": docstring,
                "class_name": None
            }
        )
        self.documents.append(doc)
        
        # Track class context
        prev_class = self.current_class
        self.current_class = node.name
        
        # Visit children (methods etc)
        self.generic_visit(node)
        
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        source = ast.get_source_segment(self.source_code, node)
        docstring = ast.get_docstring(node) or ""
        
        # A function is a method if it is defined directly inside a class
        is_method = self.current_class is not None and self.inside_function_depth == 0
        
        doc = Document(
            page_content=source if source is not None else "",
            metadata={
                "type": "method" if is_method else "function",
                "name": node.name,
                "filepath": self.filepath,
                "line_start": node.lineno,
                "line_end": getattr(node, "end_lineno", node.lineno),
                "docstring": docstring,
                "class_name": self.current_class if is_method else None
            }
        )
        self.documents.append(doc)
        
        # Increment function depth context
        self.inside_function_depth += 1
        self.generic_visit(node)
        self.inside_function_depth -= 1

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        # Treat async functions the same as normal functions
        self.visit_FunctionDef(node)  # type: ignore


def chunk_directory(path: str) -> List[Document]:
    """
    Walks a directory of Python files and chunks all of them.

    Args:
        path (str): Path to the target directory.

    Returns:
        List[Document]: List of LangChain Document objects representing code chunks.
    """
    all_documents: List[Document] = []
    
    if not os.path.exists(path):
        return all_documents

    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                try:
                    tree = ast.parse(content, filename=filepath)
                    parser = CodebaseASTParser(content, filepath)
                    parser.visit(tree)
                    all_documents.extend(parser.documents)
                except Exception:
                    # Ignore files that fail to parse
                    pass
                    
    return all_documents
