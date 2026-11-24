import sys

from tangent_l.math_extractor import MathExtractor

PAYLOAD_DELIMITER = "|__|"
PAYLOAD_SEPARATOR = ":"
START_TAG = "#(start)#"
END_TAG = "#(end)#"
TERMINAL_NODE = "terminal_node"
COMPOUND_NODE = "compound_node"
EDGE_PAIR_NODE = "edge_pair"
EOL_NODE = "eol_node"
SYMBOL_PAIR_NODE = "symbol_pair"
EDGES = ['n', 'a', 'b', 'c', 'o', 'u', 'd', 'w', 'e']
WILDCARD_MOCK = "?x"
WILDCARD = "*"
WINDOWS = "nt"
ENCODING = "utf-8"

def get_slt_from_mathml(mathml,
                        as_string=True,
                        output_pmml=False,
                        ignore_formatting = True):
    """Returns the slt in terms of a tree of MathSymbols.

    Parameters:
        mathml: the math expression (string)
        (as_string): True if SLT should be outputted as a string.
        (output_pmml): True if pmml (mathml string) should be outputted too along with the SLT.
        (ignore_formatting): True if SLT should ignore mathvariant attributes at the MathML nodes.
    Returns:
        : MathSymbol (default) or string (if as_string is True)
        : if output_mml is True, the extracted math pmml (as string)
    """

    try:
        tokens = MathExtractor.math_tokens(mathml)
        pmml = MathExtractor.isolate_pmml(tokens[0])
    except: # MathML is mal-formed
        print("Badly formed MathML expression in data file or query : " + mathml,file=sys.stderr)
        return ""
    
    tree_root = MathExtractor.convert_to_mathsymbol(pmml, ignore_formatting)

    if as_string:
        tree_root = tree_root.tostring()

    if output_pmml:
        return tree_root, pmml
    else:
        return tree_root


def convert_math_expression(mathml,
                            window_size=1,
                            symbol_pairs=True,
                            eol=False,
                            compound_symbols=False,
                            terminal_symbols=False,
                            edge_pairs=False,
                            unbounded=False,
                            shortened=True,
                            location=False,
                            synonyms=False,
                            no_payload=False,
                            expand_location=False):
    """Returns the math tuples for a given math expression

    Parameters:
        mathml: the math expression (string)
        (window_size): The size of the path between nodes for symbols pairs
        (symbol_pairs): True will include symbol pairs
        (eol): True will included eol nodes
        (compound_symbols): True to include compound symbols nodes
        (terminal_symbols): True to include terminal symbols nodes
        (edge_pairs): True to include edge pairs nodes
        (unbounded): True - unbounded window size
        (shortened): True - shorten symbol pair paths
        (location): True to include location for symbol pairs along with path
        (synonyms): True to expand nodes to include wildcard expansion
    Returns:
        : a string of the math tuples
    """

    tree_root = get_slt_from_mathml(mathml,as_string=False)

    if tree_root is not None:
        height = tree_root.get_height()
        eol_check = False
        if height <= 2:
            eol_check = eol
        pairs = tree_root.get_pairs("",
                                    window_size,
                                    eol=eol_check,
                                    symbol_pairs=symbol_pairs,
                                    compound_symbols=compound_symbols,
                                    terminal_symbols=terminal_symbols,
                                    edge_pairs=edge_pairs,
                                    unbounded=unbounded,
                                    shortened=shortened)
        if not synonyms:
            node_list = [node
                         for node in pairs
                         if check_node(node)]
        else:
            # loop through all kept nodes and their expanded nodes
            node_list = [expanded_node
                         for node in pairs
                         if check_node(node)
                         for expanded_node in expand_node_with_wildcards(node)
                         ]
        # create a list of nodes and their payloads
        formula_size = len(node_list)
        # do we want to expand with location
        if expand_location:
            nodes_payloads = expand_nodes_with_location(node_list,
                                                        formula_size)
        else:
            # remove the location if not wanted and create payloads
            nodes_payloads = [pop_location(node, formula_size, location)
                              for node in node_list]
        if no_payload:
            node_list = [format_node(node[0]) for node in nodes_payloads]
        else:
            # now format the nodes
            node_list = [format_node(node[0], payload=node[1])
                         for node in nodes_payloads]
        # add start and end strings
        node_list = [START_TAG] + node_list + [END_TAG]
        return " ".join(node_list)
    else:
        return ""


