# Skeleton change
- TYPE `gast/gast.py::Assign` — node table entry gains a `type_comment` field: fields become `('targets', 'value', 'type_comment')`
- ADD `gast/ast3.py::Ast3ToGAst.visit_Assign(self, node) -> gast.Assign` — for Python < 3.8, build a gast Assign from an ast Assign with `type_comment=None`
- ADD `gast/ast3.py::GAstToAst3.visit_Assign(self, node) -> ast.Assign` — for Python < 3.8, build an ast Assign from a gast Assign, dropping `type_comment`
- ADD `gast/ast2.py::Ast2ToGAst.visit_Assign(self, node) -> gast.Assign` — build a gast Assign from a Python 2 Assign with `type_comment=None`
- ADD `gast/ast2.py::GAstToAst2.visit_Assign(self, node) -> ast.Assign` — build a Python 2 Assign from a gast Assign, dropping `type_comment`
