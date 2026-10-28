# Restores the ast.Str class and its .s attribute, removed in Python 3.12,
# because mkdocs-gallery 0.10.4 still uses them to parse example scripts.
# This package is imported by the mkdocs-macros plugin during on_config,
# before the gallery plugin generates the gallery in on_pre_build, so the
# aliases are in place when mkdocs_gallery.py_source_parser runs.
import ast

if not hasattr(ast, "Str"):
    ast.Str = ast.Constant
    ast.Constant.s = property(lambda node: node.value)
