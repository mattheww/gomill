# -*- coding: utf-8 -*-

extensions = ['sphinx.ext.todo']
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
pygments_style = 'sphinx'
modindex_common_prefix = ['gomill.']

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

html_theme = 'default'
html_theme_options = {
    'nosidebar'     : False,
    'rightsidebar'  : True,
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
    #'headbgcolor'      : ,
    'headtextcolor'    : '#5c4320',
    #'headlinkcolor'    : ,
    #'codebgcolor'      : ,
    #'codetextcolor'    : ,
    }

html_static_path = ['_static']
html_add_permalinks = False

#html_use_modindex = True
#html_use_index = True
html_show_sourcelink = False


todo_include_todos = True


def setup(app):
    app.add_description_unit('cmdarg', 'cmdarg',
                             indextemplate='pair: %s; ringmaster command')

    app.add_description_unit('confval', 'confval',
                             indextemplate='pair: %s; configuration value')
