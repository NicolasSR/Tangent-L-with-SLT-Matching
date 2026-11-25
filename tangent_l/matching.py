import re

from tangent_l.mathsymbol import mathvariant_flags_dict

style_wildcard = '¡¿'
regex_mathvariant_group_pattern = ''.join(mathvariant_flags_dict.values())

def match_pattern_in_slt(pattern, doc_slt):
    matches_indices_list = []
    matches_inner_content = []
    matches_style_differences = []
    pieces = [sub_pattern for sub_pattern in pattern.split(',?')]
    if style_wildcard not in pattern and any(p not in doc_slt for p in pieces):
        return matches_indices_list, matches_inner_content, matches_style_differences
    finished = False
    i_c_total = 0
    while not finished:
        match_indices=[]
        match_inner_content=[]
        style_differences=[]
        for i_p, p in enumerate(pieces):
            found_index = doc_slt.find(p)
            if found_index>0 and i_p!=0: # For pieces other than the first one, the piece should be at the start of the string. Otherwise, we have to start from the first piece again.
                break
            elif found_index == -1:
                return matches_indices_list, matches_inner_content, matches_style_differences
            index_start = i_c_total + found_index
            local_end = found_index+len(p)
            i_c_total += local_end
            match_indices.append((index_start,i_c_total))
            doc_slt = doc_slt[local_end:]
                
            if i_p == len(pieces)-1:
                matches_indices_list.append(match_indices)
                matches_inner_content.append(match_inner_content)
                matches_style_differences.append(style_differences)
                break
            bracket_count = 0
            for i_c, c in enumerate(doc_slt):
                if c == '[':
                    bracket_count += 1
                elif c == ']':
                    bracket_count -= 1
                    if bracket_count==0:
                        match_inner_content.append(doc_slt[:i_c+1])
                        doc_slt=doc_slt[i_c+1:]
                        i_c_total+=i_c+1
                        break
            else:
                print('ERROR: Unbalanced parenthesis in doc_slt. Returning no match')
                return None
        if len(doc_slt) < sum(len(p)-p.count(style_wildcard) for p in pieces):
            finished = True
    return matches_indices_list, matches_inner_content, matches_style_differences