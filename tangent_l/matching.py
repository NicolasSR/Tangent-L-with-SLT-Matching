import re

from tangent_l.mathsymbol import mathvariant_flags_dict

mathvariant_flags_str = ''.join(mathvariant_flags_dict.values())
format_marker = '¡'
format_split_re_pattern = re.compile(r"¡(["+mathvariant_flags_str+r"]*?)([\[\],])")
unknown_next_marker = ',?'

def match_pattern_in_slt(pattern, doc_slt, flexible_format=False):

    def _get_piece_or_pattern(piece):
        if format_marker in piece:
            pre_format_splits = format_split_re_pattern.split(piece)
            end_format = ''
            for c in pre_format_splits[-1][::-1]:
                if c in set(mathvariant_flags_dict.values()):
                    end_format = c+end_format
                elif c == '¡':
                    pre_format_splits[-1] = pre_format_splits[-1].removesuffix(end_format)
                    break
                else:
                    end_format = None
                    break
            else:
                end_format = None
            format_splits = []
            formats_orig = []
            init_char = ''
            current_tag = ''
            for i, split in enumerate(pre_format_splits):
                relative_i = i%3
                if relative_i == 0:
                    format_splits.append(init_char+split)
                    tag_init_idx = max(0,split.rfind('[')+1)
                    current_tag = split[tag_init_idx:]
                elif relative_i == 1:
                    formats_orig.append((current_tag,split))
                elif relative_i == 2:
                    if len(split)!=1:
                        print('Error while splitting by format markers. Second groups of re pattern should have length 1')
                        return None
                    init_char = split
            re_pattern = f"¡([{mathvariant_flags_str}]*)".join([re.escape(split) for split in format_splits])
            piece_min_string = "¡".join([re.escape(split) for split in format_splits])
            if re_pattern[-1]==format_marker: # Add format group for the node containing the unknown_next_marker
                re_pattern+=f"([{mathvariant_flags_str}]*)"
                piece_min_string+='¡'
            re_pattern_compiled = re.compile(re_pattern)
            if end_format is not None:
                formats_orig.append((current_tag[:-1],end_format))
            return (re_pattern_compiled, formats_orig), len(piece_min_string)
        else:
            return piece, len(piece)

    matches_indices_list = []
    matches_inner_content = []
    matches_style_differences = []
    pattern_len = 0
    if flexible_format:
        pieces = []
        for sub_pattern in pattern.split(unknown_next_marker):
            piece, piece_len = _get_piece_or_pattern(sub_pattern)
            pieces.append(piece)
            pattern_len += piece_len
    else:
        pieces = [sub_pattern for sub_pattern in pattern.split(unknown_next_marker)]
        pattern_len = sum([len(p) for p in pieces])
        if any(p not in doc_slt for p in pieces):
            return matches_indices_list, matches_inner_content, matches_style_differences
    finished = False
    i_c_total = 0
    while not finished:
        match_indices=[]
        match_inner_content=[]
        style_differences=[]
        restart = False
        for i_p, p in enumerate(pieces):
            if i_p != 0:
                bracket_count = 0
                if doc_slt[0] not in [',','[',']']:
                    restart = True
                    break
                for i_c, c in enumerate(doc_slt):
                    if c == '[':
                        bracket_count += 1
                    elif c == ']':
                        bracket_count -= 1
                        if bracket_count==0:
                            match_inner_content.append(doc_slt_local[:i_c+1])
                            doc_slt_local=doc_slt_local[i_c+1:]
                            i_c_local+=i_c+1
                            break
                else:
                    print('ERROR: Unbalanced parenthesis in doc_slt. Returning no match')
                    return None
            if isinstance(p,tuple):
                re_pattern_compiled = p[0]
                formats_orig = p[1]
                if i_p == 0:
                    re_match = re_pattern_compiled.search(doc_slt)
                    if re_match is None:
                        return matches_indices_list, matches_inner_content, matches_style_differences
                    index_start = i_c_total + re_match.span()[0]
                    local_end = re_match.span()[1]
                    i_c_total += local_end
                    i_c_local = i_c_total
                    doc_slt = doc_slt[local_end:]
                    doc_slt_local = doc_slt
                else:
                    re_match = re_pattern_compiled.match(doc_slt_local)
                    if re_match is None: # Pattern was not matched at the beginning of doc_slt
                        restart = True
                        break
                    index_start = i_c_local
                    local_end = re_match.span()[1]
                    i_c_local += local_end
                    doc_slt_local = doc_slt_local[local_end:]
                match_indices.append((index_start,i_c_local))
                style_differences.extend([(f_orig[0], f_orig[1], f_match) for f_orig, f_match in zip(formats_orig, re_match.groups())])
            else:
                if i_p == 0:
                    found_index = doc_slt.find(p)
                    if found_index == -1:
                        return matches_indices_list, matches_inner_content, matches_style_differences
                    index_start = i_c_total + found_index
                    local_end = found_index+len(p)
                    i_c_total += local_end
                    i_c_local = i_c_total
                    doc_slt = doc_slt[local_end:]
                    doc_slt_local = doc_slt
                else:
                    if doc_slt_local.startswith(p):
                        index_start = i_c_local
                        local_end = len(p)
                        i_c_local += local_end
                        doc_slt_local = doc_slt_local[local_end:]
                    else:
                        restart = True
                        break
                match_indices.append((index_start,i_c_local))

        if not restart:
            matches_indices_list.append(match_indices)
            matches_inner_content.append(match_inner_content)
            matches_style_differences.append(style_differences)

        if len(doc_slt) < pattern_len:
            finished = True
        
    return matches_indices_list, matches_inner_content, matches_style_differences