def check_node(node):
    """Returns False if the node is not needed
    """
    node_type = determine_node(node)
    check = True
    if node_type == EOL_NODE or node_type == TERMINAL_NODE:
        # only need to look at first part
        check = not check_wildcard(node[0])
    elif node_type == SYMBOL_PAIR_NODE:
        # does it make sense to keep pairs of symbols with no path
        # if one of those symbols is a wildcard
        if len(node) == 3:
            # if one is a wildcard then dont want to keep it
            check = not(check_wildcard(node[0]) or check_wildcard(node[1]))
        else:
            # then both need to be a wildcard
            check = not(check_wildcard(node[0]) and check_wildcard(node[1]))
    elif node_type == EDGE_PAIR_NODE or node_type == COMPOUND_NODE:
        # keep them regardless at this point
        pass
    return check


def expand_nodes_with_location(nodes, formula_size):
    """Returns a list of nodes where each tuple is expand to two tuples
        one with its location and one without its location

    Parameters:
        nodes: the list of nodes
        formula_size: the size of the formula
    Returns:
        result: the list of nodes after expansion
    """
    result = []
    for node in nodes:
        location = node[-1]
        # add the first node
        result.append((node, location + PAYLOAD_SEPARATOR + str(formula_size)))
        # add the second node
        temp_node = list(node)
        temp_node.pop()
        temp_node = tuple(temp_node)
        result.append((temp_node,
                      location + PAYLOAD_SEPARATOR + str(formula_size)))
    return result


def pop_location(node, formula_size, include_location):
    """Returns the node along with the payload

    Parameters:
        node: the math tuple
        formula_size: the total size of the math formula
        include_location: whether to include the location in the tuple
    Returns:
        : a tuple with (node, payload)
    """
    location = node[-1]
    if not include_location:
        # need to remove the location from the tuple
        node = list(node)
        node.pop()
        node = tuple(node)
    return (node, location + PAYLOAD_SEPARATOR + str(formula_size))


def check_wildcard(term):
    """Returns True if term is a wildcard term
    """
    wildcard = True
    letters = "zxcvbnmasdfghjklqwertyuiop"
    letter = 0
    while letter < len(letters) and term.lower() != "?" + letters[letter]:
        letter += 1
    if letter == len(letters):
        # got to the end so not a wild card
        wildcard = False
    return wildcard


def format_node(node, payload=None):
    """Returns the formatted node
    """
    new_node = []
    for part in node:
        new_node.append(part)
        if "*" in part:
            new_node[-1] = "/*"
        if "?" in part:
            new_node[-1] = WILDCARD
    node = tuple(new_node)
    node = str(node).lower()
    if payload is not None:
        node = node + PAYLOAD_DELIMITER + payload
    return ("#" + (str(node)
                   .replace(" ", "")
                   .replace("&comma;", "comma")
                   .replace("&lsqb;", "lsqb")
                   .replace("&rsqb;", "rsqb")
                   .replace("&quest;", "quest")
                   .replace("'>'", "'gt'")
                   .replace("'<'", "'lt'")
                   ) + "#")


def determine_node(node):
    """Returns the type of node
    """
    node_type = SYMBOL_PAIR_NODE
    if node[1] == "!0":
        if len(node) == 2:
            node_type = TERMINAL_NODE
        elif node[2] == "n":
            node_type = EOL_NODE
        else:
            node_type = TERMINAL_NODE
    elif ("[" in node[1] and "]" in node[1]) or isinstance(node[1], list):
        node_type = COMPOUND_NODE
    elif node[0] in EDGES:
        node_type = EDGE_PAIR_NODE
    return node_type


def expand_node_with_wildcards(node):
    """Returns a list of nodes that includes the expanded nodes
    """
    results = [node]
    node_type = determine_node(node)
    if node_type == SYMBOL_PAIR_NODE:
        # if just two symbols (no path) then no point in expanding
        if len(node) > 3:
            # expands to two nodes
            # one with first tag as wc and second tag as wc
            temp = list(node)
            remember = temp[0]
            if (not check_wildcard(remember) and not check_wildcard(temp[1])):
                temp[0] = WILDCARD_MOCK
                results.append(tuple(temp))
            # now do the second node
            if (not check_wildcard(remember) and not check_wildcard(temp[1])):
                temp[0] = remember
                temp[1] = WILDCARD_MOCK
                results.append(tuple(temp))
    elif node_type == COMPOUND_NODE:
        # add an expansion of the compound node
        # the node tag is replaced with a wildcard
        if (not check_wildcard(node[0])):
            temp = list(node)
            temp[0] = WILDCARD_MOCK
            results.append(tuple(temp))
    elif node_type == EDGE_PAIR_NODE:
        # replace tag with a wildcard
        if (not check_wildcard(node[-2])):
            temp = list(node)
            temp[-2] = WILDCARD_MOCK
            results.append(tuple(temp))
    elif node_type == TERMINAL_NODE or EOL_NODE:
        # no expansion for them
        pass
    return results