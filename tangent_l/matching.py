import re

from tangent_l.mathsymbol import mathvariant_flags_dict

mathvariant_flags_str = ''.join(mathvariant_flags_dict.values())
format_marker = '¡'
format_split_re_pattern = re.compile(f"¡([{mathvariant_flags_str}]*?)([\[\],])")

def match_pattern_in_slt(pattern, doc_slt, flexible_format=False):
    matches_indices_list = []
    matches_inner_content = []
    matches_style_differences = []
    pieces = [sub_pattern for sub_pattern in pattern.split(',?')]
    if not flexible_format and any(p not in doc_slt for p in pieces):
        return matches_indices_list, matches_inner_content, matches_style_differences
    finished = False
    i_c_total = 0
    while not finished:
        match_indices=[]
        match_inner_content=[]
        style_differences=[]
        for i_p, p in enumerate(pieces):
            if flexible_format and format_marker in p:
                pre_format_splits = format_split_re_pattern.split(p)
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
                # style_splits = p.split(format_marker)
                # splits_to_remove = []
                # orig_format = []
                # for i_s, split in enumerate(style_splits[1:]):
                #     if split == '':
                #         # Means we had '¡¡', which should only occur if using ¡ as an operator in the mathematical expression.
                #         splits_to_remove.append(i_s+1)
                #         style_splits[i_s]+='¡'
                #     else:
                #         format_end_mark_idx = [v for v in [split.find(m) for m in ['[',']',',']] if v>=0]
                #         orig_format.append(style_splits[i_s+1][:format_end_mark_idx])
                #         style_splits[i_s+1] = style_splits[i_s+1][format_end_mark_idx:]
                # for i_empty_split in reversed(splits_to_remove):
                #     del(style_splits[i_empty_split])
                re_pattern = f"¡([{mathvariant_flags_str}]*)".join([re.escape(split) for split in format_splits])
                re_match = re.search(re_pattern, doc_slt)
                if re_match.span()[0]>0 and i_p!=0: # For pieces other than the first one, the piece should be at the start of the string. Otherwise, we have to start from the first piece again.
                    break
                if re_match is None:
                    return matches_indices_list, matches_inner_content, matches_style_differences
                index_start = i_c_total + re_match.span()[0]
                local_end = re_match.span()[1]
                i_c_total += local_end
                style_differences.extend([(f_orig[0], f_orig[1], f_match) for f_orig, f_match in zip(formats_orig, re_match.groups())])
                match_indices.append((index_start,i_c_total))
                doc_slt = doc_slt[local_end:]
            else:
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
        if len(doc_slt) < sum(len(p)-p.count(format_marker) for p in pieces):
            finished = True
    return matches_indices_list, matches_inner_content, matches_style_differences