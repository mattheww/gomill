# -*- coding: utf-8 -*-

needs_sphinx = '1.0'
extensions = ['sphinx.ext.todo', 'sphinx.ext.pngmath']
templates_path = ['_templates']
source_suffix = '.rst'
source_encoding = 'utf-8'
master_doc = 'index'
project = u'gomill'
copyright = u'2009-2010, Matthew Woodcraft'
version = '0.5'
release = '0.5'
unused_docs = []
exclude_dirnames = ['.git']
pygments_style = 'borland'
modindex_common_prefix = ['gomill.']

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

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

#html_use_modindex = True
#html_use_index = True
html_show_sourcelink = False


pngmath_use_preview = True

todo_include_todos = True


rst_epilog = """
.. |gtp| replace:: :abbr:`GTP (Go Text Protocol)`
.. |sgf| replace:: :abbr:`SGF (Smart Game Format)`
"""

def setup(app):
    app.add_description_unit('action', 'action',
                             indextemplate='pair: %s; ringmaster action')

    app.add_description_unit('gtp', 'gtp',
                             indextemplate='pair: %s; GTP command')

    app.add_description_unit('script', 'script',
                             indextemplate='pair: %s; example script')

    app.add_description_unit(
        'setting', 'setting',
        indextemplate='pair: %s; control file setting')

    app.add_description_unit(
        'mc-setting', 'mc-setting',
        indextemplate='pair: %s; Monte Carlo tuner setting')

    app.add_description_unit(
        'ce-setting', 'ce-setting',
        indextemplate='pair: %s; cross-entropy tuner setting')


# Undo undesirable sphinx code that auto-adds 'xref' class to literals 'True',
# 'False', and 'None'.
from sphinx.writers import html as html_mod
def visit_literal(self, node):
    self.body.append(self.starttag(node, 'tt', '',
                                   CLASS='docutils literal'))
    self.protect_literal_text += 1
html_mod.HTMLTranslator.visit_literal = visit_literal

