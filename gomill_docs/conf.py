# -*- coding: utf-8 -*-

import sphinx
_sphinx_is_v1x0 = sphinx.__version__.startswith("1.0.")

needs_sphinx = '1.0'
extensions = ['sphinx.ext.todo', 'sphinx.ext.pngmath', 'sphinx.ext.intersphinx',
              'sphinx.ext.viewcode']
templates_path = ['_templates']
source_suffix = '.rst'
source_encoding = 'utf-8'
master_doc = 'index'
project = u'gomill'
copyright = u'2009-2012, Matthew Woodcraft'
version = '0.7.4'
release = '0.7.4'
unused_docs = []
exclude_dirnames = ['.git']
pygments_style = 'vs'
modindex_common_prefix = ['gomill.']

html_theme = 'default'
html_theme_options = {
    'nosidebar'     : False,
    #'rightsidebar'  : True,
    'stickysidebar' : False,

    'footerbgcolor'    : '#3d3011',
    #'footertextcolor'  : ,
    'sidebarbgcolor'   : '#3d3011',
    #'sidebartextcolor' : ,
    'sidebarlinkcolor' : '#d8d898',
    'relbarbgcolor'    : '#523f13',
    #'relbartextcolor'  : ,
    #'relbarlinkcolor'  : ,
    #'bgcolor'          : ,
    #'textcolor'        : ,
    'linkcolor'        : '#7c5f35',
    'visitedlinkcolor' : '#7c5f35',
    #'headbgcolor'      : ,
    'headtextcolor'    : '#5c4320',
    #'headlinkcolor'    : ,
    #'codebgcolor'      : ,
    #'codetextcolor'    : ,

    'externalrefs'     : True,
    }

html_static_path = ['_static']
html_add_permalinks = False
html_copy_source = False
html_sidebars = {'**' : ['wholetoc.html', 'relations.html', 'searchbox.html']}
html_style = "gomill.css"
html_show_sourcelink = False

html_context = {
    'sphinx_v1x0' : _sphinx_is_v1x0,
}

pngmath_use_preview = True

todo_include_todos = True

intersphinx_mapping = {'python': ('http://docs.python.org/2.7',
                                  'python-inv.txt')}


rst_epilog = """
.. |gtp| replace:: :abbr:`GTP (Go Text Protocol)`
.. |sgf| replace:: :abbr:`SGF (Smart Game Format)`
"""

def setup(app):
    app.add_object_type('action', 'action',
                        indextemplate='pair: %s; ringmaster action',
                        objname="Ringmaster action")

    app.add_object_type('gtp', 'gtp',
                        indextemplate='pair: %s; GTP command',
                        objname="GTP command")

    app.add_object_type('script', 'script',
                        indextemplate='pair: %s; example script',
                        objname="Example script")

    app.add_object_type('setting', 'setting',
                        indextemplate='pair: %s; control file setting',
                        objname="Control file setting")

    app.add_object_type('pl-setting', 'pl-setting',
                        indextemplate='pair: %s; Playoff tournament setting',
                        objname="Playoff tournament setting")

    app.add_object_type('aa-setting', 'aa-setting',
                        indextemplate='pair: %s; All-play-all tournament setting',
                        objname="All-play-all tournament setting")

    app.add_object_type('mc-setting', 'mc-setting',
                        indextemplate='pair: %s; Monte Carlo tuner setting',
                        objname="Monte Carlo tuner setting")

    app.add_object_type('ce-setting', 'ce-setting',
                        indextemplate='pair: %s; cross-entropy tuner setting',
                        objname="Cross-entropy tuner setting")

    app.add_crossref_type('setting-cls', 'setting-cls',
                          indextemplate='single: %s',
                          objname="Control file object")

    app.add_crossref_type('pl-setting-cls', 'pl-setting-cls',
                          indextemplate='single: %s',
                          objname="Control file object")

    app.add_crossref_type('mc-setting-cls', 'mc-setting-cls',
                          indextemplate='single: %s',
                           objname="Control file object")

    app.add_crossref_type('ce-setting-cls', 'ce-setting-cls',
                          indextemplate='single: %s',
                          objname="Control file object")


if _sphinx_is_v1x0:
    # Undo undesirable sphinx code that auto-adds 'xref' class to literals
    # 'True', 'False', and 'None' (this was removed in sphinx 1.1)
    from sphinx.writers import html as html_mod
    def visit_literal(self, node):
        self.body.append(self.starttag(node, 'tt', '',
                                       CLASS='docutils literal'))
        self.protect_literal_text += 1
    html_mod.HTMLTranslator.visit_literal = visit_literal

