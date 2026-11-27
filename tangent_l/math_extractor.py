import sys
import re
import xml.etree.ElementTree as ET

from tangent_l.mathsymbol import MathSymbol
from tangent_l.symboltree import SymbolTree
from tangent_l.exceptions import UnknownTagException

__author__ = 'Nidhin, FWTompa'

## TODO: produce cleaned_file_content for text indexing on a separate pass (called separately in Version 0.2)
## simplify math extraction by creating simple list of math expressions and then grouping them by SLT, rather than by LaTeX


class MathExtractor:
    def __init__(self):
        pass

    namespace = r"(?:[^> :]*:)?"
    attributes = r"(?: [^>]*)?"
    math_expr = "<"+namespace+"math"+attributes+r">.*?</"+namespace+"math>"
    dollars = r"(?<!\\)\$+"
    latex_expr = dollars+".{1,200}?"+dollars # converted to math_expr in cleaned text
    text_token = r"[^<\s]+"
 
    math_pattern = re.compile(math_expr, re.DOTALL)  # TODO: allow for LaTeX as well
    inner_math = re.compile(".*(<"+math_expr+")", re.DOTALL)  # rightmost <*:math 
    open_tag = re.compile("<(?!/)(?!mws:qvar)"+namespace, re.DOTALL) # up to and including namespace
    close_tag = re.compile("</(?!mws:qvar)"+namespace, re.DOTALL)    # but keep qvar namespace
    xmlns_pattern = re.compile(r"\s+xmlns\s*=\s*\"[^<>=\s]+\"", re.DOTALL)

    @classmethod
    def next_math_token(cls, content):
        token = cls.math_pattern.search(content)
        result = (-1, -1)
        if token is not None:
            result = token.span()
        return result

    @classmethod
    def math_tokens(cls, content):
        """
        extract Math expressions from XML (incl. HTML) file
        
        param content: XML document
        type  content: string

        return: embedded math expressions
        rtype:  list(string) where each string is a MathML expr
        """

        tokens = cls.math_pattern.findall(content)
        math = []

        for token in tokens:
            token = cls.close_tag.sub("</",token)
            token = cls.open_tag.sub("<",token)
            token = token.replace("<Math ","<math ").replace("</Math>","</math>")
            token = cls.xmlns_pattern.sub(" ",token)     
            math.append(token)    

        return math


    @classmethod
    def isolate_pmml(cls,math_expr_str):
        """
        extract the Presentation MathML from a MathML expr
        
        param tree: MathML expression
        type  tree: string
        return: Presentation MathML
        rtype:  string
        """

        math_tree = ET.fromstring(math_expr_str)

        if math_tree.tag != "math":
            math_root=math_tree.find("math") # namespaces have been removed (FWT)
        else:
            math_root = math_tree
        
        application_tex_parent = math_root.find(".//annotation[@encoding='application/x-tex']/..")
        if application_tex_parent is not None:
            application_tex = math_root.find(".//annotation[@encoding='application/x-tex']")
            application_tex_parent.remove(application_tex) # delete any tex annotation

        pmml_markup=math_root.find(".//annotation-xml[@encoding='MathML-Presentation']")
        if pmml_markup is not None:
            pmml_markup.tag = "math"
        else:
            pmml_markup=math_root
            cmml_parent=math_root.find(".//annotation-xml[@encoding='MathML-Content']/..")
            if cmml_parent is not None:
                cmml_markup=math_root.find(".//annotation-xml[@encoding='MathML-Content']")
                cmml_parent.remove(cmml_markup) # delete any Content MML
        pmml_markup.set('xmlns',"http://www.w3.org/1998/Math/MathML") # set the default namespace
        return ET.tostring(pmml_markup)

    @classmethod
    def convert_to_mathsymbol(cls, elem, ignore_formatting = True, unify_symbol_tags = False):
        """
        Parse expression from MathML


        :param elem: mathml
        :type  elem: string

        :rtype MathSymbol or None
        :return root of symbol tree

        """
        if (len(elem) == 0):
            return None
        parser = ET.XMLParser(encoding="utf-8")
        root = ET.fromstring(elem, parser=parser)
        return MathSymbol.parse_from_mathml(root, ignore_formatting, unify_symbol_tags=unify_symbol_tags)

    @classmethod
    def convert_and_link_mathml(cls, elem, document=None, position=None):
        """
        Parse expression from MathML keeping the links to the original MathML for visualization purposes


        :param elem: mathml
        :type  elem: string

        :rtype SymbolTree or None
        :return Symbol tree instance

        """
        if (len(elem) == 0):
            return None


        parser = ET.XMLParser(encoding="utf-8")
        root = ET.fromstring(elem, parser=parser)

        symbol_root = MathSymbol.parse_from_mathml(root)

        return SymbolTree(symbol_root, document, position, root)


    @classmethod
    def parse_from_xml(cls, content, content_id, missing_tags=None, problem_files=None):
        """
        Parse expressions from XML file

        :param content: XML content to be parsed
        :type  content: string
        :param content_id: fileid for indexing or querynum for querying
        :type  content_id: int
        :param missing_tags: dictionary to collect tag errors
        :type  missing_tags: dictionary(tag->set(content_id))
        :param problem_files: dictionary to collect parsing errors
        :type  problem_files: dictionary(str->set(content_id))

        :rtype list(SymbolTree)
        :return list of Symbol trees found in content identified by content_id

        """
        idx = -1
        try:
            trees = cls.math_tokens(content)
            groupBySLT = {}
            for idx, tree in enumerate(trees):
                #print("Parsing doc %s, expr %i" % (content_id,idx),flush=True)
                pmml = cls.isolate_pmml(tree)
                symbol_tree = cls.convert_to_mathsymbol(pmml)
                if symbol_tree:
                    s = symbol_tree.tostring()
                    if s not in groupBySLT:
                        groupBySLT[s] = SymbolTree(symbol_tree,content_id,[idx])
                    else:
                        groupBySLT[s].position.append(idx)
            return(list(groupBySLT.values()))
        
        except UnknownTagException as e:
            print("Unknown tag in file or query "+str(content_id)+": "+e.tag, file=sys.stderr)
            missing_tags[e.tag] = missing_tags.get(e.tag, set())
            missing_tags[e.tag].add([content_id,idx])
        except Exception as err:
            reason = str(err)
            print("Parse error in file or query "+str(content_id)+": "+reason+": "+str(tree), file=sys.stderr)
            raise Exception(reason) # pass on the exception to identify the document or query
